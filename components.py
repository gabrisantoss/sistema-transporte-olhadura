from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from app_logging import get_logger
from styles import PREMIUM_STYLESHEET
from workers import InfoWorker


LOGGER = get_logger(__name__)


class NewsTicker(QtWidgets.QWidget):
    def __init__(self, db, parent=None, internet_ok: bool = True):
        super().__init__(parent)
        self.db = db
        self.internet_ok = internet_ok
        self.clima_cache = "Aguardando atualizacao..."
        self.texto_completo = (
            "   SINCRONIZANDO INFORMACOES DE CAMPO...   "
            if internet_ok
            else "   MODO OFFLINE ATIVO   "
        )
        self.offset = 0

        self.setFixedHeight(28)
        self.setStyleSheet("background-color: #0f151d; border-top: 1px solid #203a50;")

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.mover_texto)
        self.timer.start(50)

        self.worker = None
        self.refresh_timer = None

        if internet_ok:
            self.worker = InfoWorker(self.db)
            self.worker.info_pronta.connect(self.atualizar)
            self.worker.clima_atual_sertaozinho.connect(self._atualizar_clima_cache)
            self.worker.finished.connect(self._agendar_proxima_consulta)
            self.worker.start()

    def _atualizar_clima_cache(self, texto: str) -> None:
        self.clima_cache = texto

    def _agendar_proxima_consulta(self) -> None:
        if not self.internet_ok:
            return

        if self.refresh_timer is None:
            self.refresh_timer = QtCore.QTimer(self)
            self.refresh_timer.setInterval(900000)
            self.refresh_timer.timeout.connect(self._iniciar_worker)
            self.refresh_timer.start()

    def _iniciar_worker(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.worker = InfoWorker(self.db)
        self.worker.info_pronta.connect(self.atualizar)
        self.worker.clima_atual_sertaozinho.connect(self._atualizar_clima_cache)
        self.worker.finished.connect(self._agendar_proxima_consulta)
        self.worker.start()

    def atualizar(self, lista) -> None:
        if not lista:
            return
        separador = "          "
        self.texto_completo = separador + separador.join(lista) + separador
        self.update()

    def mover_texto(self) -> None:
        self.offset -= 2
        largura = self.fontMetrics().horizontalAdvance(self.texto_completo)
        if largura <= 0:
            return
        if self.offset <= -largura:
            self.offset += largura
        self.update()

    def paintEvent(self, _event) -> None:
        if not self.isVisible():
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#0f151d"))
        painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Bold))
        painter.setPen(QtGui.QColor("#7ec8e3") if self.internet_ok else QtGui.QColor("#ffc48a"))
        largura = self.fontMetrics().horizontalAdvance(self.texto_completo)
        painter.drawText(self.offset, 19, self.texto_completo)
        painter.drawText(self.offset + largura, 19, self.texto_completo)


class DialogoComparacao(QtWidgets.QDialog):
    def __init__(self, parent, numero, dados_antigos, dados_novos):
        super().__init__(parent)
        self.setWindowTitle(f"Conflito na nota {numero}")
        self.setModal(True)
        self.resize(750, 400)
        self.setStyleSheet(PREMIUM_STYLESHEET)
        self.resultado = "cancelar"

        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(f"A nota {numero} ja existe.")
        label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #f28b82;")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)

        tabela = QtWidgets.QTableWidget()
        tabela.setColumnCount(3)
        tabela.setHorizontalHeaderLabels(["CAMPO", "SISTEMA (ANTIGO)", "DIGITADO (NOVO)"])
        tabela.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        tabela.setRowCount(5)

        campos = [
            ("Motorista", "motorista_nome"),
            ("Caminhao", "caminhao"),
            ("Fazenda", "faz_plantio_nome"),
            ("Data", "data_colheita"),
            ("Variedade", "variedade_nome"),
        ]
        dados_antigos = dict(dados_antigos)

        for index, (nome, chave) in enumerate(campos):
            valor_antigo = str(dados_antigos.get(chave, ""))
            valor_novo = str(dados_novos.get(chave, ""))
            tabela.setItem(index, 0, QtWidgets.QTableWidgetItem(nome))
            tabela.setItem(index, 1, QtWidgets.QTableWidgetItem(valor_antigo))
            item = QtWidgets.QTableWidgetItem(valor_novo)
            if valor_antigo != valor_novo:
                item.setBackground(QtGui.QColor("#4d3800"))
                item.setForeground(QtGui.QColor("#ffdd57"))
            tabela.setItem(index, 2, item)

        layout.addWidget(tabela)

        botoes = QtWidgets.QHBoxLayout()
        btn_cancelar = QtWidgets.QPushButton(" Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_sobrescrever = QtWidgets.QPushButton(" Sobrescrever")
        btn_sobrescrever.clicked.connect(lambda: self.fim("sobrescrever"))
        btn_duplicar = QtWidgets.QPushButton(f" Duplicar ({numero}0)")
        btn_duplicar.clicked.connect(lambda: self.fim("duplicar"))
        botoes.addWidget(btn_cancelar)
        botoes.addWidget(btn_sobrescrever)
        botoes.addWidget(btn_duplicar)
        layout.addLayout(botoes)

    def fim(self, acao: str) -> None:
        self.resultado = acao
        self.accept()
