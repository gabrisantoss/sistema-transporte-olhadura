from __future__ import annotations

import re
from datetime import datetime

from fpdf import FPDF


def formatar_periodo_br(d_ini: str, d_fim: str) -> str:
    dt_i_str = datetime.strptime(d_ini, "%Y-%m-%d").strftime("%d/%m/%Y")
    dt_f_str = datetime.strptime(d_fim, "%Y-%m-%d").strftime("%d/%m/%Y")
    return f"{dt_i_str} a {dt_f_str}"


class PDFRelatorio(FPDF):
    def __init__(self, titulo, periodo, total_viagens):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titulo = titulo
        self.periodo = periodo
        self.total_viagens = total_viagens
        self.gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _safe(self, texto):
        return str(texto or "").encode("latin-1", "replace").decode("latin-1")

    def header(self):
        self.set_fill_color(21, 22, 27)
        self.rect(0, 0, 210, 30, "F")

        self.set_y(8)
        self.set_font("Arial", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, self.titulo, ln=1)

        self.set_font("Arial", "", 9)
        self.set_text_color(200, 200, 200)
        info = f"Periodo: {self.periodo} | Total Considerado: {self.total_viagens} Viagens"
        self.cell(0, 6, info, ln=1)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(190, 10, self._safe(f"Gerado em {self.gerado_em}"), 0, 0, "L")

    def section_title(self, titulo, subtitulo=""):
        self.set_fill_color(241, 245, 249)
        self.set_text_color(30, 41, 59)
        self.set_font("Arial", "B", 11)
        self.cell(190, 8, self._safe(f" {titulo}"), ln=1, fill=True)
        if subtitulo:
            self.set_font("Arial", "", 8)
            self.set_text_color(100, 116, 139)
            self.cell(190, 5, self._safe(f" {subtitulo}"), ln=1)
        self.ln(2)

    def metric_card(self, x, y, w, h, titulo, valor, subtitulo="", accent=(59, 64, 74)):
        self.set_draw_color(226, 232, 240)
        self.set_fill_color(248, 250, 252)
        self.rect(x, y, w, h, "DF")
        self.set_fill_color(*accent)
        self.rect(x, y, 3, h, "F")

        self.set_xy(x + 5, y + 3)
        self.set_font("Arial", "B", 7)
        self.set_text_color(100, 116, 139)
        self.cell(w - 8, 4, self._safe(titulo.upper()), 0, 2)

        self.set_x(x + 5)
        self.set_font("Arial", "B", 13 if h >= 16 else 11)
        self.set_text_color(15, 23, 42)
        self.cell(w - 8, 6, self._safe(valor), 0, 2)

        if subtitulo:
            self.set_x(x + 5)
            self.set_font("Arial", "", 7)
            self.set_text_color(100, 116, 139)
            self.cell(w - 8, 4, self._safe(subtitulo), 0, 2)


class RelatorioFormatacaoMixin:
    def _normalizar_texto_relatorio(self, texto: str) -> str:
        substituicoes = {
            "\u2013": "-",
            "\u2014": "-",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2022": "-",
            "\u00a0": " ",
            "\ufffd": " ",
        }
        for antigo, novo in substituicoes.items():
            texto = texto.replace(antigo, novo)
        texto = re.sub(r"\s+\?\s+", " / ", texto)
        texto = re.sub(r"\s+/\s+", " / ", texto)
        return texto

    def _latin1_safe(self, s: str) -> str:
        texto = self._normalizar_texto_relatorio(s or "")
        return texto.encode("latin-1", "replace").decode("latin-1")

    def _fmt_int(self, valor) -> str:
        try:
            return f"{int(valor):,}".replace(",", ".")
        except Exception:
            return str(valor)

    def _formatar_codigo_relatorio(self, codigo) -> str:
        codigo = self._texto_relatorio(codigo, "-")
        if codigo == "-":
            return codigo

        codigo_limpo = re.sub(r"\s+", "", codigo)
        if "-" in codigo_limpo or len(codigo_limpo) <= 3:
            return codigo_limpo

        return f"{codigo_limpo[:3]}-{codigo_limpo[3:]}"

    def _texto_relatorio(self, valor, padrao="") -> str:
        texto = "" if valor is None else str(valor)
        texto = self._normalizar_texto_relatorio(texto)
        texto = texto.replace("\r", " ").replace("\n", " ")
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto or padrao

    def _chave_relatorio(self, valor, padrao="") -> str:
        return self._texto_relatorio(valor, padrao).upper()

    def _sort_key_texto(self, valor):
        partes = re.split(r"(\d+)", self._texto_relatorio(valor))
        return [int(p) if p.isdigit() else p.upper() for p in partes]

    def _sort_key_codigo_relatorio(self, codigo, nome=""):
        codigo_limpo = self._texto_relatorio(codigo, "-")
        if codigo_limpo == "-":
            return (1, self._sort_key_texto(nome))
        return (
            0,
            self._sort_key_texto(self._formatar_codigo_relatorio(codigo_limpo)),
            self._sort_key_texto(nome),
        )

    def _resumir_texto(self, texto, limite=52) -> str:
        texto = self._texto_relatorio(texto, "-")
        if len(texto) <= limite:
            return texto
        return texto[: limite - 3].rstrip() + "..."

    def _resumir_lista(self, itens, limite=10) -> str:
        itens = [self._texto_relatorio(item) for item in itens if self._texto_relatorio(item)]
        if not itens:
            return "-"
        if len(itens) <= limite:
            return ", ".join(itens)
        return ", ".join(itens[:limite]) + f" +{len(itens) - limite}"

    def _label_origem_relatorio(self, codigo, nome) -> str:
        codigo = self._formatar_codigo_relatorio(codigo)
        nome = self._texto_relatorio(nome, "NÃO INFORMADA")
        return f"[{codigo}] {nome}" if codigo != "-" else nome

    def _label_fazenda_relatorio(self, codigo, nome, tipo="") -> str:
        base = self._label_origem_relatorio(codigo, nome)
        if tipo:
            return f"({tipo.upper()}) {base}"
        return base
