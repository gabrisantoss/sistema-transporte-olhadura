from fpdf import FPDF

from .base import RelatorioFormatacaoMixin


class RelatorioPdfDiarioBuilder(RelatorioFormatacaoMixin):
    def criar_pdf_resumo_diario(self, dados):
        if not dados:
            return None

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Resumo Plantio (Diario)", ln=True, align="C")

        data_atual = None
        for item in dados["linhas"]:
            if item["data"] != data_atual:
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, f"DATA: {item['data']}", ln=True)
                data_atual = item["data"]

            pdf.set_font("Arial", "", 10)
            pdf.cell(100, 8, self._latin1_safe(item["fazenda"][:35]), 1)
            pdf.cell(60, 8, self._latin1_safe(item["variedade"][:20]), 1)
            pdf.cell(20, 8, str(item["qtd"]), 1, ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"TOTAL: {self._fmt_int(dados['total_geral'])}", ln=True, align="C")
        return pdf
