from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from app_logging import get_logger


LOGGER = get_logger(__name__)

try:
    import qtawesome as qta

    ICONS_AVAILABLE = True
except Exception:
    qta = None
    ICONS_AVAILABLE = False


_ICON_CACHE = {}


def get_icon(nome_icone: str, cor: str = "white"):
    if not ICONS_AVAILABLE or not nome_icone:
        return None
    key = (str(nome_icone), str(cor))
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    icon = qta.icon(nome_icone, color=cor)
    _ICON_CACHE[key] = icon
    return icon


def aplicar_icone(botao, nome_icone, cor="white", size=18):
    icon = get_icon(nome_icone, cor=cor)
    if icon is None:
        return False
    botao.setIcon(icon)
    botao.setIconSize(QtCore.QSize(int(size), int(size)))
    return True


def set_state(widget: QtWidgets.QWidget, state: str = ""):
    widget.setProperty("state", state)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def apply_theme(app_or_widget):
    if app_or_widget is None:
        LOGGER.warning("apply_theme chamado antes da criacao da QApplication")
        return False

    try:
        app_or_widget.setStyleSheet(PREMIUM_STYLESHEET)
        LOGGER.info("Tema visual aplicado com sucesso")
        return True
    except Exception:
        LOGGER.exception("Erro ao aplicar tema visual")
        return False


class StatusDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        texto = index.data()
        texto_upper = str(texto).upper() if texto else ""

        cor_fundo = None
        if texto_upper == "ATIVO":
            cor_fundo = QtGui.QColor("#2e8b57")
        elif texto_upper in ["MANUTENCAO", "MANUTENÇÃO", "QUEBRADO"]:
            cor_fundo = QtGui.QColor("#b4493e")
        elif texto_upper == "DUPLICADO":
            cor_fundo = QtGui.QColor("#bb8740")

        if cor_fundo:
            painter.save()
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            rect = option.rect.adjusted(4, 4, -4, -4)
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(rect), 7, 7)
            painter.fillPath(path, cor_fundo)
            painter.setPen(QtGui.QColor("white"))
            font = painter.font()
            font.setBold(True)
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(rect, QtCore.Qt.AlignCenter, str(texto))
            painter.restore()
        else:
            super().paint(painter, option, index)


PREMIUM_STYLESHEET = """
* {
    font-family: "Segoe UI", "Roboto", sans-serif;
}

QWidget {
    background-color: #0d1116;
    color: #d8dde4;
    font-size: 11pt;
}

QToolTip {
    background-color: #0a0e13;
    color: #eef2f6;
    border: 1px solid #334154;
    padding: 8px;
    border-radius: 6px;
}

QFrame#Card {
    background-color: #121821;
    border: 1px solid #253243;
    border-radius: 14px;
    margin: 5px;
}

QFrame#CardSoft {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #111925, stop:1 #0f141c);
    border: 1px solid #223041;
    border-radius: 16px;
}

QLabel#WindowTitle {
    font-size: 16pt;
    font-weight: 800;
    color: #f2f5f8;
}

QLabel#WindowSubtitle {
    font-size: 9pt;
    color: #8ea1b5;
}

QLabel#SplashSubtitle {
    color: #7ec8e3;
    font-weight: 700;
}

QLabel#StatusChipOnline, QLabel#StatusChipOffline, QLabel#StatusChipNeutral,
QLabel#StatusMetricGreen, QLabel#StatusMetricBlue {
    font-weight: 700;
    border-radius: 9px;
    padding: 3px 9px;
}

QLabel#StatusChipOnline {
    background-color: #143928;
    color: #8fddb0;
    border: 1px solid #1f6944;
}

QLabel#StatusChipOffline {
    background-color: #412411;
    color: #ffc48a;
    border: 1px solid #8d532a;
}

QLabel#StatusChipNeutral {
    background-color: #142334;
    color: #9bc4f0;
    border: 1px solid #315377;
}

QLabel#StatusMetricGreen {
    background-color: #10271b;
    color: #89d2a6;
    border: 1px solid #24593b;
    margin-left: 6px;
}

QLabel#StatusMetricBlue {
    background-color: #112235;
    color: #8bbbe9;
    border: 1px solid #264f76;
    margin-left: 6px;
}

QGroupBox {
    border: 1px solid #263547;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: #121821;
    font-weight: 700;
    color: #d8dde4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    top: 0px;
    background-color: #121821;
    padding: 0 5px 0 5px;
    color: #eef2f6;
}

QTabWidget::pane {
    border: 1px solid #243446;
    background-color: #121821;
    border-radius: 14px;
    margin-top: -1px;
}

QTabBar::tab {
    background-color: #10161f;
    color: #7b8fa2;
    padding: 9px 18px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 4px;
    font-weight: 700;
    border: 1px solid #223142;
    border-bottom: none;
}

QTabBar::tab:hover {
    color: #bfd0e2;
    background-color: #141d28;
}

QTabBar::tab:selected {
    background-color: #17202b;
    color: #eef2f6;
    border: 1px solid #345170;
}

QLineEdit, QComboBox, QDateEdit, QTimeEdit, QTextEdit, QPlainTextEdit {
    padding: 3px 8px;
    border: 2px solid #243243;
    border-radius: 10px;
    background-color: #0b1118;
    color: #e2e5ea;
    font-size: 10pt;
    min-height: 28px;
    selection-background-color: #30597b;
    selection-color: #ffffff;
}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus,
QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #6ca6d8;
    background-color: #0a1017;
}

QLineEdit[state="error"], QComboBox[state="error"], QDateEdit[state="error"],
QTimeEdit[state="error"], QTextEdit[state="error"], QPlainTextEdit[state="error"] {
    border: 2px solid #d05a5a;
    background-color: #1a1010;
}

QLineEdit[state="ok"], QComboBox[state="ok"], QDateEdit[state="ok"],
QTimeEdit[state="ok"], QTextEdit[state="ok"], QPlainTextEdit[state="ok"] {
    border: 2px solid #6bbf7a;
    background-color: #101a12;
}

QLineEdit[state="warn"], QComboBox[state="warn"], QDateEdit[state="warn"],
QTimeEdit[state="warn"], QTextEdit[state="warn"], QPlainTextEdit[state="warn"] {
    border: 2px solid #caa64a;
    background-color: #19150c;
}

QCheckBox {
    color: #d8dde4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #243243;
    border-radius: 4px;
    background-color: #0b1118;
}

QCheckBox::indicator:checked {
    background-color: #6ca6d8;
    border: 2px solid #6ca6d8;
    image: none;
}

QPushButton {
    font-weight: 700;
    border-radius: 10px;
    padding: 7px 16px;
    font-size: 10pt;
    border: 1px solid transparent;
    min-height: 34px;
}

QPushButton:hover {
    border: 1px solid #4a617a;
}

QPushButton:pressed {
    padding-top: 12px;
    padding-bottom: 8px;
}

QPushButton:disabled {
    background-color: #24262d;
    color: #7a818c;
    border: 1px solid #2a2d34;
}

QPushButton#PrimaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #31577b, stop:1 #203b54);
    color: #eef2f6;
    border: 1px solid #47729a;
}

QPushButton#PrimaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3c678f, stop:1 #264866);
}

QPushButton#SecondaryButton {
    background-color: #151d28;
    color: #d8dde4;
    border: 1px solid #263547;
}

QPushButton#SecondaryButton:hover {
    background-color: #1b2532;
}

QPushButton#SuccessButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e7254, stop:1 #1f513b);
    color: #eef2f6;
    border: 1px solid #2f7a59;
}

QPushButton#SuccessButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #388661, stop:1 #245d45);
}

QPushButton#DangerButton {
    background-color: #6a2d2d;
    color: #f3f3f3;
    border: 1px solid #8a4646;
}

QPushButton#DangerButton:hover {
    background-color: #7b3737;
}

QPushButton#PurpleButton {
    background-color: #2a314f;
    color: #eef2f6;
    border: 1px solid #465989;
}

QPushButton#PurpleButton:hover {
    background-color: #324064;
}

QPushButton#TelegramButton {
    background-color: #0c6a8f;
    color: #eef2f6;
    border: 1px solid #1d91bd;
}

QPushButton#TelegramButton:hover {
    background-color: #0f7ba5;
}

QTableWidget, QTableView {
    background-color: #111720;
    alternate-background-color: #0e141c;
    color: #e2e5ea;
    gridline-color: #233142;
    border: 1px solid #233142;
    selection-background-color: #244561;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #0d131b;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #31495f;
    font-weight: 700;
    color: #9eb4c7;
    text-transform: uppercase;
    font-size: 10pt;
}

QLabel#KPI {
    font-size: 28pt;
    font-weight: 800;
    color: #eff4f8;
}

QLabel#KPITitle {
    font-size: 11pt;
    font-weight: 700;
    color: #86a0b7;
    text-transform: uppercase;
}

QProgressBar {
    border: 2px solid #243243;
    border-radius: 8px;
    text-align: center;
    background-color: #111720;
    color: #eef2f6;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5f95c6, stop:1 #77c59a);
    border-radius: 6px;
}

QScrollBar:vertical {
    background: #111720;
    width: 14px;
    border-radius: 7px;
}

QScrollBar::handle:vertical {
    background: #2c3d50;
    border-radius: 7px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #3d5872;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QStatusBar {
    background-color: #0f151d;
    color: #9eb4c7;
    border-top: 1px solid #243243;
}

QMenu {
    background-color: #121821;
    color: #d8dde4;
    border: 1px solid #243243;
    padding: 6px;
}

QMenu::item {
    padding: 8px 18px;
    border-radius: 8px;
}

QMenu::item:selected {
    background-color: #20364b;
}

QSplashScreen {
    background: transparent;
}
"""
