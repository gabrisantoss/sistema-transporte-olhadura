from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from app_logging import get_logger
from styles import aplicar_icone


LOGGER = get_logger(__name__)


class TabHistorico(QtWidgets.QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main = main_window
        self._usar_filtro_atual = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        resumo = QtWidgets.QFrame()
        resumo.setObjectName("Card")
        resumo_layout = QtWidgets.QHBoxLayout(resumo)
        resumo_layout.setContentsMargins(16, 12, 16, 12)
        self.lbl_total_registros = QtWidgets.QLabel("Registros: 0")
        self.lbl_periodo = QtWidgets.QLabel("Periodo: todos")
        self.lbl_visiveis = QtWidgets.QLabel("Visiveis: 0")
        for label in (self.lbl_total_registros, self.lbl_periodo, self.lbl_visiveis):
            label.setStyleSheet("font-weight: 700; color: #cfd3d8;")
            resumo_layout.addWidget(label)
        resumo_layout.addStretch()
        layout.addWidget(resumo)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.ed_pesq = QtWidgets.QLineEdit()
        self.ed_pesq.setPlaceholderText("Pesquisar por nota, motorista, operador, origem ou destino...")
        self.ed_pesq.textChanged.connect(self.filtrar)

        self.cb_campo = QtWidgets.QComboBox()
        self.cb_campo.addItems(
            ["Todos os campos", "Nota", "Motorista", "Operador", "Origem", "Destino", "Variedade"]
        )
        self.cb_campo.currentIndexChanged.connect(lambda: self.filtrar(self.ed_pesq.text()))

        self.dt_de = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(-7))
        self.dt_de.setCalendarPopup(True)
        self.dt_ate = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dt_ate.setCalendarPopup(True)

        btn_filtrar = QtWidgets.QPushButton(" Filtrar")
        btn_filtrar.clicked.connect(lambda: self.carregar_dados(True))
        btn_todos = QtWidgets.QPushButton(" Todos")
        btn_todos.clicked.connect(lambda: self.carregar_dados(False))
        btn_hoje = QtWidgets.QPushButton(" Hoje")
        btn_hoje.clicked.connect(self.filtrar_hoje)
        btn_7d = QtWidgets.QPushButton(" 7 dias")
        btn_7d.clicked.connect(lambda: self.aplicar_periodo_rapido(7))
        btn_30d = QtWidgets.QPushButton(" 30 dias")
        btn_30d.clicked.connect(lambda: self.aplicar_periodo_rapido(30))
        btn_exportar = QtWidgets.QPushButton(" Excel")
        btn_exportar.clicked.connect(self.exportar)

        aplicar_icone(btn_exportar, "fa5s.file-excel")
        aplicar_icone(btn_filtrar, "fa5s.filter")
        aplicar_icone(btn_todos, "fa5s.list")

        top.addWidget(self.ed_pesq, 2)
        top.addWidget(self.cb_campo)
        top.addWidget(QtWidgets.QLabel("De:"))
        top.addWidget(self.dt_de)
        top.addWidget(QtWidgets.QLabel("Ate:"))
        top.addWidget(self.dt_ate)
        top.addWidget(btn_filtrar)
        top.addWidget(btn_todos)
        top.addWidget(btn_hoje)
        top.addWidget(btn_7d)
        top.addWidget(btn_30d)
        top.addWidget(btn_exportar)
        layout.addLayout(top)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(15)
        self.table.setHorizontalHeaderLabels(
            [
                "Nota",
                "C.Mot",
                "Motorista",
                "Cam",
                "C.Op",
                "Operador",
                "Col",
                "C.FM",
                "Faz.Muda",
                "Talhao",
                "C.FP",
                "Faz.Plantio",
                "Var",
                "Dt.Col",
                "Dt.Pla",
            ]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.menu_contexto)
        self.table.itemDoubleClicked.connect(lambda *_: self.editar_selecionado())
        layout.addWidget(self.table, 1)

        self.carregar_dados(False)

    def _periodo_sql(self) -> tuple[str, str]:
        return (
            self.dt_de.date().toString("yyyy-MM-dd"),
            self.dt_ate.date().toString("yyyy-MM-dd"),
        )

    def _buscar_registros(self, usar_filtro: bool = False):
        if usar_filtro:
            return self.db.listar_notas(*self._periodo_sql())
        return self.db.listar_notas()

    def carregar_dados(self, usar_filtro: bool = False) -> None:
        self._usar_filtro_atual = usar_filtro
        rows = self._buscar_registros(usar_filtro)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row_index, row in enumerate(rows):
            self.table.insertRow(row_index)
            for col_index, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem("" if value in (None, "") else str(value))
                self.table.setItem(row_index, col_index, item)

        self.table.setSortingEnabled(True)
        periodo = "todos"
        if usar_filtro:
            periodo = (
                f"{self.dt_de.date().toString('dd/MM/yyyy')} a "
                f"{self.dt_ate.date().toString('dd/MM/yyyy')}"
            )
        self._atualizar_resumo(len(rows), periodo)
        self.filtrar(self.ed_pesq.text())

    def filtrar(self, texto: str) -> None:
        filtro = (texto or "").lower().strip()
        campo = self.cb_campo.currentText()
        mapa_campos = {
            "Nota": [0],
            "Motorista": [2],
            "Operador": [5],
            "Origem": [8],
            "Destino": [11],
            "Variedade": [12],
        }
        colunas = mapa_campos.get(campo, list(range(self.table.columnCount())))
        visiveis = 0

        for row_index in range(self.table.rowCount()):
            def _cell_text(col_index: int) -> str:
                item = self.table.item(row_index, col_index)
                return item.text().lower() if item else ""

            visivel = not filtro or any(filtro in _cell_text(coluna) for coluna in colunas)
            self.table.setRowHidden(row_index, not visivel)
            if visivel:
                visiveis += 1

        self.lbl_visiveis.setText(f"Visiveis: {visiveis}")

    def exportar(self) -> None:
        caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Salvar Excel",
            "Historico.xlsx",
            "Excel (*.xlsx)",
        )
        if not caminho:
            return

        try:
            if self._usar_filtro_atual:
                df = self.db.dataframe_historico(*self._periodo_sql())
            else:
                df = self.db.dataframe_historico()
            df.to_excel(caminho, index=False)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Historico exportado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao exportar historico")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel exportar:\n{exc}")

    def aplicar_periodo_rapido(self, dias: int) -> None:
        hoje = QtCore.QDate.currentDate()
        self.dt_ate.setDate(hoje)
        self.dt_de.setDate(hoje.addDays(-(dias - 1)))
        self.carregar_dados(True)

    def filtrar_hoje(self) -> None:
        hoje = QtCore.QDate.currentDate()
        self.dt_de.setDate(hoje)
        self.dt_ate.setDate(hoje)
        self.carregar_dados(True)

    def _atualizar_resumo(self, total: int, periodo: str) -> None:
        self.lbl_total_registros.setText(f"Registros: {total}")
        self.lbl_periodo.setText(f"Periodo: {periodo}")
        self.lbl_visiveis.setText(f"Visiveis: {total}")

    def menu_contexto(self, posicao) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction("Editar no lancamento").triggered.connect(self.editar_selecionado)
        menu.addAction("Excluir").triggered.connect(self.excluir)
        menu.exec_(self.table.viewport().mapToGlobal(posicao))

    def editar_selecionado(self) -> None:
        row_index = self.table.currentRow()
        if row_index < 0:
            return
        item = self.table.item(row_index, 0)
        if not item:
            return
        self.main.tab_lanc.carregar_nota_para_edicao(item.text())

    def excluir(self) -> None:
        row_index = self.table.currentRow()
        if row_index < 0:
            return

        resposta = QtWidgets.QMessageBox.question(
            self,
            "Excluir registro",
            "Deseja excluir a nota selecionada?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if resposta != QtWidgets.QMessageBox.Yes:
            return

        item = self.table.item(row_index, 0)
        if not item:
            return

        try:
            self.db.excluir_nota(item.text())
            self.carregar_dados(self._usar_filtro_atual)
            self.main._atualizar_contadores()
            self.main.status.showMessage("Nota excluida com sucesso.", 2500)
        except Exception as exc:
            LOGGER.exception("Falha ao excluir nota")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel excluir a nota:\n{exc}")
