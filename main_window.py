from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
import qtawesome as qta

from app_config import APP_ROOT
from app_logging import get_logger
from components import NewsTicker
from styles import PREMIUM_STYLESHEET
from tabs.tab_cadastros import TabCadastros
from tabs.tab_historico import TabHistorico
from tabs.tab_lancamento import TabLancamento
from tabs.tab_logistica_cadastros import TabLogisticaCadastros
from tabs.tab_logistica_mapa import TabLogisticaMapa
from tabs.tab_mapa import AbaIntegracaoMapa
from tabs.tab_relatorios import AbaRelatorios


LOGGER = get_logger(__name__)
BACKUP_DIR = APP_ROOT / "backups"


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db, internet_ok: bool = True):
        super().__init__()
        self.db = db
        self.internet_ok = internet_ok
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        self.setStyleSheet(PREMIUM_STYLESHEET)
        self.setWindowTitle("Sistema de Transporte | Safra 2026")
        self.resize(1500, 900)

        self._setup_ui()
        self._setup_atalhos()
        self._atualizar_contadores()
        self.showMaximized()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.db.create_backup(
                BACKUP_DIR / f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.db"
            )
        except Exception:
            LOGGER.exception("Falha ao criar backup local ao fechar janela")
        event.accept()

    def _setup_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(8)

        header = QtWidgets.QFrame()
        header.setObjectName("CardSoft")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(10)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QtWidgets.QLabel("Sistema de Transporte")
        lbl_title.setObjectName("WindowTitle")
        lbl_subtitle = QtWidgets.QLabel("Operacao de campo, historico e relatorios em um unico painel")
        lbl_subtitle.setObjectName("WindowSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_subtitle)

        status_box = QtWidgets.QHBoxLayout()
        status_box.setSpacing(8)
        self.lbl_internet = QtWidgets.QLabel(
            "Online" if self.internet_ok else "Offline"
        )
        self.lbl_internet.setObjectName("StatusChipOnline" if self.internet_ok else "StatusChipOffline")
        self.lbl_backup = QtWidgets.QLabel("Backup local ativo")
        self.lbl_backup.setObjectName("StatusChipNeutral")
        status_box.addWidget(self.lbl_internet)
        status_box.addWidget(self.lbl_backup)

        header_layout.addLayout(title_box, 1)
        header_layout.addLayout(status_box)
        layout.addWidget(header)

        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.tab_lanc = TabLancamento(self.db, self)
        self.tabs.addTab(self.tab_lanc, qta.icon("fa5s.edit"), " Lancamento (F12)")

        self.tab_hist = TabHistorico(self.db, self)
        self.tabs.addTab(self.tab_hist, qta.icon("fa5s.list"), " Historico (F5)")

        self.tab_rel = AbaRelatorios(self.db, self)
        self.tabs.addTab(self.tab_rel, qta.icon("fa5s.chart-line"), " BI e Relatorios")

        self.tab_mapa = AbaIntegracaoMapa(self.db, self)
        self.tabs.addTab(self.tab_mapa, qta.icon("fa5s.satellite"), " Satelite")

        self.tab_cad = TabCadastros(self.db, self)
        self.tabs.addTab(self.tab_cad, qta.icon("fa5s.plus-circle"), " Cadastros")

        # Codigo mantido importado para facilitar futura reativacao.
        _ = (TabLogisticaCadastros, TabLogisticaMapa)

        self.ticker = NewsTicker(self.db, internet_ok=self.internet_ok)
        layout.addWidget(self.ticker)

        self.status = QtWidgets.QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)

        self.lbl_hj = QtWidgets.QLabel("Hoje: 0")
        self.lbl_hj.setObjectName("StatusMetricGreen")
        self.lbl_tot = QtWidgets.QLabel("Total: 0")
        self.lbl_tot.setObjectName("StatusMetricBlue")
        self.status.addPermanentWidget(self.lbl_hj)
        self.status.addPermanentWidget(self.lbl_tot)
        self.status.showMessage("Sistema pronto.", 3000)

    def _setup_atalhos(self) -> None:
        QtWidgets.QShortcut(
            QtGui.QKeySequence("F12"),
            self,
            activated=lambda: self.tabs.setCurrentWidget(self.tab_lanc),
        )
        QtWidgets.QShortcut(
            QtGui.QKeySequence("F5"),
            self,
            activated=lambda: self.tab_hist.carregar_dados(self.tab_hist._usar_filtro_atual),
        )
        QtWidgets.QShortcut(
            QtGui.QKeySequence("Esc"),
            self,
            activated=self.tab_lanc._limpar,
        )

    def _atualizar_contadores(self) -> None:
        try:
            hoje_sql = date.today().strftime("%Y-%m-%d")
            total = self.db.contar_notas_total()
            hoje = self.db.contar_notas_data(hoje_sql)
            self.lbl_tot.setText(f" Total: {total} ")
            self.lbl_hj.setText(f" Hoje: {hoje} ")
        except Exception:
            LOGGER.exception("Falha ao atualizar contadores da janela principal")

    def reabrir_lancamento_para_nota(self, numero) -> None:
        self.tabs.setCurrentWidget(self.tab_lanc)
        self.tab_lanc.carregar_nota_para_edicao(numero)

    def recarregar_dados_apos_restore(self) -> None:
        for action in (
            self.tab_lanc.recarregar_referencias,
            lambda: self.tab_hist.carregar_dados(False),
            self.tab_rel.gerar_dashboard,
            self.tab_cad.recarregar_tabelas,
            self.tab_mapa.atualizar_status_gps,
        ):
            try:
                action()
            except Exception:
                LOGGER.exception("Falha ao recarregar dados apos restauracao")

        self._atualizar_contadores()
        self.status.showMessage("Dados recarregados apos restauracao do backup.", 4000)
