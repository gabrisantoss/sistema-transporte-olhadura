from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from app_logging import get_logger
from backup_manager import BackupWorker, listar_backups_disponiveis
from styles import aplicar_icone


LOGGER = get_logger(__name__)


class TabCadastros(QtWidgets.QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main = main_window
        self.worker = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)

        gb_admin = QtWidgets.QGroupBox("Administracao do Sistema")
        gb_admin.setMaximumHeight(190)
        layout_admin = QtWidgets.QVBoxLayout(gb_admin)
        layout_admin.setSpacing(10)

        linha_backup = QtWidgets.QHBoxLayout()
        lbl_info = QtWidgets.QLabel("Backup e recuperacao")
        lbl_info.setStyleSheet("font-weight: 700; color: #d8dde4;")

        self.btn_backup = QtWidgets.QPushButton(" Fazer backup agora")
        self.btn_backup.setObjectName("PrimaryButton")
        self.btn_backup.setCursor(QtCore.Qt.PointingHandCursor)
        aplicar_icone(self.btn_backup, "fa5s.cloud-upload-alt")
        self.btn_backup.clicked.connect(self.fazer_backup_manual)

        self.btn_refresh_backups = QtWidgets.QPushButton(" Atualizar lista")
        self.btn_refresh_backups.setObjectName("SecondaryButton")
        aplicar_icone(self.btn_refresh_backups, "fa5s.sync-alt")
        self.btn_refresh_backups.clicked.connect(self.carregar_backups_disponiveis)

        self.btn_restore = QtWidgets.QPushButton(" Restaurar selecionado")
        self.btn_restore.setObjectName("DangerButton")
        aplicar_icone(self.btn_restore, "fa5s.history")
        self.btn_restore.clicked.connect(self.restaurar_backup_selecionado)

        self.cb_backups = QtWidgets.QComboBox()
        self.cb_backups.setMinimumWidth(420)
        self.lbl_backup_status = QtWidgets.QLabel("")
        self.lbl_backup_status.setObjectName("WindowSubtitle")

        linha_backup.addWidget(lbl_info)
        linha_backup.addWidget(self.btn_backup)
        linha_backup.addWidget(self.btn_refresh_backups)
        linha_backup.addStretch()

        linha_restore = QtWidgets.QHBoxLayout()
        linha_restore.addWidget(QtWidgets.QLabel("Backups disponiveis:"))
        linha_restore.addWidget(self.cb_backups, 1)
        linha_restore.addWidget(self.btn_restore)

        layout_admin.addLayout(linha_backup)
        layout_admin.addLayout(linha_restore)
        layout_admin.addWidget(self.lbl_backup_status)
        layout.addWidget(gb_admin)

        self.tabs_internas = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs_internas, 1)

        self.tab_motoristas = QtWidgets.QWidget()
        self._setup_motoristas()
        self.tabs_internas.addTab(self.tab_motoristas, "Motoristas")

        self.tab_fazendas = QtWidgets.QWidget()
        self._setup_fazendas()
        self.tabs_internas.addTab(self.tab_fazendas, "Fazendas")

        self.tab_variedades = QtWidgets.QWidget()
        self._setup_variedades()
        self.tabs_internas.addTab(self.tab_variedades, "Variedades")

        self.carregar_backups_disponiveis()

    def fazer_backup_manual(self) -> None:
        if self.worker and self.worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Aguarde", "Ja existe um backup em andamento.")
            return

        self.btn_backup.setEnabled(False)
        self.btn_backup.setText(" Gerando backup...")
        self.worker = BackupWorker()
        self.worker.finalizado.connect(self.on_backup_finished)
        self.worker.start()

    def on_backup_finished(self, msg: str, sucesso: bool) -> None:
        self.btn_backup.setEnabled(True)
        self.btn_backup.setText(" Fazer backup agora")
        self.carregar_backups_disponiveis()

        if sucesso:
            QtWidgets.QMessageBox.information(self, "Backup concluido", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Falha no backup", msg)

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def carregar_backups_disponiveis(self) -> None:
        self.cb_backups.clear()
        backups = listar_backups_disponiveis()
        for item in backups:
            data_txt = QtCore.QDateTime.fromSecsSinceEpoch(int(item["mtime"])).toString("dd/MM/yyyy HH:mm")
            label = f"{item['origem']} | {data_txt} | {item['nome']}"
            self.cb_backups.addItem(label, str(item["path"]))

        if backups:
            self.lbl_backup_status.setText(f"{len(backups)} backup(s) disponiveis para restauracao.")
        else:
            self.lbl_backup_status.setText("Nenhum backup encontrado ainda.")

    def restaurar_backup_selecionado(self) -> None:
        caminho = self.cb_backups.currentData()
        if not caminho:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um backup para restaurar.")
            return

        resposta = QtWidgets.QMessageBox.question(
            self,
            "Restaurar backup",
            "Essa acao substitui os dados atuais pelos dados do backup selecionado.\n\nDeseja continuar?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if resposta != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.db.restore_from_backup(caminho)
            self.recarregar_tabelas()
            if self.main:
                self.main.recarregar_dados_apos_restore()
            QtWidgets.QMessageBox.information(self, "Sucesso", "Backup restaurado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao restaurar backup")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel restaurar o backup:\n{exc}")

    def _setup_motoristas(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.tab_motoristas)
        form_layout = QtWidgets.QHBoxLayout()
        self.ed_mot_cod = QtWidgets.QLineEdit()
        self.ed_mot_cod.setPlaceholderText("Codigo (ex: 1050)")
        self.ed_mot_nome = QtWidgets.QLineEdit()
        self.ed_mot_nome.setPlaceholderText("Nome do motorista")
        btn_add = QtWidgets.QPushButton("Adicionar")
        btn_add.setObjectName("SuccessButton")
        btn_add.clicked.connect(self.add_motorista)

        form_layout.addWidget(QtWidgets.QLabel("Cod:"))
        form_layout.addWidget(self.ed_mot_cod)
        form_layout.addWidget(QtWidgets.QLabel("Nome:"))
        form_layout.addWidget(self.ed_mot_nome)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        self.tb_mot = QtWidgets.QTableWidget()
        self.tb_mot.setColumnCount(2)
        self.tb_mot.setHorizontalHeaderLabels(["Codigo", "Nome"])
        self.tb_mot.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tb_mot.setAlternatingRowColors(True)
        layout.addWidget(self.tb_mot)

        btn_del = QtWidgets.QPushButton("Excluir selecionado")
        btn_del.setObjectName("SecondaryButton")
        btn_del.clicked.connect(lambda: self.excluir_item("motoristas", self.tb_mot))
        layout.addWidget(btn_del)
        self.carregar_motoristas()

    def add_motorista(self) -> None:
        codigo = self.ed_mot_cod.text().strip()
        nome = self.ed_mot_nome.text().strip()
        if not codigo or not nome:
            return
        try:
            self.db.adicionar_motorista(codigo, nome)
            self.carregar_motoristas()
            self.ed_mot_cod.clear()
            self.ed_mot_nome.clear()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Erro", str(exc))

    def carregar_motoristas(self) -> None:
        self._preencher_tabela(self.tb_mot, self.db.listar_motoristas())

    def _setup_fazendas(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.tab_fazendas)
        form_layout = QtWidgets.QHBoxLayout()
        self.ed_faz_cod = QtWidgets.QLineEdit()
        self.ed_faz_cod.setPlaceholderText("Codigo (ex: 100-001)")
        self.ed_faz_nome = QtWidgets.QLineEdit()
        self.ed_faz_nome.setPlaceholderText("Nome da fazenda")
        btn_add = QtWidgets.QPushButton("Adicionar")
        btn_add.setObjectName("SuccessButton")
        btn_add.clicked.connect(self.add_fazenda)

        form_layout.addWidget(QtWidgets.QLabel("Cod:"))
        form_layout.addWidget(self.ed_faz_cod)
        form_layout.addWidget(QtWidgets.QLabel("Nome:"))
        form_layout.addWidget(self.ed_faz_nome)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        self.tb_faz = QtWidgets.QTableWidget()
        self.tb_faz.setColumnCount(2)
        self.tb_faz.setHorizontalHeaderLabels(["Codigo", "Nome"])
        self.tb_faz.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tb_faz.setAlternatingRowColors(True)
        layout.addWidget(self.tb_faz)

        btn_del = QtWidgets.QPushButton("Excluir selecionado")
        btn_del.setObjectName("SecondaryButton")
        btn_del.clicked.connect(lambda: self.excluir_item("fazendas", self.tb_faz))
        layout.addWidget(btn_del)
        self.carregar_fazendas()

    def add_fazenda(self) -> None:
        codigo = self.ed_faz_cod.text().strip()
        nome = self.ed_faz_nome.text().strip()
        if not codigo or not nome:
            return
        try:
            self.db.adicionar_fazenda(codigo, nome)
            self.carregar_fazendas()
            self.ed_faz_cod.clear()
            self.ed_faz_nome.clear()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Erro", str(exc))

    def carregar_fazendas(self) -> None:
        self._preencher_tabela(self.tb_faz, self.db.listar_fazendas())

    def _setup_variedades(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.tab_variedades)
        form_layout = QtWidgets.QHBoxLayout()
        self.ed_var_nome = QtWidgets.QLineEdit()
        self.ed_var_nome.setPlaceholderText("Nome da variedade")
        btn_add = QtWidgets.QPushButton("Adicionar")
        btn_add.setObjectName("SuccessButton")
        btn_add.clicked.connect(self.add_variedade)

        form_layout.addWidget(QtWidgets.QLabel("Nome:"))
        form_layout.addWidget(self.ed_var_nome)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)

        self.tb_var = QtWidgets.QTableWidget()
        self.tb_var.setColumnCount(2)
        self.tb_var.setHorizontalHeaderLabels(["ID", "Nome"])
        self.tb_var.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.tb_var.setAlternatingRowColors(True)
        layout.addWidget(self.tb_var)

        btn_del = QtWidgets.QPushButton("Excluir selecionado")
        btn_del.setObjectName("SecondaryButton")
        btn_del.clicked.connect(lambda: self.excluir_item("variedades", self.tb_var))
        layout.addWidget(btn_del)
        self.carregar_variedades()

    def add_variedade(self) -> None:
        nome = self.ed_var_nome.text().strip()
        if not nome:
            return
        try:
            self.db.adicionar_variedade(nome)
            self.carregar_variedades()
            self.ed_var_nome.clear()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Erro", str(exc))

    def carregar_variedades(self) -> None:
        self._preencher_tabela(self.tb_var, self.db.listar_variedades())

    def recarregar_tabelas(self) -> None:
        self.carregar_motoristas()
        self.carregar_fazendas()
        self.carregar_variedades()
        self.carregar_backups_disponiveis()

    def _preencher_tabela(self, tabela, dados) -> None:
        tabela.setRowCount(0)
        tabela.setSortingEnabled(False)
        for row_index, row in enumerate(dados):
            tabela.insertRow(row_index)
            for col_index, value in enumerate(row):
                tabela.setItem(row_index, col_index, QtWidgets.QTableWidgetItem(str(value)))
        tabela.setSortingEnabled(True)

    def excluir_item(self, tabela: str, widget_tabela) -> None:
        row_index = widget_tabela.currentRow()
        if row_index < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione uma linha.")
            return

        valor_id = widget_tabela.item(row_index, 0).text()
        resposta = QtWidgets.QMessageBox.question(
            self,
            "Confirmacao",
            "Tem certeza que deseja excluir o item selecionado?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if resposta != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.db.excluir_cadastro(tabela, valor_id)
            if tabela == "motoristas":
                self.carregar_motoristas()
            elif tabela == "fazendas":
                self.carregar_fazendas()
            elif tabela == "variedades":
                self.carregar_variedades()
        except Exception as exc:
            LOGGER.exception("Falha ao excluir item de %s", tabela)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao excluir item:\n{exc}")
