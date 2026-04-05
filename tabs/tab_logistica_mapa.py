import os
import sqlite3
from datetime import datetime, timedelta
import folium
from folium.plugins import MarkerCluster, Fullscreen, AntPath, MeasureControl, MousePosition
from PyQt5 import QtWidgets, QtCore
import webbrowser

class TabLogisticaMapa(QtWidgets.QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Painel de Controle (Visual Dark)
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: #25262c; border-radius: 15px; border: 1px solid #444;")
        fl = QtWidgets.QVBoxLayout(frame)
        
        lbl = QtWidgets.QLabel("📡 RADAR DE LOGÍSTICA (C.O.L.)")
        lbl.setStyleSheet("color: white; font-size: 18pt; font-weight: bold; border: none;")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        
        lbl_desc = QtWidgets.QLabel("Monitoramento em Tempo Real da Frota e Frentes de Trabalho")
        lbl_desc.setStyleSheet("color: #aaa; font-size: 11pt; border: none;")
        lbl_desc.setAlignment(QtCore.Qt.AlignCenter)
        
        btn_radar = QtWidgets.QPushButton("  ABRIR MAPA INTERATIVO  ")
        btn_radar.setCursor(QtCore.Qt.PointingHandCursor)
        btn_radar.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; 
                color: white; 
                font-size: 14pt; 
                padding: 15px; 
                border-radius: 8px; 
                font-weight: bold; 
            } 
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_radar.clicked.connect(self.gerar_radar)
        
        fl.addWidget(lbl)
        fl.addWidget(lbl_desc)
        fl.addSpacing(20)
        fl.addWidget(btn_radar)
        
        layout.addWidget(frame)
        layout.addStretch()

    def gerar_radar(self):
        # 1. CRIAÇÃO DO MAPA BASE E FERRAMENTAS (IGUAL AO SATÉLITE)
        m = folium.Map(location=[-21.135, -48.05], zoom_start=11, tiles=None)
        
        # Camadas de Base (Satélite vs Rua)
        folium.TileLayer('OpenStreetMap', name='🗺️ Mapa de Ruas').add_to(m)
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='🛰️ Satélite (Real)'
        ).add_to(m)

        # Ferramentas Profissionais
        Fullscreen().add_to(m)
        MousePosition().add_to(m) # Mostra Lat/Lon no canto
        MeasureControl(
            position='bottomleft', 
            primary_length_unit='meters', 
            secondary_length_unit='kilometers', 
            primary_area_unit='hectares'
        ).add_to(m)

        # Grupos para o Menu (Para ligar/desligar itens)
        fg_onibus = folium.FeatureGroup(name="🚌 Frota (Ônibus)")
        fg_rotas = folium.FeatureGroup(name="➖ Trajetos (Linhas)")
        fg_frentes = folium.FeatureGroup(name="🛑 Frentes (Destinos)")

        # 2. Busca a Configuração do Dia
        hoje = datetime.now().strftime("%Y-%m-%d")
        agora = datetime.now()
        
        sql = """
            SELECT 
                f.numero, f.placa,              
                c.nome, c.lat, c.lon,           
                fr.nome,                        
                faz.nome, faz.lat, faz.lon,     
                e.hora_ida, e.hora_volta
            FROM escala_viagem e
            JOIN frota f ON e.onibus_id = f.id
            JOIN cidades c ON e.cidade_id = c.id
            JOIN frentes fr ON e.frente_id = fr.id
            LEFT JOIN localizacao_frentes lf ON lf.frente_id = fr.id AND lf.data = ?
            LEFT JOIN fazendas faz ON lf.fazenda_cod = faz.codigo
        """
        
        viagens = self.db.conn.execute(sql, (hoje,)).fetchall()
        
        if not viagens:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma escala encontrada para HOJE.\nConfigure a 'Localização das Frentes' na aba de Cadastros.")
            return

        cnt_onibus = 0
        
        for v in viagens:
            bus_num, bus_placa, cid_nome, cid_lat, cid_lon, frente_nome, faz_nome, faz_lat, faz_lon, h_ida, h_volta = v
            
            if not (cid_lat and cid_lon and faz_lat and faz_lon): continue

            cnt_onibus += 1
            dt_ida = datetime.strptime(f"{hoje} {h_ida}", "%Y-%m-%d %H:%M")
            dt_volta = datetime.strptime(f"{hoje} {h_volta}", "%Y-%m-%d %H:%M")
            
            # Estimativa de tempo de viagem (1h)
            dt_chegada_fazenda = dt_ida + timedelta(hours=1)
            dt_chegada_cidade = dt_volta + timedelta(hours=1)

            # LÓGICA "THE SIMS"
            pos_lat, pos_lon = 0, 0
            status_txt = ""
            icone_cor = "blue"
            icone_tipo = "bus"
            animar_rota = False
            
            # --- CÁLCULO DA POSIÇÃO ---
            if agora < dt_ida:
                # Garagem
                pos_lat, pos_lon = cid_lat, cid_lon
                status_txt = f"Aguardando saída ({h_ida})"
                icone_cor = "gray"
                
            elif dt_ida <= agora < dt_chegada_fazenda:
                # Indo
                tempo_total = (dt_chegada_fazenda - dt_ida).seconds
                tempo_decorrido = (agora - dt_ida).seconds
                perc = tempo_decorrido / tempo_total
                pos_lat = cid_lat + (faz_lat - cid_lat) * perc
                pos_lon = cid_lon + (faz_lon - cid_lon) * perc
                status_txt = f"🚍 VIAJANDO para {faz_nome}"
                icone_cor = "green"
                animar_rota = True
                rota_pts = [[cid_lat, cid_lon], [faz_lat, faz_lon]]
                cor_rota = "blue"

            elif dt_chegada_fazenda <= agora < dt_volta:
                # Na Frente
                pos_lat, pos_lon = faz_lat, faz_lon
                status_txt = f"🛑 OPERANDO NA FRENTE"
                icone_cor = "orange"
                icone_tipo = "users" # Ícone muda para 'pessoal'
                
                # Marca a Frente no mapa também
                folium.CircleMarker(
                    [faz_lat, faz_lon], radius=8, color='red', fill=True, 
                    popup=f"<b>{frente_nome}</b><br>{faz_nome}"
                ).add_to(fg_frentes)

            elif dt_volta <= agora < dt_chegada_cidade:
                # Voltando
                tempo_total = (dt_chegada_cidade - dt_volta).seconds
                tempo_decorrido = (agora - dt_volta).seconds
                perc = tempo_decorrido / tempo_total
                pos_lat = faz_lat + (cid_lat - faz_lat) * perc
                pos_lon = faz_lon + (cid_lon - faz_lon) * perc
                status_txt = f"🏠 VOLTANDO para Base"
                icone_cor = "red"
                animar_rota = True
                rota_pts = [[faz_lat, faz_lon], [cid_lat, cid_lon]]
                cor_rota = "red"

            else:
                # Fim do dia
                pos_lat, pos_lon = cid_lat, cid_lon
                status_txt = "🏁 Encerrado"
                icone_cor = "black"

            # --- DESENHO NO MAPA ---
            
            # 1. Rota Animada (Se estiver andando)
            if animar_rota:
                AntPath(
                    rota_pts, 
                    color=cor_rota, 
                    weight=4, 
                    opacity=0.7, 
                    delay=1000, 
                    tooltip=f"Rota {bus_num}"
                ).add_to(fg_rotas)

            # 2. Marcador do Ônibus (Popup Bonito)
            html_popup = f"""
            <div style="font-family: 'Segoe UI', sans-serif; width: 220px; color: #333;">
                <div style="background-color: {icone_cor}; color: white; padding: 5px; border-radius: 5px 5px 0 0;">
                    <h4 style="margin:0;">🚌 {bus_num}</h4>
                </div>
                <div style="padding: 10px; border: 1px solid #ccc; border-top: none;">
                    <b>Placa:</b> {bus_placa}<br>
                    <b>Status:</b> {status_txt}<br>
                    <hr style="margin: 5px 0;">
                    <b>Origem:</b> {cid_nome}<br>
                    <b>Destino:</b> {faz_nome}<br>
                    <b>Frente:</b> {frente_nome}
                </div>
            </div>
            """
            
            folium.Marker(
                [pos_lat, pos_lon],
                popup=folium.Popup(html_popup, max_width=300),
                tooltip=f"🚌 {bus_num}: {status_txt}",
                icon=folium.Icon(color=icone_cor, icon=icone_tipo, prefix="fa")
            ).add_to(fg_onibus)

        # ADICIONA OS GRUPOS AO MAPA
        fg_frentes.add_to(m)
        fg_rotas.add_to(m)
        fg_onibus.add_to(m)

        # 3. MENU DE CAMADAS (O "MENU" QUE VOCÊ PEDIU)
        folium.LayerControl(collapsed=False).add_to(m)

        # Salva e Abre
        arquivo = os.path.abspath("mapa_logistica.html")
        m.save(arquivo)
        webbrowser.open(f"file:///{arquivo}")
