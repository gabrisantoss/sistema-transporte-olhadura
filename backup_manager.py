from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore

from app_config import APP_ROOT, BACKUP_DRIVE_PATH, DB_PATH, MAX_BACKUPS, MAX_LOCAL_BACKUPS
from app_logging import get_logger
from database import backup_sqlite_file, sqlite_integrity_status


LOGGER = get_logger(__name__)
PASTA_LOCAL = APP_ROOT / "backups"


def listar_backups_disponiveis() -> list[dict]:
    itens: list[dict] = []
    for origem, pasta in (("Local", PASTA_LOCAL), ("Drive", BACKUP_DRIVE_PATH)):
        pasta_path = Path(pasta)
        if not pasta_path.exists():
            continue

        for arquivo in pasta_path.glob("*.db"):
            try:
                itens.append(
                    {
                        "origem": origem,
                        "path": arquivo,
                        "nome": arquivo.name,
                        "mtime": arquivo.stat().st_mtime,
                    }
                )
            except OSError:
                LOGGER.exception("Falha ao listar backup em %s", arquivo)

    itens.sort(key=lambda item: item["mtime"], reverse=True)
    return itens


def encontrar_backup_recente_integro() -> dict | None:
    for item in listar_backups_disponiveis():
        try:
            if sqlite_integrity_status(item["path"]).lower() == "ok":
                return item
        except Exception:
            LOGGER.exception("Falha ao validar backup %s", item["path"])
    return None


def _limpar_antigos(pasta: Path, limite: int) -> None:
    if limite <= 0 or not pasta.exists():
        return

    arquivos = sorted(
        (
            arquivo
            for arquivo in pasta.glob("transporte_20*.db")
            if arquivo.is_file()
        ),
        key=lambda arquivo: arquivo.stat().st_mtime,
        reverse=True,
    )

    for arquivo in arquivos[limite:]:
        try:
            arquivo.unlink()
        except OSError:
            LOGGER.exception("Falha ao remover backup antigo %s", arquivo)


class BackupWorker(QtCore.QThread):
    finalizado = QtCore.pyqtSignal(str, bool)

    def __init__(self, db_path: str | Path = DB_PATH):
        super().__init__()
        self.db_path = Path(db_path)

    def run(self) -> None:
        if not self.db_path.exists():
            self.finalizado.emit(f"Banco de dados '{self.db_path}' nao encontrado.", False)
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nome_historico = f"transporte_{timestamp}.db"
        local_historico = PASTA_LOCAL / nome_historico
        drive_historico = Path(BACKUP_DRIVE_PATH) / nome_historico
        drive_atual = Path(BACKUP_DRIVE_PATH) / "transporte_ATUAL.db"

        PASTA_LOCAL.mkdir(parents=True, exist_ok=True)

        sucesso_local = False
        sucesso_drive = False
        erros: list[str] = []

        try:
            backup_sqlite_file(self.db_path, local_historico)
            sucesso_local = True
        except Exception as exc:
            erros.append(f"Local: {exc}")
            LOGGER.exception("Falha ao criar backup local")

        try:
            Path(BACKUP_DRIVE_PATH).mkdir(parents=True, exist_ok=True)
            backup_sqlite_file(self.db_path, drive_historico)
            backup_sqlite_file(self.db_path, drive_atual)
            sucesso_drive = True
        except Exception as exc:
            erros.append(f"Drive: {exc}")
            LOGGER.exception("Falha ao criar backup no Drive")

        _limpar_antigos(PASTA_LOCAL, MAX_LOCAL_BACKUPS)
        _limpar_antigos(Path(BACKUP_DRIVE_PATH), MAX_BACKUPS)

        if sucesso_local or sucesso_drive:
            destinos = []
            if sucesso_local:
                destinos.append("local")
            if sucesso_drive:
                destinos.append("Drive")
            msg = f"Backup concluido com sucesso em {', '.join(destinos)}."
            if erros:
                msg += f" Falhas parciais: {' | '.join(erros)}"
            self.finalizado.emit(msg, True)
            return

        self.finalizado.emit(
            "Falha ao criar backup. " + " | ".join(erros),
            False,
        )
