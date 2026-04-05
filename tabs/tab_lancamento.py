from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from app_logging import get_logger
from components import DialogoComparacao
from styles import aplicar_icone, set_state


LOGGER = get_logger(__name__)


class TabLancamento(QtWidgets.QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main = main_window
        self._numero_em_edicao = None
        self.val_int_nota = QtGui.QIntValidator(1, 999999999, self)
        self._compl_motoristas = None
        self._compl_fazendas = None
        self._compl_variedades = None

        self._setup_ui()
        self._conectar_sinais()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.lbl_titulo = QtWidgets.QLabel("Novo Lancamento")
        font = self.lbl_titulo.font()
        font.setPointSize(14)
        font.setBold(True)
        self.lbl_titulo.setFont(font)

        self.lbl_modo = QtWidgets.QLabel("")
        self.lbl_modo.setStyleSheet("color: #f6ad55; font-weight: bold;")
        self.lbl_modo.hide()

        self.chk_manter = QtWidgets.QCheckBox(" Manter carga")
        self.chk_manter.setCursor(QtCore.Qt.PointingHandCursor)
        self.chk_manter.setToolTip("Mantem fazenda e variedade do lancamento anterior para agilizar a digitacao.")
        chk_font = self.chk_manter.font()
        chk_font.setPointSize(10)
        chk_font.setBold(True)
        self.chk_manter.setFont(chk_font)
        self.chk_manter.stateChanged.connect(self._atualizar_estado_manter_carga)

        top.addWidget(self.lbl_titulo)
        top.addSpacing(4)
        top.addWidget(self.lbl_modo)
        top.addStretch()
        self.lbl_hint = QtWidgets.QLabel("Digite codigo ou nome completo nos campos de cadastro.")
        self.lbl_hint.setObjectName("WindowSubtitle")
        top.addWidget(self.lbl_hint)
        top.addSpacing(10)
        top.addWidget(self.chk_manter)
        layout.addLayout(top)

        form = QtWidgets.QHBoxLayout()
        form.setSpacing(10)

        grupo_viagem = QtWidgets.QGroupBox(" VIAGEM")
        layout_viagem = QtWidgets.QVBoxLayout(grupo_viagem)
        layout_viagem.setContentsMargins(12, 10, 12, 10)
        layout_viagem.setSpacing(2)

        self.ed_num = QtWidgets.QLineEdit()
        self.ed_num.setValidator(self.val_int_nota)
        self.ed_num.setPlaceholderText("000000")
        self.ed_num.setAlignment(QtCore.Qt.AlignCenter)
        numero_font = self.ed_num.font()
        numero_font.setPointSize(16)
        numero_font.setBold(True)
        self.ed_num.setFont(numero_font)
        self.ed_num.setStyleSheet("color: #5a67d8; border: 2px solid #5a67d8;")

        self.ed_mot = QtWidgets.QLineEdit()
        self.ed_mot.setPlaceholderText("Digite codigo ou nome do motorista")
        self.ed_cam = QtWidgets.QLineEdit()
        self.ed_cam.setPlaceholderText("Placa ou identificacao do caminhao")
        self.ed_op = QtWidgets.QLineEdit()
        self.ed_op.setPlaceholderText("Operador da colhedora")
        self.ed_col = QtWidgets.QLineEdit()
        self.ed_col.setPlaceholderText("Numero da colhedora")

        for widget in (self.ed_num, self.ed_mot, self.ed_cam, self.ed_op, self.ed_col):
            widget.setMinimumHeight(32)
            widget.setMaximumHeight(32)

        self._add_field(layout_viagem, "NUMERO DA NOTA:", self.ed_num)
        self._add_field(layout_viagem, "MOTORISTA:", self.ed_mot)
        self._add_field(layout_viagem, "CAMINHAO:", self.ed_cam)
        self._add_field(layout_viagem, "OPERADOR:", self.ed_op)
        self._add_field(layout_viagem, "COLHEDORA:", self.ed_col)
        layout_viagem.addStretch()
        form.addWidget(grupo_viagem, 1)

        grupo_carga = QtWidgets.QGroupBox(" CARGA")
        layout_carga = QtWidgets.QVBoxLayout(grupo_carga)
        layout_carga.setContentsMargins(12, 10, 12, 10)
        layout_carga.setSpacing(2)

        self.ed_fmuda = QtWidgets.QLineEdit()
        self.ed_fmuda.setPlaceholderText("Fazenda de origem")
        self.ed_talhao = QtWidgets.QLineEdit()
        self.ed_talhao.setPlaceholderText("Talhao")
        self.ed_fplant = QtWidgets.QLineEdit()
        self.ed_fplant.setPlaceholderText("Fazenda de destino")
        self.ed_var = QtWidgets.QLineEdit()
        self.ed_var.setPlaceholderText("Variedade")

        for widget in (self.ed_fmuda, self.ed_talhao, self.ed_fplant, self.ed_var):
            widget.setMinimumHeight(32)
            widget.setMaximumHeight(32)

        self._add_field(layout_carga, "FAZENDA MUDA (ORIGEM):", self.ed_fmuda)
        self._add_field(layout_carga, "FAZENDA PLANTIO (DESTINO):", self.ed_fplant)

        row_mista = QtWidgets.QHBoxLayout()
        row_mista.addWidget(self._wrap_label_widget("VARIEDADE:", self.ed_var), 3)
        row_mista.addWidget(self._wrap_label_widget("TALHAO:", self.ed_talhao), 1)
        layout_carga.addLayout(row_mista)

        self.dt_col = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dt_col.setCalendarPopup(True)
        self.dt_col.setDisplayFormat("dd/MM/yyyy")
        self.dt_pla = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dt_pla.setCalendarPopup(True)
        self.dt_pla.setDisplayFormat("dd/MM/yyyy")
        self._sincronizar_limite_datas()
        self.dt_col.setMinimumHeight(32)
        self.dt_col.setMaximumHeight(32)
        self.dt_pla.setMinimumHeight(32)
        self.dt_pla.setMaximumHeight(32)

        row_datas = QtWidgets.QHBoxLayout()
        row_datas.setSpacing(8)
        row_datas.addWidget(self._wrap_label_widget("DATA COLHEITA:", self.dt_col))
        row_datas.addWidget(self._wrap_label_widget("DATA PLANTIO:", self.dt_pla))
        layout_carga.addLayout(row_datas)
        layout_carga.addStretch()

        form.addWidget(grupo_carga, 1)
        layout.addLayout(form)

        botoes = QtWidgets.QHBoxLayout()
        botoes.setContentsMargins(0, 2, 0, 0)

        btn_limpar = QtWidgets.QPushButton(" Limpar (Esc)")
        btn_limpar.setObjectName("SecondaryButton")
        btn_limpar.setMinimumHeight(36)
        btn_limpar.setMaximumHeight(36)
        aplicar_icone(btn_limpar, "fa5s.eraser")
        btn_limpar.clicked.connect(self._limpar)

        self.b_lancar = QtWidgets.QPushButton(" Lancar nota (F12)")
        self.b_lancar.setObjectName("PrimaryButton")
        self.b_lancar.setMinimumHeight(36)
        self.b_lancar.setMaximumHeight(36)
        self.b_lancar.setStyleSheet("font-size: 11pt;")
        aplicar_icone(self.b_lancar, "fa5s.check")
        self.b_lancar.clicked.connect(self._lancar)

        botoes.addWidget(btn_limpar)
        botoes.addWidget(self.b_lancar)
        layout.addLayout(botoes)

        self._configurar_autocomplete()
        self._atualizar_estado_manter_carga()

        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, activated=self._limpar)
        QtWidgets.QShortcut(QtGui.QKeySequence("F12"), self, activated=self._lancar)

    def _add_field(self, layout_destino, label_texto: str, widget) -> None:
        label = QtWidgets.QLabel(label_texto)
        label.setStyleSheet("color: #a0aec0; font-weight: bold; font-size: 9pt;")
        layout_destino.addWidget(label)
        layout_destino.addWidget(widget)

    def _wrap_label_widget(self, label_texto: str, widget) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        label = QtWidgets.QLabel(label_texto)
        label.setStyleSheet("color: #a0aec0; font-weight: bold; font-size: 9pt;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return container

    def _conectar_sinais(self) -> None:
        for widget in (self.ed_mot, self.ed_op, self.ed_fmuda, self.ed_fplant, self.ed_var):
            widget.editingFinished.connect(lambda w=widget: self._buscar_auto(w))

        self.ed_num.returnPressed.connect(self.ed_mot.setFocus)
        self.ed_mot.returnPressed.connect(self.ed_cam.setFocus)
        self.ed_cam.returnPressed.connect(self.ed_op.setFocus)
        self.ed_op.returnPressed.connect(self.ed_col.setFocus)
        self.ed_col.returnPressed.connect(self._navegar_pos_colhedora)
        self.ed_fmuda.returnPressed.connect(self.ed_talhao.setFocus)
        self.ed_talhao.returnPressed.connect(self.ed_fplant.setFocus)
        self.ed_fplant.returnPressed.connect(self.ed_var.setFocus)

    def _atualizar_estado_manter_carga(self) -> None:
        manter = self.chk_manter.isChecked()
        for widget in (self.ed_fmuda, self.ed_fplant, self.ed_var):
            widget.setReadOnly(manter)
            widget.setFocusPolicy(QtCore.Qt.NoFocus if manter else QtCore.Qt.StrongFocus)
            if manter:
                widget.setStyleSheet("background-color: #10161f; color: #65788d; border: 1px solid #2b3b4c;")
            else:
                widget.setStyleSheet("")

    def _navegar_pos_colhedora(self) -> None:
        if self.chk_manter.isChecked():
            self.ed_talhao.setFocus()
            self.ed_talhao.selectAll()
        else:
            self.ed_fmuda.setFocus()

    def _configurar_autocomplete(self) -> None:
        def criar_completer(lista):
            completer = QtWidgets.QCompleter(lista, self)
            completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            if hasattr(completer, "setFilterMode"):
                completer.setFilterMode(QtCore.Qt.MatchContains)
            return completer

        try:
            motoristas = [f"{row[0]} - {row[1]}" for row in self.db.listar_motoristas()]
            compl_mot = criar_completer(motoristas)
            compl_op = criar_completer(motoristas)
            self._compl_motoristas = (compl_mot, compl_op)
            self.ed_mot.setCompleter(compl_mot)
            self.ed_op.setCompleter(compl_op)

            fazendas = [f"{row[0]} - {row[1]}" for row in self.db.listar_fazendas()]
            compl_fmuda = criar_completer(fazendas)
            compl_fplant = criar_completer(fazendas)
            self._compl_fazendas = (compl_fmuda, compl_fplant)
            self.ed_fmuda.setCompleter(compl_fmuda)
            self.ed_fplant.setCompleter(compl_fplant)

            variedades = [f"{row[0]} - {row[1]}" for row in self.db.listar_variedades()]
            self._compl_variedades = criar_completer(variedades)
            self.ed_var.setCompleter(self._compl_variedades)
        except Exception:
            LOGGER.exception("Falha ao configurar autocomplete")

    def recarregar_referencias(self) -> None:
        self._configurar_autocomplete()

    def carregar_nota_para_edicao(self, numero) -> None:
        nota = self.db.buscar_nota(numero)
        if not nota:
            QtWidgets.QMessageBox.warning(self, "Aviso", f"Nota {numero} nao encontrada.")
            return

        dado = dict(nota)
        self._numero_em_edicao = int(dado["numero"])
        self.chk_manter.setChecked(False)
        self.ed_num.setText(str(dado["numero"]))
        self.ed_num.setReadOnly(True)
        self.ed_mot.setText(self._formatar_codigo_nome(dado["motorista_cod"], dado["motorista_nome"]))
        self.ed_cam.setText(dado["caminhao"] or "")
        self.ed_op.setText(self._formatar_codigo_nome(dado["operador_cod"], dado["operador_nome"]))
        self.ed_col.setText(dado["colhedora"] or "")
        self.ed_fmuda.setText(self._formatar_codigo_nome(dado["faz_muda_cod"], dado["faz_muda_nome"]))
        self.ed_talhao.setText(dado["talhao"] or "")
        self.ed_fplant.setText(self._formatar_codigo_nome(dado["faz_plantio_cod"], dado["faz_plantio_nome"]))
        self.ed_var.setText(self._formatar_codigo_nome(dado["variedade_id"], dado["variedade_nome"]))

        if dado["data_colheita"]:
            self.dt_col.setDate(QtCore.QDate.fromString(dado["data_colheita"], "yyyy-MM-dd"))
        if dado["data_plantio"]:
            self.dt_pla.setDate(QtCore.QDate.fromString(dado["data_plantio"], "yyyy-MM-dd"))

        self.lbl_titulo.setText(f"Editar nota {numero}")
        self.lbl_modo.setText("Modo edicao ativo")
        self.lbl_modo.show()
        self.b_lancar.setText(" Salvar alteracoes")
        self.b_lancar.setObjectName("SuccessButton")
        self.b_lancar.style().unpolish(self.b_lancar)
        self.b_lancar.style().polish(self.b_lancar)
        self.main.tabs.setCurrentWidget(self)
        self.ed_mot.setFocus()

    def _formatar_codigo_nome(self, codigo, nome) -> str:
        codigo_txt = "" if codigo in (None, "") else str(codigo)
        nome_txt = "" if nome in (None, "") else str(nome)
        if codigo_txt and nome_txt:
            return f"{codigo_txt} - {nome_txt}"
        return codigo_txt or nome_txt

    def _extrair(self, widget: QtWidgets.QLineEdit):
        texto = (widget.text() or "").strip()
        if " - " in texto:
            codigo, nome = texto.split(" - ", 1)
            return codigo.strip(), nome.strip()
        return texto, None

    def _buscar_auto(self, widget: QtWidgets.QLineEdit) -> None:
        texto = (widget.text() or "").strip()
        if not texto or " - " in texto:
            return

        referencia = self._resolver_referencia_widget(widget)
        if referencia:
            campo_id = "id" if widget == self.ed_var else "codigo"
            widget.setText(f"{referencia[campo_id]} - {referencia['nome']}")

    def _resolver_referencia_widget(self, widget: QtWidgets.QLineEdit):
        if widget in (self.ed_mot, self.ed_op):
            return self.db.resolver_referencia("motoristas", widget.text(), col_id="codigo")
        if widget in (self.ed_fmuda, self.ed_fplant):
            return self.db.resolver_referencia("fazendas", widget.text(), col_id="codigo")
        if widget == self.ed_var:
            return self.db.resolver_referencia("variedades", widget.text(), col_id="id")
        return None

    def _sincronizar_limite_datas(self) -> QtCore.QDate:
        hoje = QtCore.QDate.currentDate()
        for widget in (self.dt_col, self.dt_pla):
            widget.setMaximumDate(hoje)
            calendario = widget.calendarWidget()
            if calendario is not None:
                calendario.setMaximumDate(hoje)
        return hoje

    def _validar_datas(self) -> bool:
        hoje = self._sincronizar_limite_datas()
        campos_invalidos = []
        for widget, label in (
            (self.dt_col, "Data de colheita"),
            (self.dt_pla, "Data de plantio"),
        ):
            if widget.date() > hoje:
                set_state(widget, "error")
                campos_invalidos.append(label)

        if not campos_invalidos:
            return True

        hoje_br = hoje.toString("dd/MM/yyyy")
        QtWidgets.QMessageBox.warning(
            self,
            "Datas invalidas",
            "Nao e permitido lancar notas com data futura.\n"
            f"Revise: {', '.join(campos_invalidos)}.\n"
            f"Data atual do sistema: {hoje_br}.",
        )
        return False

    def _validar_campos(self) -> bool:
        valido = True
        self._sincronizar_limite_datas()
        for widget in (self.ed_num, self.ed_mot, self.ed_fplant, self.ed_var, self.dt_col, self.dt_pla):
            set_state(widget, "")

        if not (self.ed_num.text() or "").strip():
            set_state(self.ed_num, "error")
            valido = False

        motorista = self._resolver_referencia_widget(self.ed_mot)
        if not motorista:
            set_state(self.ed_mot, "warn")
            valido = False

        fazenda_destino = self._resolver_referencia_widget(self.ed_fplant)
        if not fazenda_destino:
            set_state(self.ed_fplant, "warn")
            valido = False

        variedade = self._resolver_referencia_widget(self.ed_var)
        if not variedade:
            set_state(self.ed_var, "warn")
            valido = False

        if not valido:
            QtWidgets.QMessageBox.warning(
                self,
                "Campos invalidos",
                "Revise os campos obrigatorios e confira os cadastros digitados.",
            )
            return False

        return self._validar_datas()

    def _lancar(self) -> None:
        if not self._validar_campos():
            return

        motorista = self._resolver_referencia_widget(self.ed_mot)
        operador = self._resolver_referencia_widget(self.ed_op)
        fazenda_muda = self._resolver_referencia_widget(self.ed_fmuda)
        fazenda_plantio = self._resolver_referencia_widget(self.ed_fplant)
        variedade = self._resolver_referencia_widget(self.ed_var)

        payload = {
            "numero": int(self.ed_num.text()),
            "motorista_cod": motorista["codigo"] if motorista else None,
            "motorista_nome": motorista["nome"] if motorista else None,
            "caminhao": (self.ed_cam.text() or "").strip(),
            "operador_cod": operador["codigo"] if operador else None,
            "operador_nome": operador["nome"] if operador else None,
            "colhedora": (self.ed_col.text() or "").strip(),
            "faz_muda_cod": fazenda_muda["codigo"] if fazenda_muda else None,
            "faz_muda_nome": fazenda_muda["nome"] if fazenda_muda else None,
            "talhao": (self.ed_talhao.text() or "").strip(),
            "faz_plantio_cod": fazenda_plantio["codigo"] if fazenda_plantio else None,
            "faz_plantio_nome": fazenda_plantio["nome"] if fazenda_plantio else None,
            "variedade_id": variedade["id"] if variedade else None,
            "variedade_nome": variedade["nome"] if variedade else None,
            "data_colheita": self.dt_col.date().toString("yyyy-MM-dd"),
            "data_plantio": self.dt_pla.date().toString("yyyy-MM-dd"),
        }

        try:
            numero = payload["numero"]
            existente = self.db.buscar_nota(numero)
            if self._numero_em_edicao == numero:
                self.db.inserir_nota(payload, force=True)
            elif existente:
                dialogo = DialogoComparacao(self, numero, existente, payload)
                if dialogo.exec_() == QtWidgets.QDialog.Accepted:
                    if dialogo.resultado == "sobrescrever":
                        self.db.inserir_nota(payload, force=True)
                    elif dialogo.resultado == "duplicar":
                        payload["numero"] = int(f"{numero}0")
                        self.db.inserir_nota(payload)
                    else:
                        return
                else:
                    return
            else:
                self.db.inserir_nota(payload)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "Datas invalidas", str(exc))
            return
        except Exception as exc:
            LOGGER.exception("Falha ao salvar nota")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Nao foi possivel salvar a nota:\n{exc}")
            return

        self.main.status.showMessage("Nota salva com sucesso.", 2500)
        self.main._atualizar_contadores()
        try:
            self.main.tab_hist.carregar_dados(self.main.tab_hist._usar_filtro_atual)
        except Exception:
            LOGGER.exception("Falha ao recarregar historico apos salvar nota")
        self._limpar_campos()

    def _limpar_campos(self) -> None:
        self._sincronizar_limite_datas()
        self.ed_num.clear()
        self.ed_cam.clear()
        self.ed_op.clear()
        self.ed_col.clear()
        self.ed_mot.clear()

        for widget in (self.ed_num, self.ed_mot, self.ed_fplant, self.ed_var, self.dt_col, self.dt_pla):
            set_state(widget, "")

        if not self.chk_manter.isChecked():
            self.ed_talhao.clear()
            self.ed_fmuda.clear()
            self.ed_fplant.clear()
            self.ed_var.clear()
        else:
            self.ed_talhao.clear()

        self._numero_em_edicao = None
        self.ed_num.setReadOnly(False)
        self.lbl_titulo.setText("Novo Lancamento")
        self.lbl_modo.hide()
        self.b_lancar.setText(" Lancar nota (F12)")
        self.b_lancar.setObjectName("PrimaryButton")
        self.b_lancar.style().unpolish(self.b_lancar)
        self.b_lancar.style().polish(self.b_lancar)
        self._atualizar_estado_manter_carga()
        self.ed_num.setFocus()

    def _limpar(self) -> None:
        self.chk_manter.setChecked(False)
        self._limpar_campos()
