from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from app_logging import get_logger
from reporting import (
    RelatorioDataService,
    RelatorioFormatacaoMixin,
    RelatorioPdfDiarioBuilder,
    RelatorioPdfGeralBuilder,
    RelatorioPdfSimplificadoBuilder,
)
from styles import aplicar_icone
from workers import TelegramWorker

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    MATPLOTLIB_INSTALADO = True
except ImportError:
    MATPLOTLIB_INSTALADO = False


LOGGER = get_logger(__name__)


class AbaRelatorios(RelatorioFormatacaoMixin, QtWidgets.QWidget):
    def __init__(self, db, main_window_ref):
        super().__init__()
        self.db = db
        self.main_window = main_window_ref
        self.worker_bot = None
        self.graficos = []
        self.relatorio_data = RelatorioDataService(self.db.conn)
        self.relatorio_pdf_diario = RelatorioPdfDiarioBuilder()
        self.relatorio_pdf_geral = RelatorioPdfGeralBuilder()
        self.relatorio_pdf_simplificado = RelatorioPdfSimplificadoBuilder()

        self._setup_ui()
        self.gerar_dashboard()

    def _setup_ui(self) -> None:
        layout_principal = QtWidgets.QVBoxLayout(self)
        layout_principal.setContentsMargins(10, 10, 10, 10)
        layout_principal.setSpacing(15)

        filter_box = QtWidgets.QGroupBox("Controle e Analise")
        filter_layout = QtWidgets.QVBoxLayout(filter_box)
        filter_layout.setSpacing(10)

        self.dt_inicio = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(-30))
        self.dt_inicio.setCalendarPopup(True)
        self.dt_inicio.setDisplayFormat("dd/MM/yyyy")
        self.dt_inicio.setMinimumWidth(120)

        self.dt_fim = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setMinimumWidth(120)

        self.cb_visao = QtWidgets.QComboBox()
        self.cb_visao.addItems(["Diario", "Mensal", "Anual"])
        self.cb_visao.currentIndexChanged.connect(self.gerar_dashboard)
        self.cb_visao.setMinimumWidth(120)

        btn_atualizar = QtWidgets.QPushButton(" Atualizar dados")
        btn_atualizar.setObjectName("PrimaryButton")
        aplicar_icone(btn_atualizar, "fa5s.sync-alt")
        btn_atualizar.clicked.connect(self.gerar_dashboard)
        btn_atualizar.setMinimumHeight(40)

        btn_excel = QtWidgets.QPushButton(" Excel (Fluxo)")
        btn_excel.setObjectName("SuccessButton")
        aplicar_icone(btn_excel, "fa5s.file-excel")
        btn_excel.clicked.connect(self.gerar_excel_fluxo)

        btn_excel_bruto = QtWidgets.QPushButton(" Excel (Bruto)")
        btn_excel_bruto.setObjectName("SuccessButton")
        aplicar_icone(btn_excel_bruto, "fa5s.database")
        btn_excel_bruto.clicked.connect(self.gerar_excel_bruto)

        btn_pdf_diario = QtWidgets.QPushButton(" PDF (Diario)")
        btn_pdf_diario.setObjectName("DangerButton")
        aplicar_icone(btn_pdf_diario, "fa5s.file-pdf")
        btn_pdf_diario.clicked.connect(self.gerar_pdf_resumo)

        btn_pdf_geral = QtWidgets.QPushButton(" PDF (Geral)")
        btn_pdf_geral.setObjectName("PurpleButton")
        aplicar_icone(btn_pdf_geral, "fa5s.file-alt")
        btn_pdf_geral.clicked.connect(self.gerar_pdf_geral_fazenda)

        btn_pdf_simplificado = QtWidgets.QPushButton(" PDF (Simples)")
        btn_pdf_simplificado.setObjectName("SecondaryButton")
        aplicar_icone(btn_pdf_simplificado, "fa5s.list-alt")
        btn_pdf_simplificado.clicked.connect(self.gerar_pdf_simplificado)

        btn_telegram = QtWidgets.QPushButton(" Telegram")
        btn_telegram.setObjectName("TelegramButton")
        btn_telegram.setCursor(QtCore.Qt.PointingHandCursor)
        aplicar_icone(btn_telegram, "fa5s.paper-plane", "white")
        btn_telegram.clicked.connect(self.enviar_relatorio_telegram)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("De:"))
        row1.addWidget(self.dt_inicio)
        row1.addSpacing(15)
        row1.addWidget(QtWidgets.QLabel("Ate:"))
        row1.addWidget(self.dt_fim)
        row1.addSpacing(15)
        row1.addWidget(QtWidgets.QLabel("Visao:"))
        row1.addWidget(self.cb_visao)
        row1.addSpacing(20)
        row1.addWidget(btn_atualizar, 1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(btn_telegram)
        row2.addSpacing(10)
        row2.addWidget(btn_excel)
        row2.addWidget(btn_excel_bruto)
        row2.addWidget(btn_pdf_diario)
        row2.addWidget(btn_pdf_geral)
        row2.addWidget(btn_pdf_simplificado)

        filter_layout.addLayout(row1)
        filter_layout.addLayout(row2)
        layout_principal.addWidget(filter_box)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 0, 20, 20)
        self.content_layout.setSpacing(24)

        kpi_container = QtWidgets.QWidget()
        kpi_layout = QtWidgets.QHBoxLayout(kpi_container)
        kpi_layout.setContentsMargins(8, 8, 8, 8)
        kpi_layout.setSpacing(12)

        self.lbl_kpi_total = QtWidgets.QLabel("0")
        self.lbl_kpi_total.setObjectName("KPI")
        self.lbl_kpi_total.setAlignment(QtCore.Qt.AlignCenter)

        self.lbl_kpi_media = QtWidgets.QLabel("0")
        self.lbl_kpi_media.setObjectName("KPI")
        self.lbl_kpi_media.setAlignment(QtCore.Qt.AlignCenter)

        self.lbl_kpi_dias = QtWidgets.QLabel("0")
        self.lbl_kpi_dias.setObjectName("KPI")
        self.lbl_kpi_dias.setAlignment(QtCore.Qt.AlignCenter)

        kpi_layout.addWidget(self._criar_card_kpi("TOTAL DE VIAGENS", self.lbl_kpi_total))
        kpi_layout.addWidget(self._criar_card_kpi("MEDIA NO PERIODO", self.lbl_kpi_media))
        kpi_layout.addWidget(self._criar_card_kpi("DIAS COM MOVIMENTO", self.lbl_kpi_dias))
        self.content_layout.addWidget(kpi_container)

        if MATPLOTLIB_INSTALADO:
            titulos = [
                "TOP 5 MOTORISTAS",
                "TOP 5 MAQUINISTAS / OPERADORES",
                "TOP 5 COLHEDORAS",
                "VARIEDADES MAIS PLANTADAS",
                "FAZENDAS COM MAIS COLHEITA (ORIGEM)",
                "FAZENDAS COM MAIS PLANTIO (DESTINO)",
            ]
            for titulo in titulos:
                self._adicionar_espaco_grafico(titulo)
        else:
            sem_graf = QtWidgets.QLabel("Instale matplotlib para habilitar os graficos.\nEx.: pip install matplotlib")
            sem_graf.setAlignment(QtCore.Qt.AlignCenter)
            sem_graf.setWordWrap(True)
            self.content_layout.addWidget(sem_graf)

        self.content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout_principal.addWidget(scroll)

    def _criar_card_kpi(self, titulo: str, widget_valor: QtWidgets.QLabel) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        label_titulo = QtWidgets.QLabel(titulo)
        label_titulo.setObjectName("KPITitle")
        label_titulo.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label_titulo)
        layout.addWidget(widget_valor, alignment=QtCore.Qt.AlignCenter)
        return card

    def _adicionar_espaco_grafico(self, titulo: str) -> None:
        fig = Figure(figsize=(10, 4), dpi=100)
        fig.patch.set_facecolor("#121821")
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(350)

        self.graficos.append(
            {
                "titulo": titulo,
                "fig": fig,
                "canvas": canvas,
                "ax": fig.add_subplot(111),
            }
        )
        self.content_layout.addWidget(canvas)

    def _get_datas_sql(self) -> tuple[str, str]:
        return (
            self.dt_inicio.date().toString("yyyy-MM-dd"),
            self.dt_fim.date().toString("yyyy-MM-dd"),
        )

    def _ensure_date_range(self) -> None:
        if self.dt_inicio.date() > self.dt_fim.date():
            self.dt_inicio.setDate(self.dt_fim.date())

    def _coletar_dados_pdf_diario(self, d_ini: str, d_fim: str):
        return self.relatorio_data.coletar_dados_pdf_diario(d_ini, d_fim)

    def _coletar_dados_pdf_simplificado(self, d_ini: str, d_fim: str):
        return self.relatorio_data.coletar_dados_pdf_simplificado(d_ini, d_fim)

    def _coletar_dados_pdf_geral(self, d_ini: str, d_fim: str):
        return self.relatorio_data.coletar_dados_pdf_geral(d_ini, d_fim)

    def _criar_pdf_resumo_diario(self, d_ini: str, d_fim: str):
        dados = self._coletar_dados_pdf_diario(d_ini, d_fim)
        if not dados:
            return None
        return self.relatorio_pdf_diario.criar_pdf_resumo_diario(dados)

    def _criar_pdf_simplificado(self, d_ini: str, d_fim: str):
        dados = self._coletar_dados_pdf_simplificado(d_ini, d_fim)
        if not dados:
            return None
        return self.relatorio_pdf_simplificado.criar_pdf_simplificado(d_ini, d_fim, dados)

    def _criar_pdf_geral_fazenda(self, d_ini: str, d_fim: str):
        dados = self._coletar_dados_pdf_geral(d_ini, d_fim)
        if not dados:
            return None
        return self.relatorio_pdf_geral.criar_pdf_geral_fazenda(d_ini, d_fim, dados)

    def enviar_relatorio_telegram(self) -> None:
        if self.worker_bot and self.worker_bot.isRunning():
            QtWidgets.QMessageBox.information(self, "Aguarde", "Ja existe um envio em andamento.")
            return

        clima_atual = getattr(getattr(self.main_window, "ticker", None), "clima_cache", "N/A")
        self.worker_bot = TelegramWorker(self.db, clima_atual)
        self.worker_bot.sucesso.connect(lambda msg: QtWidgets.QMessageBox.information(self, "Sucesso", msg))
        self.worker_bot.erro.connect(lambda msg: QtWidgets.QMessageBox.warning(self, "Erro", msg))
        self.worker_bot.finished.connect(self._limpar_worker_telegram)
        self.worker_bot.start()

    def _limpar_worker_telegram(self) -> None:
        try:
            self.worker_bot.deleteLater()
        except Exception:
            pass
        self.worker_bot = None

    def gerar_dashboard(self) -> None:
        if not MATPLOTLIB_INSTALADO:
            return

        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()

        colunas = [
            "motorista_nome",
            "operador_nome",
            "colhedora",
            "variedade_nome",
            "faz_muda_nome",
            "faz_plantio_nome",
        ]

        dados_graficos = []
        for coluna in colunas:
            try:
                ranking = self.db.top_por_coluna(coluna, d_ini, d_fim, limit=5)
                nomes = [str(row["nome"]).strip() for row in ranking]
                qtds = [int(row["qtd"]) for row in ranking]
                dados_graficos.append((nomes, qtds))
            except Exception:
                LOGGER.exception("Falha ao montar ranking de %s", coluna)
                dados_graficos.append(([], []))

        try:
            total = self.db.contar_notas_periodo(d_ini, d_fim)
            dias_intervalo = (self.dt_fim.date().toPyDate() - self.dt_inicio.date().toPyDate()).days + 1
            media = total / dias_intervalo if dias_intervalo > 0 else 0
            dias_ativos = self.db.contar_dias_ativos_periodo(d_ini, d_fim)
            self.lbl_kpi_total.setText(f"{total:,}".replace(",", "."))
            self.lbl_kpi_media.setText(f"{media:.1f}/dia")
            self.lbl_kpi_dias.setText(str(dias_ativos))
        except Exception:
            LOGGER.exception("Falha ao atualizar KPI do dashboard")

        cores = ["#4f84b3", "#6880a8", "#5a67d8", "#48bb78", "#f6ad55", "#d97757"]
        for index, item in enumerate(self.graficos):
            ax = item["ax"]
            canvas = item["canvas"]
            fig = item["fig"]
            nomes, qtds = dados_graficos[index]
            cor = cores[index % len(cores)]

            ax.clear()
            if nomes:
                bars = ax.barh(nomes, qtds, color=cor, height=0.62)
                if hasattr(ax, "bar_label"):
                    try:
                        ax.bar_label(bars, color="white", padding=5, fontsize=11, fontweight="bold")
                    except Exception:
                        pass
                ax.invert_yaxis()
                ax.tick_params(axis="y", labelsize=11, labelcolor="#e2e5ea")
                ax.tick_params(axis="x", labelsize=10, labelcolor="#9aa3ae")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "Sem dados\nno periodo",
                    ha="center",
                    va="center",
                    color="#8b93a0",
                    fontsize=14,
                    transform=ax.transAxes,
                )

            ax.set_facecolor("#121821")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color("#243243")
            ax.spines["left"].set_color("#243243")
            ax.set_title(item["titulo"], color="#eef2f6", fontsize=14, fontweight="bold", pad=15)
            fig.subplots_adjust(left=0.3, right=0.95, top=0.9, bottom=0.13)
            canvas.draw()

    def gerar_excel_fluxo(self) -> None:
        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()
        try:
            df = self.db.dataframe_fluxo(d_ini, d_fim)
            if df.empty:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Sem dados no periodo.")
                return

            caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Salvar Excel",
                f"Fluxo_{d_ini}_a_{d_fim}.xlsx",
                "Excel (*.xlsx)",
            )
            if caminho:
                df.to_excel(caminho, index=False)
                QtWidgets.QMessageBox.information(self, "Sucesso", "Excel gerado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao gerar Excel de fluxo")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao gerar Excel:\n{exc}")

    def gerar_excel_bruto(self) -> None:
        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()
        try:
            df = self.db.dataframe_historico(d_ini, d_fim)
            if df.empty:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Sem dados brutos no periodo.")
                return

            nome_arquivo = f"Dados_Brutos_{d_ini}_a_{d_fim}.xlsx"
            caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Salvar Dados Brutos",
                nome_arquivo,
                "Excel (*.xlsx)",
            )
            if caminho:
                df.to_excel(caminho, index=False)
                QtWidgets.QMessageBox.information(self, "Sucesso", f"Arquivo salvo em:\n{caminho}")
        except Exception as exc:
            LOGGER.exception("Falha ao gerar Excel bruto")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao gerar Excel bruto:\n{exc}")

    def gerar_pdf_resumo(self) -> None:
        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()
        try:
            pdf = self._criar_pdf_resumo_diario(d_ini, d_fim)
            if not pdf:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Sem dados no periodo.")
                return

            caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Salvar PDF",
                f"Resumo_Diario_{d_ini}_a_{d_fim}.pdf",
                "PDF (*.pdf)",
            )
            if caminho:
                pdf.output(caminho)
                QtWidgets.QMessageBox.information(self, "Sucesso", "PDF gerado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao gerar PDF diario")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF:\n{exc}")

    def gerar_pdf_geral_fazenda(self) -> None:
        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()
        try:
            pdf = self._criar_pdf_geral_fazenda(d_ini, d_fim)
            if not pdf:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Sem dados no periodo.")
                return

            caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Salvar PDF Analitico",
                f"Relatorio_Fluxo_{d_ini}_a_{d_fim}.pdf",
                "PDF (*.pdf)",
            )
            if caminho:
                pdf.output(caminho)
                QtWidgets.QMessageBox.information(self, "Sucesso", "Relatorio analitico gerado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao gerar PDF geral")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro na geracao do PDF:\n{exc}")

    def gerar_pdf_simplificado(self) -> None:
        self._ensure_date_range()
        d_ini, d_fim = self._get_datas_sql()
        try:
            pdf = self._criar_pdf_simplificado(d_ini, d_fim)
            if not pdf:
                QtWidgets.QMessageBox.warning(self, "Aviso", "Sem dados no periodo.")
                return

            caminho, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Salvar PDF Simplificado",
                f"Relatorio_Simplificado_{d_ini}_a_{d_fim}.pdf",
                "PDF (*.pdf)",
            )
            if caminho:
                pdf.output(caminho)
                QtWidgets.QMessageBox.information(self, "Sucesso", "Relatorio simplificado gerado com sucesso.")
        except Exception as exc:
            LOGGER.exception("Falha ao gerar PDF simplificado")
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao gerar relatorio simplificado:\n{exc}")
