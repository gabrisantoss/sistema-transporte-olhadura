from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("transporte.db")

NOTE_FIELDS = (
    "numero",
    "motorista_cod",
    "motorista_nome",
    "caminhao",
    "operador_cod",
    "operador_nome",
    "colhedora",
    "faz_muda_cod",
    "faz_muda_nome",
    "talhao",
    "faz_plantio_cod",
    "faz_plantio_nome",
    "variedade_id",
    "variedade_nome",
    "data_colheita",
    "data_plantio",
)


class DatabaseAdapter:
    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Banco nao encontrado: {path}")
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def buscar_por_codigo(self, tabela: str, codigo: Any) -> sqlite3.Row | None:
        if codigo in (None, ""):
            return None
        query = f"SELECT codigo, nome FROM {tabela} WHERE codigo = ?"
        res = self.conn.execute(query, (codigo,)).fetchone()
        if res:
            return res
        if tabela == "fazendas":
            codigo_txt = str(codigo)
            if "-" not in codigo_txt and len(codigo_txt) >= 4:
                codigo_alt = codigo_txt[:3] + "-" + codigo_txt[3:]
                return self.conn.execute(query, (codigo_alt,)).fetchone()
        return None

    def close(self) -> None:
        self.conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insere registros e aplica correcoes no transporte.db com validacao e simulacao.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python script_insercao.py notas --registro "
            "'{\"numero\": 1289999, \"motorista\": \"972 - ANDERSON FABRICIO ELIAS\", "
            "\"destino\": \"1132457 - FAZENDA SANTA LUCIA I\", "
            "\"variedade\": \"IACSP04-6007\", \"data_colheita\": \"2026-03-13\"}' --dry-run\n"
            "  python script_insercao.py motoristas --arquivo motoristas.json\n"
            "  python script_insercao.py notas --arquivo notas.json --force\n"
            "  python script_insercao.py correcoes --arquivo correcoes.json --dry-run"
        ),
    )
    parser.add_argument(
        "tabela",
        choices=("motoristas", "fazendas", "variedades", "notas", "correcoes"),
        help="Tabela de destino.",
    )
    origem = parser.add_mutually_exclusive_group(required=True)
    origem.add_argument("--arquivo", help="Arquivo JSON contendo um objeto ou lista de objetos.")
    origem.add_argument("--registro", help="Registro em JSON inline.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Caminho do banco SQLite.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Atualiza registros existentes quando houver chave duplicada.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra os registros normalizados sem gravar no banco.",
    )
    return parser.parse_args()


def carregar_registros(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.arquivo:
        payload = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    else:
        payload = json.loads(args.registro)

    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError("O JSON precisa ser um objeto ou uma lista de objetos.")


def texto(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def inteiro(value: Any, campo: str) -> int:
    value = texto(value)
    if value is None:
        raise ValueError(f"O campo '{campo}' e obrigatorio.")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"O campo '{campo}' precisa ser numerico: {value}") from exc


def inteiro_opcional(value: Any) -> int | None:
    value = texto(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def decimal_opcional(value: Any, campo: str) -> float | None:
    value = texto(value)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"O campo '{campo}' precisa ser numerico: {value}") from exc


def separar_codigo_nome(value: Any) -> tuple[str | None, str | None]:
    value = texto(value)
    if value is None:
        return None, None
    if " - " in value:
        codigo, nome = value.split(" - ", 1)
        return texto(codigo), texto(nome)
    return value, None


def primeiro_preenchido(registro: dict[str, Any], *chaves: str) -> Any:
    for chave in chaves:
        if chave in registro and registro[chave] not in (None, ""):
            return registro[chave]
    return None


def buscar_por_nome(
    db: DatabaseAdapter,
    tabela: str,
    nome: str,
    codigo_coluna: str = "codigo",
) -> sqlite3.Row | None:
    consulta = {
        "motoristas": f"SELECT {codigo_coluna}, nome FROM motoristas WHERE UPPER(TRIM(nome)) = UPPER(TRIM(?)) LIMIT 1",
        "fazendas": f"SELECT {codigo_coluna}, nome FROM fazendas WHERE UPPER(TRIM(nome)) = UPPER(TRIM(?)) LIMIT 1",
        "variedades": "SELECT id, nome FROM variedades WHERE UPPER(TRIM(nome)) = UPPER(TRIM(?)) LIMIT 1",
    }
    return db.conn.execute(consulta[tabela], (nome,)).fetchone()


def resolver_cadastro(
    db: DatabaseAdapter,
    tabela: str,
    codigo: Any = None,
    nome: Any = None,
) -> tuple[int | str | None, str | None]:
    codigo_txt = texto(codigo)
    nome_txt = texto(nome)

    if codigo_txt:
        row = db.buscar_por_codigo(tabela, codigo_txt)
        if row:
            codigo_real = row["codigo"]
            return codigo_real, texto(row["nome"])
        return inteiro_opcional(codigo_txt) or codigo_txt, nome_txt

    if nome_txt:
        row = buscar_por_nome(db, tabela, nome_txt)
        if row:
            codigo_real = row["codigo"]
            return codigo_real, texto(row["nome"])
        return None, nome_txt

    return None, None


def resolver_variedade(
    db: DatabaseAdapter,
    variedade_id: Any = None,
    variedade_nome: Any = None,
) -> tuple[int | None, str | None]:
    var_id_txt = texto(variedade_id)
    var_nome_txt = texto(variedade_nome)

    if var_id_txt:
        var_id_num = inteiro_opcional(var_id_txt)
        if var_id_num is not None:
            row = db.conn.execute("SELECT id, nome FROM variedades WHERE id = ?", (var_id_num,)).fetchone()
            if row:
                return row["id"], var_nome_txt or texto(row["nome"])
            return var_id_num, var_nome_txt

        row = buscar_por_nome(db, "variedades", var_id_txt, "id")
        if row:
            return row["id"], var_nome_txt or texto(row["nome"])
        return None, var_nome_txt or var_id_txt

    if var_nome_txt:
        row = buscar_por_nome(db, "variedades", var_nome_txt, "id")
        if row:
            return row["id"], texto(row["nome"])
        return None, var_nome_txt

    return None, None


def normalizar_motorista(registro: dict[str, Any]) -> dict[str, Any]:
    return {
        "codigo": inteiro(primeiro_preenchido(registro, "codigo", "motorista_cod"), "codigo"),
        "nome": texto(primeiro_preenchido(registro, "nome", "motorista_nome")),
    }


def normalizar_fazenda(registro: dict[str, Any]) -> dict[str, Any]:
    return {
        "codigo": texto(primeiro_preenchido(registro, "codigo", "fazenda_cod")),
        "nome": texto(primeiro_preenchido(registro, "nome", "fazenda_nome")),
        "lat": decimal_opcional(registro.get("lat"), "lat"),
        "lon": decimal_opcional(registro.get("lon"), "lon"),
    }


def normalizar_variedade(registro: dict[str, Any]) -> dict[str, Any]:
    return {
        "nome": texto(primeiro_preenchido(registro, "nome", "variedade", "variedade_nome")),
    }


def normalizar_nota(db: DatabaseAdapter, registro: dict[str, Any]) -> dict[str, Any]:
    numero = inteiro(registro.get("numero"), "numero")

    mot_cod, mot_nome = separar_codigo_nome(primeiro_preenchido(registro, "motorista"))
    mot_cod = primeiro_preenchido(registro, "motorista_cod") or mot_cod
    mot_nome = primeiro_preenchido(registro, "motorista_nome") or mot_nome
    motorista_cod, motorista_nome = resolver_cadastro(db, "motoristas", mot_cod, mot_nome)

    op_cod, op_nome = separar_codigo_nome(primeiro_preenchido(registro, "operador"))
    op_cod = primeiro_preenchido(registro, "operador_cod") or op_cod
    op_nome = primeiro_preenchido(registro, "operador_nome") or op_nome
    operador_cod, operador_nome = resolver_cadastro(db, "motoristas", op_cod, op_nome)

    origem_cod, origem_nome = separar_codigo_nome(primeiro_preenchido(registro, "origem", "faz_muda"))
    origem_cod = primeiro_preenchido(registro, "faz_muda_cod") or origem_cod
    origem_nome = primeiro_preenchido(registro, "faz_muda_nome") or origem_nome
    faz_muda_cod, faz_muda_nome = resolver_cadastro(db, "fazendas", origem_cod, origem_nome)

    destino_cod, destino_nome = separar_codigo_nome(primeiro_preenchido(registro, "destino", "faz_plantio"))
    destino_cod = primeiro_preenchido(registro, "faz_plantio_cod") or destino_cod
    destino_nome = primeiro_preenchido(registro, "faz_plantio_nome") or destino_nome
    faz_plantio_cod, faz_plantio_nome = resolver_cadastro(db, "fazendas", destino_cod, destino_nome)

    var_cod, var_nome = separar_codigo_nome(primeiro_preenchido(registro, "variedade"))
    var_cod = primeiro_preenchido(registro, "variedade_id") or var_cod
    var_nome = primeiro_preenchido(registro, "variedade_nome") or var_nome
    variedade_id, variedade_nome = resolver_variedade(db, var_cod, var_nome)

    if not (motorista_cod or motorista_nome):
        raise ValueError("A nota precisa ter motorista_cod, motorista_nome ou motorista.")
    if not (faz_plantio_cod or faz_plantio_nome):
        raise ValueError("A nota precisa ter faz_plantio_cod, faz_plantio_nome, destino ou faz_plantio.")
    if not (variedade_id or variedade_nome):
        raise ValueError("A nota precisa ter variedade_id, variedade_nome ou variedade.")

    data_colheita = texto(registro.get("data_colheita")) or date.today().isoformat()
    data_plantio = texto(registro.get("data_plantio")) or data_colheita

    return {
        "numero": numero,
        "motorista_cod": motorista_cod,
        "motorista_nome": motorista_nome,
        "caminhao": texto(registro.get("caminhao")),
        "operador_cod": operador_cod,
        "operador_nome": operador_nome,
        "colhedora": texto(registro.get("colhedora")),
        "faz_muda_cod": faz_muda_cod,
        "faz_muda_nome": faz_muda_nome,
        "talhao": texto(registro.get("talhao")),
        "faz_plantio_cod": faz_plantio_cod,
        "faz_plantio_nome": faz_plantio_nome,
        "variedade_id": variedade_id,
        "variedade_nome": variedade_nome,
        "data_colheita": data_colheita,
        "data_plantio": data_plantio,
    }


def inserir_motorista(db: DatabaseAdapter, registro: dict[str, Any], force: bool) -> str:
    try:
        db.conn.execute(
            "INSERT INTO motoristas (codigo, nome) VALUES (?, ?)",
            (registro["codigo"], registro["nome"]),
        )
        return f"motorista {registro['codigo']} inserido"
    except sqlite3.IntegrityError:
        if not force:
            raise
        db.conn.execute(
            "UPDATE motoristas SET nome = ? WHERE codigo = ?",
            (registro["nome"], registro["codigo"]),
        )
        return f"motorista {registro['codigo']} atualizado"


def inserir_fazenda(db: DatabaseAdapter, registro: dict[str, Any], force: bool) -> str:
    try:
        db.conn.execute(
            "INSERT INTO fazendas (codigo, nome, lat, lon) VALUES (?, ?, ?, ?)",
            (registro["codigo"], registro["nome"], registro["lat"], registro["lon"]),
        )
        return f"fazenda {registro['codigo']} inserida"
    except sqlite3.IntegrityError:
        if not force:
            raise
        db.conn.execute(
            "UPDATE fazendas SET nome = ?, lat = ?, lon = ? WHERE codigo = ?",
            (registro["nome"], registro["lat"], registro["lon"], registro["codigo"]),
        )
        return f"fazenda {registro['codigo']} atualizada"


def inserir_variedade(db: DatabaseAdapter, registro: dict[str, Any], force: bool) -> str:
    try:
        db.conn.execute(
            "INSERT INTO variedades (nome) VALUES (?)",
            (registro["nome"],),
        )
        return f"variedade '{registro['nome']}' inserida"
    except sqlite3.IntegrityError:
        if not force:
            raise
        return f"variedade '{registro['nome']}' ja existia"


def inserir_nota(db: DatabaseAdapter, registro: dict[str, Any], force: bool) -> str:
    valores = [registro[campo] for campo in NOTE_FIELDS] + [int(force)]
    placeholders = ",".join("?" * len(valores))
    colunas = ", ".join(NOTE_FIELDS + ("duplicado",))

    try:
        db.conn.execute(f"INSERT INTO notas ({colunas}) VALUES ({placeholders})", valores)
        return f"nota {registro['numero']} inserida"
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" not in str(exc).upper() or not force:
            raise

        update_values = valores[1:] + [registro["numero"]]
        db.conn.execute(
            """
            UPDATE notas SET
                motorista_cod = ?, motorista_nome = ?, caminhao = ?, operador_cod = ?,
                operador_nome = ?, colhedora = ?, faz_muda_cod = ?, faz_muda_nome = ?,
                talhao = ?, faz_plantio_cod = ?, faz_plantio_nome = ?, variedade_id = ?,
                variedade_nome = ?, data_colheita = ?, data_plantio = ?, duplicado = ?
            WHERE numero = ?
            """,
            update_values,
        )
        return f"nota {registro['numero']} atualizada"


def normalizar_filtros_notas(filtros: Any) -> dict[str, Any]:
    if not isinstance(filtros, dict) or not filtros:
        raise ValueError("A correcao precisa informar um objeto 'filtros' com pelo menos um criterio.")

    permitidos = {
        "numero",
        "faz_muda_cod",
        "faz_muda_nome",
        "faz_plantio_cod",
        "faz_plantio_nome",
        "variedade_id",
        "variedade_nome",
        "data_colheita",
        "data_plantio",
        "variedade_nome_vazia",
    }
    normalizados: dict[str, Any] = {}

    for chave, valor in filtros.items():
        if chave not in permitidos:
            raise ValueError(f"Filtro nao suportado em correcoes: {chave}")
        if chave == "numero":
            normalizados[chave] = inteiro(valor, chave)
        elif chave == "variedade_nome_vazia":
            normalizados[chave] = bool(valor)
        else:
            valor_txt = texto(valor)
            if valor_txt is None:
                raise ValueError(f"O filtro '{chave}' nao pode ser vazio.")
            normalizados[chave] = valor_txt

    return normalizados


def normalizar_correcao(db: DatabaseAdapter, registro: dict[str, Any]) -> dict[str, Any]:
    acao = texto(primeiro_preenchido(registro, "acao", "tipo"))
    if acao != "atualizar_variedade_notas":
        raise ValueError("Acao suportada no momento: atualizar_variedade_notas")

    filtros = normalizar_filtros_notas(registro.get("filtros"))
    variedade_id, variedade_nome = resolver_variedade(
        db,
        primeiro_preenchido(registro, "variedade_id"),
        primeiro_preenchido(registro, "variedade_nome", "variedade"),
    )
    if not (variedade_id or variedade_nome):
        raise ValueError("A correcao precisa informar a variedade de destino.")

    return {
        "acao": acao,
        "filtros": filtros,
        "variedade_id": variedade_id,
        "variedade_nome": variedade_nome,
    }


def montar_where_notas(filtros: dict[str, Any]) -> tuple[str, list[Any]]:
    clausulas: list[str] = []
    parametros: list[Any] = []

    for chave, valor in filtros.items():
        if chave == "numero":
            clausulas.append("numero = ?")
            parametros.append(valor)
        elif chave == "variedade_nome_vazia":
            if valor:
                clausulas.append("(variedade_nome IS NULL OR TRIM(variedade_nome) = '')")
            else:
                clausulas.append("(variedade_nome IS NOT NULL AND TRIM(variedade_nome) <> '')")
        else:
            clausulas.append(f"UPPER(TRIM(COALESCE({chave}, ''))) = UPPER(TRIM(?))")
            parametros.append(str(valor))

    if not clausulas:
        raise ValueError("Nenhum filtro foi informado para a correcao.")

    return " AND ".join(clausulas), parametros


def buscar_notas_correcao(db: DatabaseAdapter, filtros: dict[str, Any]) -> list[dict[str, Any]]:
    where_sql, parametros = montar_where_notas(filtros)
    rows = db.conn.execute(
        f"""
        SELECT numero, faz_muda_cod, faz_muda_nome, faz_plantio_cod, faz_plantio_nome,
               variedade_id, variedade_nome, data_colheita
        FROM notas
        WHERE {where_sql}
        ORDER BY numero
        """,
        parametros,
    ).fetchall()
    return [dict(row) for row in rows]


def simular_correcoes(db: DatabaseAdapter, registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    simulacao: list[dict[str, Any]] = []
    for indice, registro in enumerate(registros, start=1):
        notas = buscar_notas_correcao(db, registro["filtros"])
        simulacao.append(
            {
                "indice": indice,
                "acao": registro["acao"],
                "filtros": registro["filtros"],
                "variedade_id": registro["variedade_id"],
                "variedade_nome": registro["variedade_nome"],
                "quantidade_encontrada": len(notas),
                "amostra_numeros": [nota["numero"] for nota in notas[:20]],
            }
        )
    return simulacao


def executar_correcao(db: DatabaseAdapter, registro: dict[str, Any]) -> str:
    notas = buscar_notas_correcao(db, registro["filtros"])
    if not notas:
        return f"nenhuma nota encontrada para filtros {registro['filtros']}"

    where_sql, parametros = montar_where_notas(registro["filtros"])
    db.conn.execute(
        f"""
        UPDATE notas
        SET variedade_id = ?, variedade_nome = ?
        WHERE {where_sql}
        """,
        [registro["variedade_id"], registro["variedade_nome"], *parametros],
    )
    return (
        f"{len(notas)} nota(s) atualizadas para "
        f"{registro['variedade_nome']} com filtros {registro['filtros']}"
    )


def normalizar_registros(
    db: DatabaseAdapter,
    tabela: str,
    registros: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalizadores = {
        "motoristas": lambda item: normalizar_motorista(item),
        "fazendas": lambda item: normalizar_fazenda(item),
        "variedades": lambda item: normalizar_variedade(item),
        "notas": lambda item: normalizar_nota(db, item),
        "correcoes": lambda item: normalizar_correcao(db, item),
    }
    saida: list[dict[str, Any]] = []
    for indice, registro in enumerate(registros, start=1):
        normalizado = normalizadores[tabela](registro)
        campos_obrigatorios = {
            "motoristas": ("codigo", "nome"),
            "fazendas": ("codigo", "nome"),
            "variedades": ("nome",),
            "notas": ("numero",),
            "correcoes": ("acao", "filtros"),
        }[tabela]
        faltando = [campo for campo in campos_obrigatorios if normalizado.get(campo) in (None, "")]
        if faltando:
            lista = ", ".join(faltando)
            raise ValueError(f"Registro {indice} da tabela '{tabela}' esta sem: {lista}")
        saida.append(normalizado)
    return saida


def executar(
    db: DatabaseAdapter,
    tabela: str,
    registros: list[dict[str, Any]],
    force: bool,
) -> list[str]:
    insertores = {
        "motoristas": inserir_motorista,
        "fazendas": inserir_fazenda,
        "variedades": inserir_variedade,
        "notas": inserir_nota,
        "correcoes": lambda banco, registro, _: executar_correcao(banco, registro),
    }
    mensagens: list[str] = []
    with db.conn:
        for registro in registros:
            mensagens.append(insertores[tabela](db, registro, force))
    return mensagens


def main() -> int:
    args = parse_args()
    db = DatabaseAdapter(Path(args.db))
    try:
        registros_brutos = carregar_registros(args)
        registros = normalizar_registros(db, args.tabela, registros_brutos)

        if args.dry_run:
            if args.tabela == "correcoes":
                print(json.dumps(simular_correcoes(db, registros), ensure_ascii=False, indent=2))
            else:
                print(json.dumps(registros, ensure_ascii=False, indent=2))
            return 0

        mensagens = executar(db, args.tabela, registros, args.force)
        print(f"{len(mensagens)} registro(s) processado(s) com sucesso.")
        for mensagem in mensagens:
            print(f"- {mensagem}")
        return 0
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
