import sys
import sqlite3
import os
import webbrowser
import requests # <--- NOVA BIBLIOTECA PARA BAIXAR A ROTA
import folium
from folium.plugins import Draw, MeasureControl, Fullscreen, MousePosition, MarkerCluster, HeatMap
from PyQt5 import QtWidgets, QtCore, QtGui

# --- ESTILO DARK (PREMIUM) ---
STYLESHEET = """
QWidget { background-color: #1e1e24; color: #e0e0e0; font-family: "Segoe UI", sans-serif; font-size: 11pt; }
QTabWidget::pane { border: 1px solid #444; background-color: #25262c; margin-top: -1px; }
QTabBar::tab { background-color: #2b2d35; color: #888; padding: 10px 25px; border-top-left-radius: 4px; border-top-right-radius: 4px; border: 1px solid #333; }
QTabBar::tab:selected { background-color: #3a7bd5; color: white; border: 1px solid #3a7bd5; }
QPushButton { background-color: #3a7bd5; color: white; border-radius: 5px; padding: 10px; font-weight: bold; }
QPushButton:hover { background-color: #4ea4ff; }
QLineEdit { padding: 8px; border: 1px solid #444; border-radius: 4px; background-color: #1a1b20; color: white; }
QTableWidget { background-color: #25262c; gridline-color: #444; border: none; }
QHeaderView::section { background-color: #1a1b20; padding: 5px; border: none; font-weight: bold; color: #3a7bd5; }
"""

class SistemaMapas(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Satélite Transporte - Rotas Reais")
        self.resize(650, 500)
        self.setStyleSheet(STYLESHEET)
        
        self.db_path = "transporte.db"
        self._verificar_banco()
        
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.tab_mapa = QtWidgets.QWidget()
        self.tab_coords = QtWidgets.QWidget()
        
        self._setup_aba_mapa()
        self._setup_aba_coords()
        
        self.tabs.addTab(self.tab_mapa, "🌍 Mapa de Rotas & Calor")
        self.tabs.addTab(self.tab_coords, "📍 Cadastro GPS")

        self.arquivo_desenhos = "meus_desenhos.geojson"

    def _verificar_banco(self):
        if not os.path.exists(self.db_path):
            QtWidgets.QMessageBox.critical(self, "Erro", "Banco não encontrado.")
            sys.exit()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("ALTER TABLE fazendas ADD COLUMN lat REAL")
            conn.execute("ALTER TABLE fazendas ADD COLUMN lon REAL")
            conn.commit(); conn.close()
        except: pass

    # --- FUNÇÃO MÁGICA: CALCULAR ROTA REAL (OSRM) ---
    def get_rota_real(self, lat1, lon1, lat2, lon2):
        """
        Consulta o serviço gratuito OSRM para pegar o caminho da estrada.
        Retorna uma lista de coordenadas [[lat, lon], [lat, lon]...]
        """
        try:
            # OSRM espera longitude,latitude (ao contrário do Google)
            url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
            response = requests.get(url, timeout=2) # Timeout curto para não travar se falhar
            
            if response.status_code == 200:
                dados = response.json()
                # OSRM retorna [lon, lat], precisamos inverter para [lat, lon] para o Folium
                coords_osrm = dados['routes'][0]['geometry']['coordinates']
                rota_folium = [[c[1], c[0]] for c in coords_osrm]
                return rota_folium
        except:
            pass # Se der erro (sem internet), retorna None e usaremos linha reta
        return None

    # --- ABA 1: GERADOR ---
    def _setup_aba_mapa(self):
        layout = QtWidgets.QVBoxLayout(self.tab_mapa)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        
        box = QtWidgets.QFrame()
        box.setStyleSheet("background-color: #25262c; border-radius: 15px; border: 1px solid #444; padding: 20px;")
        box_layout = QtWidgets.QVBoxLayout(box)
        
        lbl = QtWidgets.QLabel("🚚 ROTAS REAIS & SATÉLITE")
        lbl.setStyleSheet("font-size: 18pt; font-weight: bold; color: white; border: none;")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        
        lbl_info = QtWidgets.QLabel("Gera o trajeto pelas estradas (via OSRM) e Mapa de Calor.\nRequer conexão com a internet.")
        lbl_info.setStyleSheet("color: #aaa; border: none; margin-bottom: 15px;")
        lbl_info.setAlignment(QtCore.Qt.AlignCenter)
        
        form = QtWidgets.QHBoxLayout()
        self.dt_ini = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addDays(-30))
        self.dt_ini.setCalendarPopup(True); self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dt_fim.setCalendarPopup(True); self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        
        form.addWidget(QtWidgets.QLabel("De:"))
        form.addWidget(self.dt_ini)
        form.addWidget(QtWidgets.QLabel("Até:"))
        form.addWidget(self.dt_fim)
        
        btn_gerar = QtWidgets.QPushButton("  GERAR ROTAS NO NAVEGADOR  ")
        btn_gerar.setCursor(QtCore.Qt.PointingHandCursor)
        btn_gerar.setStyleSheet("font-size: 12pt; background-color: #d35400; padding: 15px; margin-top: 10px;")
        btn_gerar.clicked.connect(self.gerar_mapa)
        
        btn_load = QtWidgets.QPushButton("📂 Carregar Desenho Anterior")
        btn_load.clicked.connect(self.carregar_arquivo)
        
        box_layout.addWidget(lbl)
        box_layout.addWidget(lbl_info)
        box_layout.addLayout(form)
        box_layout.addWidget(btn_gerar)
        box_layout.addWidget(btn_load)
        
        layout.addWidget(box)

    def carregar_arquivo(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Abrir GeoJSON", "", "GeoJSON (*.geojson *.json)")
        if f:
            self.arquivo_desenhos = f
            QtWidgets.QMessageBox.information(self, "OK", "Arquivo carregado!")

    def gerar_mapa(self):
        d_ini = self.dt_ini.date().toString("yyyy-MM-dd")
        d_fim = self.dt_fim.date().toString("yyyy-MM-dd")
        
        conn = sqlite3.connect(self.db_path)
        query = f"""
            SELECT n.faz_muda_nome, f_origem.lat, f_origem.lon,
                   n.faz_plantio_nome, f_dest.lat, f_dest.lon,
                   COUNT(*) as viagens, n.variedade_nome
            FROM notas n
            LEFT JOIN fazendas f_origem ON CAST(n.faz_muda_cod AS TEXT) = CAST(f_origem.codigo AS TEXT)
            LEFT JOIN fazendas f_dest ON CAST(n.faz_plantio_cod AS TEXT) = CAST(f_dest.codigo AS TEXT)
            WHERE n.data_colheita BETWEEN '{d_ini}' AND '{d_fim}'
            GROUP BY n.faz_muda_cod, n.faz_plantio_cod
        """
        rows = conn.execute(query).fetchall()
        conn.close()

        m = folium.Map(location=[-21.135, -48.05], zoom_start=11, tiles=None)
        
        # CAMADAS
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite (Esri)').add_to(m)
        folium.TileLayer('OpenStreetMap', name='Mapa de Ruas').add_to(m)

        Fullscreen().add_to(m); MousePosition().add_to(m)
        MeasureControl(position='bottomleft', primary_length_unit='meters', secondary_length_unit='kilometers', primary_area_unit='hectares', secondary_area_unit='sqmeters').add_to(m)
        
        Draw(export=True, filename='meus_talhoes.geojson', draw_options={'polyline':True, 'polygon':{'allowIntersection':False, 'showArea':True, 'shapeOptions':{'color':'#2ecc71', 'fillOpacity':0.4}}, 'marker':True}).add_to(m)
        
        if os.path.exists(self.arquivo_desenhos):
            try: folium.GeoJson(self.arquivo_desenhos, name="Meus Desenhos").add_to(m)
            except: pass

        # GRUPOS
        fg_origem = folium.FeatureGroup(name="📍 Origens")
        fg_destino = folium.FeatureGroup(name="📍 Destinos")
        fg_rotas = folium.FeatureGroup(name="🚚 Rotas (Estradas)") # Nova camada para as estradas
        
        dados_calor = []
        dados_ok = False
        
        # BARRA DE PROGRESSO SIMULADA (No terminal)
        total_rotas = len(rows)
        print(f"Calculando {total_rotas} trajetos...")

        for i, row in enumerate(rows):
            nome_o, lat_o, lon_o, nome_d, lat_d, lon_d, viagens, var = row
            
            # Marcadores
            if lat_o and lon_o:
                dados_ok = True
                folium.CircleMarker([lat_o, lon_o], radius=6, color='red', fill=True, popup=f"Origem: {nome_o} ({var})").add_to(fg_origem)
                dados_calor.append([lat_o, lon_o, viagens])
            
            if lat_d and lon_d:
                dados_ok = True
                folium.CircleMarker([lat_d, lon_d], radius=6, color='#00ff00', fill=True, popup=f"Destino: {nome_d}").add_to(fg_destino)
                dados_calor.append([lat_d, lon_d, viagens])
                
            # --- DESENHO DA ROTA ---
            if lat_o and lon_o and lat_d and lon_d:
                # Tenta pegar a rota real
                rota_real = self.get_rota_real(lat_o, lon_o, lat_d, lon_d)
                
                if rota_real:
                    # Se achou estrada, desenha linha sólida Azul
                    folium.PolyLine(
                        rota_real, 
                        color="#3498db", # Azul Estrada
                        weight=4, 
                        opacity=0.7, 
                        tooltip=f"Rota Real: {nome_o} -> {nome_d}"
                    ).add_to(fg_rotas)
                else:
                    # Se não achou (ou sem internet), desenha Tracejado Branco (Plano B)
                    folium.PolyLine(
                        [[lat_o, lon_o], [lat_d, lon_d]], 
                        color="white", 
                        weight=2, 
                        opacity=0.5, 
                        dash_array='5, 10',
                        tooltip="Rota Reta (Sem GPS)"
                    ).add_to(fg_rotas)

        fg_origem.add_to(m)
        fg_destino.add_to(m)
        fg_rotas.add_to(m) # Adiciona as estradas

        if dados_calor:
            HeatMap(dados_calor, name="🔥 Mapa de Calor", min_opacity=0.3, radius=20, blur=15, max_zoom=10).add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

        if not dados_ok and not os.path.exists(self.arquivo_desenhos):
            QtWidgets.QMessageBox.warning(self, "Aviso", "Sem coordenadas GPS.")

        path = os.path.abspath("mapa_rotas.html")
        m.save(path)
        webbrowser.open(f"file:///{path}")

    # --- ABA 2: CADASTRO GPS ---
    def _setup_aba_coords(self):
        layout = QtWidgets.QVBoxLayout(self.tab_coords)
        layout.addWidget(QtWidgets.QLabel("Cadastro de GPS das Fazendas"))
        self.txt_filtro = QtWidgets.QLineEdit(); self.txt_filtro.setPlaceholderText("🔍 Filtrar..."); self.txt_filtro.textChanged.connect(self.filtrar_tabela); layout.addWidget(self.txt_filtro)
        self.table = QtWidgets.QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["Cód", "Nome", "Latitude", "Longitude"]); self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch); layout.addWidget(self.table)
        btn_box = QtWidgets.QHBoxLayout(); b_load = QtWidgets.QPushButton("🔄 Recarregar"); b_load.clicked.connect(self.carregar_fazendas); b_save = QtWidgets.QPushButton("💾 Salvar"); b_save.clicked.connect(self.salvar_coords); btn_box.addWidget(b_load); btn_box.addWidget(b_save); layout.addLayout(btn_box); self.carregar_fazendas()

    def carregar_fazendas(self):
        conn = sqlite3.connect(self.db_path); rows = conn.execute("SELECT codigo, nome, lat, lon FROM fazendas ORDER BY nome").fetchall(); conn.close(); self.table.setRowCount(0); self.table.setSortingEnabled(False)
        for r, row in enumerate(rows): self.table.insertRow(r); [self.table.setItem(r, c, QtWidgets.QTableWidgetItem(str(row[c] if row[c] else ""))) for c in range(4)]
        self.table.setSortingEnabled(True)

    def filtrar_tabela(self, t):
        for i in range(self.table.rowCount()): self.table.setRowHidden(i, not (t.lower() in self.table.item(i, 1).text().lower()))

    def salvar_coords(self):
        conn = sqlite3.connect(self.db_path)
        for i in range(self.table.rowCount()):
            c = self.table.item(i, 0).text(); la = self.table.item(i, 2).text().replace(',','.'); lo = self.table.item(i, 3).text().replace(',','.')
            if la and lo: 
                try: conn.execute("UPDATE fazendas SET lat=?, lon=? WHERE codigo=?", (float(la), float(lo), c)) 
                except: pass
        conn.commit(); conn.close(); QtWidgets.QMessageBox.information(self, "Sucesso", "Coordenadas salvas!")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SistemaMapas()
    window.show()
    sys.exit(app.exec_())
