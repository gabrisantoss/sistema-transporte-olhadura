from PyQt5 import QtWidgets, QtCore
import os
import subprocess
from styles import aplicar_icone

class AbaIntegracaoMapa(QtWidgets.QWidget):
    def __init__(self, db=None, main_window=None):
        super().__init__()
        self.db = db
        self.main = main_window
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame { background-color: #25262c; border: 2px solid #3a7bd5; border-radius: 15px; min-width: 450px; min-height: 250px; }")
        fl = QtWidgets.QVBoxLayout(frame); fl.setSpacing(20)
        
        lbl_t = QtWidgets.QLabel("🛰️ SISTEMA DE SATÉLITE")
        lbl_t.setStyleSheet("font-size: 24pt; font-weight: bold; color: white; border: none;")
        lbl_t.setAlignment(QtCore.Qt.AlignCenter)
        
        lbl_d = QtWidgets.QLabel("Visualize o fluxo da safra e talhões em mapas interativos.")
        lbl_d.setStyleSheet("font-size: 12pt; color: #aaa; border: none;")
        lbl_d.setAlignment(QtCore.Qt.AlignCenter)

        self.lbl_status_gps = QtWidgets.QLabel("")
        self.lbl_status_gps.setStyleSheet("font-size: 10.5pt; color: #cfd3d8; border: none;")
        self.lbl_status_gps.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_status_gps.setWordWrap(True)
        
        btn = QtWidgets.QPushButton(" ABRIR MAPEAMENTO")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("QPushButton { background-color: #3a7bd5; color: white; font-size: 14pt; padding: 15px; border-radius: 8px; font-weight: bold; } QPushButton:hover { background-color: #4ea4ff; }")
        btn.clicked.connect(self.abrir_mapa)

        btn_att = QtWidgets.QPushButton(" Atualizar status GPS")
        btn_att.setCursor(QtCore.Qt.PointingHandCursor)
        btn_att.clicked.connect(self.atualizar_status_gps)
        
        fl.addStretch(); fl.addWidget(lbl_t); fl.addWidget(lbl_d); fl.addWidget(self.lbl_status_gps); fl.addWidget(btn); fl.addWidget(btn_att); fl.addStretch()
        layout.addWidget(frame)
        self.atualizar_status_gps()

    def atualizar_status_gps(self):
        if not self.db:
            self.lbl_status_gps.setText("Resumo de GPS indisponível nesta abertura.")
            return
        try:
            resumo = self.db.resumo_gps_fazendas()
            self.lbl_status_gps.setText(
                f"Fazendas cadastradas: {resumo['total']} | Com GPS: {resumo['com_gps']} | Sem GPS: {resumo['sem_gps']}"
            )
        except Exception:
            self.lbl_status_gps.setText("Não foi possível consultar o status de GPS agora.")

    def abrir_mapa(self):
        # Tenta abrir o EXE ou o Python
        arquivos = ["Satelite_Gestao.exe", "mapa_sistema.py"]
        for arq in arquivos:
            if os.path.exists(arq):
                if arq.endswith(".exe"): subprocess.Popen([arq])
                else: subprocess.Popen(["python", arq], shell=True)
                return
        QtWidgets.QMessageBox.critical(self, "Erro", "Arquivo do mapa não encontrado!")
