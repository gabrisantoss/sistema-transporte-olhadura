from __future__ import annotations

from datetime import date

import requests
from PyQt5 import QtCore

from app_config import OPENWEATHER_API_KEY, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from app_logging import get_logger


LOGGER = get_logger(__name__)


class InfoWorker(QtCore.QThread):
    info_pronta = QtCore.pyqtSignal(list)
    clima_atual_sertaozinho = QtCore.pyqtSignal(str)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.api_key = OPENWEATHER_API_KEY
        self.session = requests.Session()

    def _consultar_clima(self, **params) -> dict:
        url = "https://api.openweathermap.org/data/2.5/weather"
        payload = {
            "units": "metric",
            "lang": "pt_br",
            "appid": self.api_key,
            **params,
        }
        response = self.session.get(url, params=payload, timeout=5)
        response.raise_for_status()
        return response.json()

    def run(self) -> None:
        mensagens: list[str] = []
        if not self.api_key:
            self.info_pronta.emit(["Configure a chave do clima para liberar o rodape dinamico."])
            return

        try:
            resposta = self._consultar_clima(q="Sertaozinho,br")
            if resposta.get("cod") == 200:
                temp = int(resposta["main"]["temp"])
                descricao = resposta["weather"][0]["description"].upper()
                icone = self.get_icone_tempo(descricao)
                texto_clima = f"{icone} {temp} C ({descricao})"
                mensagens.append(f"BASE SERTAOZINHO: {texto_clima}")
                self.clima_atual_sertaozinho.emit(texto_clima)
        except Exception:
            LOGGER.exception("Falha ao consultar clima da base")

        try:
            fazendas = self.db.listar_fazendas_com_gps(limit=8, randomize=True)
            if not fazendas:
                mensagens.append("Cadastre o GPS das fazendas para ver clima aqui.")

            for fazenda in fazendas:
                nome, lat, lon = fazenda
                try:
                    resposta = self._consultar_clima(lat=lat, lon=lon)
                    if resposta.get("cod") == 200:
                        temp = int(resposta["main"]["temp"])
                        descricao = resposta["weather"][0]["description"].upper()
                        icone = self.get_icone_tempo(descricao)
                        nome_curto = (
                            str(nome)
                            .replace("FAZENDA", "FAZ.")
                            .replace("ESTANCIA", "EST.")
                            .replace("SITIO", "SIT.")
                            .split("/")[0]
                            .strip()
                        )
                        mensagens.append(f"{nome_curto}: {icone} {temp} C")
                except Exception:
                    LOGGER.exception("Falha ao consultar clima da fazenda %s", nome)
        except Exception:
            LOGGER.exception("Falha ao consultar fazendas com GPS")

        if mensagens:
            self.info_pronta.emit(mensagens)

    def get_icone_tempo(self, descricao: str) -> str:
        desc = (descricao or "").lower()
        if "chuva" in desc:
            return "[chuva]"
        if "nuve" in desc or "nublado" in desc:
            return "[nuvens]"
        if "limpo" in desc or "sol" in desc:
            return "[sol]"
        if "tempestade" in desc or "trovo" in desc:
            return "[trovoada]"
        return "[tempo]"


class TelegramWorker(QtCore.QThread):
    sucesso = QtCore.pyqtSignal(str)
    erro = QtCore.pyqtSignal(str)

    def __init__(self, db, clima_texto: str = "Indisponivel"):
        super().__init__()
        self.db = db
        self.clima_texto = clima_texto
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID

    def run(self) -> None:
        try:
            if not self.token or not self.chat_id:
                self.erro.emit("Configure Telegram token e chat id nas variaveis APP_NOTAS_TELEGRAM_*.")
                return

            hoje_sql = date.today().strftime("%Y-%m-%d")
            hoje_br = date.today().strftime("%d/%m/%Y")
            total = self.db.contar_notas_data(hoje_sql)
            top_motorista = self.db.top_motorista_do_dia(hoje_sql)
            campeao = (
                f"{top_motorista['motorista_nome']} ({top_motorista['qtd']} viagens)"
                if top_motorista
                else "Nenhum ainda"
            )

            msg = "\n".join(
                [
                    "*RELATORIO DIARIO - SISTEMA SAFRA*",
                    f"*Data:* {hoje_br}",
                    "",
                    "*Producao do Dia:*",
                    f"Viagens: *{total}*",
                    f"Destaque: *{campeao}*",
                    "",
                    "*Clima na Base:*",
                    self.clima_texto,
                    "",
                    "_Enviado via Sistema Enterprise_",
                ]
            )

            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            response = requests.post(
                url,
                data={"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            )
            if response.status_code == 200:
                self.sucesso.emit("Enviado com sucesso.")
            else:
                LOGGER.warning("Falha no envio do Telegram: %s", response.text)
                self.erro.emit(f"Erro Telegram: {response.text}")
        except Exception as exc:
            LOGGER.exception("Falha ao enviar relatorio Telegram")
            self.erro.emit(f"Falha: {exc}")
