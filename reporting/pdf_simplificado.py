from __future__ import annotations

from .base import PDFRelatorio, RelatorioFormatacaoMixin, formatar_periodo_br


class RelatorioPdfSimplificadoBuilder(RelatorioFormatacaoMixin):
    def criar_pdf_simplificado(self, d_ini, d_fim, dados):
        if not dados:
            return None

        pdf = PDFRelatorio(
            titulo="RELATORIO SIMPLIFICADO DE FLUXO",
            periodo=formatar_periodo_br(d_ini, d_fim),
            total_viagens=dados["total_geral"],
        )
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        self._desenhar_resumo_pdf_simplificado(pdf, dados)

        pdf.add_page()
        self._desenhar_tabela_simplificada_pdf(
            pdf,
            "Painel de Origens",
            "Origens organizadas do menor codigo para o maior, mantendo o alcance operacional.",
            dados["origens"],
            "Nenhuma fazenda de muda encontrada no periodo.",
            "Continuidade das origens em ordem crescente de codigo.",
            "FAZENDA DE MUDA",
            "DESTINOS",
            "destinos",
        )

        pdf.add_page()
        self._desenhar_tabela_simplificada_pdf(
            pdf,
            "Painel de Destinos",
            "Destinos organizados do menor codigo para o maior, mantendo a cobertura de origem.",
            dados["destinos"],
            "Nenhuma fazenda de plantio encontrada no periodo.",
            "Continuidade dos destinos em ordem crescente de codigo.",
            "FAZENDA DE PLANTIO",
            "ORIGENS",
            "origens",
        )

        pdf.add_page()
        self._desenhar_cruzamentos_simplificados_pdf(pdf, dados["cruzamentos"])

        return pdf

    def _desenhar_resumo_pdf_simplificado(self, pdf, dados):
        pdf.section_title(
            "Resumo Executivo",
            "Visao consolidada do periodo com foco em volume, cobertura operacional e principais pontos de atencao.",
        )

        self._desenhar_panorama_simplificado_pdf(pdf, dados, 50)

        metricas = [
            ("Total de Viagens", self._fmt_int(dados["total_geral"]), "Movimentacoes consideradas no periodo", (59, 64, 74)),
            ("Bases de Muda", self._fmt_int(dados["metricas"]["origens_ativas"]), "Origens com atividade", (59, 130, 246)),
            ("Bases de Plantio", self._fmt_int(dados["metricas"]["destinos_ativos"]), "Destinos com atividade", (22, 163, 74)),
            ("Fluxos Mapeados", self._fmt_int(dados["metricas"]["cruzamentos_ativos"]), "Origens com destino consolidado", (217, 119, 6)),
        ]

        x_positions = [10, 108, 10, 108]
        y_positions = [70, 70, 92, 92]
        for idx, (titulo, valor, subtitulo, accent) in enumerate(metricas):
            pdf.metric_card(x_positions[idx], y_positions[idx], 92, 18, titulo, valor, subtitulo, accent=accent)

        self._desenhar_faixa_saude_simplificada_pdf(pdf, dados, 116)

        ranking_y = 136
        esquerda_h = self._desenhar_ranking_simplificado_pdf(pdf, 10, ranking_y, 92, "Maiores Origens", dados["tops"]["origens"])
        direita_h = self._desenhar_ranking_simplificado_pdf(pdf, 108, ranking_y, 92, "Maiores Destinos", dados["tops"]["destinos"])

        destaques_y = ranking_y + max(esquerda_h, direita_h) + 4
        self._desenhar_destaques_simplificados_pdf(pdf, dados, destaques_y)
        pdf.set_y(destaques_y + 32)


    def _desenhar_panorama_simplificado_pdf(self, pdf, dados, y):
        executivo = dados.get("executivo", {})
        origem_top = executivo.get("origem_top")
        destino_top = executivo.get("destino_top")

        pdf.set_draw_color(15, 23, 42)
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(10, y, 190, 14, "DF")

        pdf.set_xy(14, y + 1.8)
        pdf.set_font("Arial", "B", 7)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(182, 3.5, "PANORAMA DO PERIODO", 0, 1)

        frase = (
            f"{self._fmt_int(dados['total_geral'])} viagens distribuidas entre "
            f"{self._fmt_int(dados['metricas']['origens_ativas'])} bases de muda e "
            f"{self._fmt_int(dados['metricas']['destinos_ativos'])} bases de plantio."
        )
        pdf.set_x(14)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(182, 4.8, self._latin1_safe(self._resumir_texto(frase, 110)), 0, 1)

        origem_txt = self._resumir_texto(origem_top["label"], 34) if origem_top else "-"
        destino_txt = self._resumir_texto(destino_top["label"], 34) if destino_top else "-"
        resumo_secundario = f"Maior origem: {origem_txt} | Maior destino: {destino_txt}"
        pdf.set_x(14)
        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(203, 213, 225)
        pdf.cell(182, 3.6, self._latin1_safe(resumo_secundario), 0, 0)


    def _desenhar_faixa_saude_simplificada_pdf(self, pdf, dados, y):
        sem_origem = int(dados["pendencias"]["sem_origem"] or 0)
        sem_destino = int(dados["pendencias"]["sem_destino"] or 0)
        consolidado = self._fmt_int(dados["metricas"]["registros_completos"])

        status_ok = sem_origem == 0 and sem_destino == 0
        accent = (22, 163, 74) if status_ok else (202, 138, 4)
        titulo = "Base cadastral consistente" if status_ok else "Base cadastral requer revisao"
        detalhe = (
            f"Sem origem: {self._fmt_int(sem_origem)}    |    "
            f"Sem destino: {self._fmt_int(sem_destino)}    |    "
            f"Registros consolidados: {consolidado}"
        )

        pdf.set_draw_color(226, 232, 240)
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(10, y, 190, 14, "DF")
        pdf.set_fill_color(*accent)
        pdf.rect(10, y, 5, 14, "F")

        pdf.set_xy(18, y + 2.2)
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(178, 4, self._latin1_safe(titulo), 0, 1)

        pdf.set_x(18)
        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(178, 3.8, self._latin1_safe(detalhe), 0, 0)


    def _desenhar_ranking_simplificado_pdf(self, pdf, x, y, w, titulo, itens):
        itens = itens[:5]
        alturas = [9 if item.get("subtitle") else 7 for item in itens] or [7]
        h = 12 + sum(alturas)

        pdf.set_draw_color(226, 232, 240)
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x, y, w, h, "DF")
        pdf.set_fill_color(43, 48, 56)
        pdf.rect(x, y, w, 8, "F")
        pdf.set_fill_color(96, 165, 250)
        pdf.rect(x, y, 3, 8, "F")

        pdf.set_xy(x + 3, y + 1.5)
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(w - 6, 5, self._latin1_safe(titulo), 0, 1)

        atual_y = y + 8
        if not itens:
            pdf.set_xy(x + 3, atual_y + 2)
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(w - 6, 5, "Sem dados no periodo.", 0, 1)
            return h + 4

        for idx, item in enumerate(itens, start=1):
            altura_item = 9 if item.get("subtitle") else 7
            if idx % 2 == 0:
                pdf.set_fill_color(248, 250, 252)
                pdf.rect(x + 1, atual_y, w - 2, altura_item, "F")

            label = self._resumir_texto(item["label"], 32 if w < 100 else 54)
            subtitle = self._resumir_texto(item.get("subtitle"), 32 if w < 100 else 54) if item.get("subtitle") else ""

            pdf.set_xy(x + 3, atual_y + 0.9)
            pdf.set_font("Arial", "B", 8)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(8, 4, f"{idx}.", 0, 0)

            pdf.set_font("Arial", "", 8)
            pdf.cell(w - 28, 4, self._latin1_safe(label), 0, 0)

            pdf.set_font("Arial", "B", 8)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(20, 4, self._fmt_int(item["qtd"]), 0, 0, "R")

            if subtitle:
                pdf.set_xy(x + 11, atual_y + 4.7)
                pdf.set_font("Arial", "", 7)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(w - 20, 3, self._latin1_safe(subtitle), 0, 0)

            atual_y += altura_item

        return h + 4


    def _desenhar_destaques_simplificados_pdf(self, pdf, dados, y):
        executivo = dados.get("executivo", {})
        origem_top = executivo.get("origem_top")
        destino_top = executivo.get("destino_top")
        cruzamento_top = executivo.get("cruzamento_top")
        principal_destino = cruzamento_top.get("destino_principal") if cruzamento_top else None

        cards = [
            {
                "titulo": "Maior origem",
                "valor": self._resumir_texto(origem_top["label"], 28) if origem_top else "-",
                "subtitulo": (
                    f"{self._fmt_int(origem_top['qtd'])} viagens | {self._fmt_int(origem_top['destinos'])} destinos"
                    if origem_top else "Sem leitura no periodo"
                ),
                "accent": (59, 130, 246),
            },
            {
                "titulo": "Maior destino",
                "valor": self._resumir_texto(destino_top["label"], 28) if destino_top else "-",
                "subtitulo": (
                    f"{self._fmt_int(destino_top['qtd'])} viagens | {self._fmt_int(destino_top['origens'])} origens"
                    if destino_top else "Sem leitura no periodo"
                ),
                "accent": (22, 163, 74),
            },
            {
                "titulo": "Fluxo principal",
                "valor": (
                    self._resumir_texto(f"{cruzamento_top['nome']} -> {principal_destino['nome']}", 30)
                    if cruzamento_top and principal_destino else "-"
                ),
                "subtitulo": (
                    f"{self._fmt_int(principal_destino['qtd'])} viagens priorizadas"
                    if principal_destino else "Sem leitura no periodo"
                ),
                "accent": (217, 119, 6),
            },
        ]

        x_positions = [10, 74, 138]
        for idx, card in enumerate(cards):
            self._desenhar_card_destaque_simplificado_pdf(pdf, x_positions[idx], y, 62, card)


    def _desenhar_card_destaque_simplificado_pdf(self, pdf, x, y, w, card):
        pdf.set_draw_color(226, 232, 240)
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(x, y, w, 28, "DF")
        pdf.set_fill_color(*card["accent"])
        pdf.rect(x, y, w, 4, "F")

        pdf.set_xy(x + 3, y + 6)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(w - 6, 4, self._latin1_safe(card["titulo"]), 0, 1)

        pdf.set_x(x + 3)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(15, 23, 42)
        pdf.multi_cell(w - 6, 4.2, self._latin1_safe(card["valor"]), 0)

        pdf.set_x(x + 3)
        pdf.set_font("Arial", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.multi_cell(w - 6, 3.8, self._latin1_safe(card["subtitulo"]), 0)


    def _desenhar_cabecalho_tabela_simplificada_pdf(self, pdf, titulo_coluna, titulo_apoio):
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(12, 6, "#", 1, 0, "C", True)
        pdf.cell(22, 6, "COD.", 1, 0, "C", True)
        pdf.cell(104, 6, self._latin1_safe(titulo_coluna), 1, 0, "L", True)
        pdf.cell(24, 6, "VIAGENS", 1, 0, "R", True)
        pdf.cell(28, 6, self._latin1_safe(titulo_apoio), 1, 1, "R", True)


    def _desenhar_tabela_simplificada_pdf(self, pdf, titulo, subtitulo, itens, texto_vazio, subtitulo_continuacao, titulo_coluna, titulo_apoio, chave_apoio):
        pdf.section_title(titulo, subtitulo)

        if not itens:
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(190, 6, self._latin1_safe(texto_vazio), ln=1)
            pdf.ln(2)
            return

        self._desenhar_cabecalho_tabela_simplificada_pdf(pdf, titulo_coluna, titulo_apoio)
        fill = False

        for idx, item in enumerate(itens, start=1):
            if pdf.get_y() + 6 > 278:
                pdf.add_page()
                pdf.section_title(titulo, subtitulo_continuacao)
                self._desenhar_cabecalho_tabela_simplificada_pdf(pdf, titulo_coluna, titulo_apoio)

            if fill:
                pdf.set_fill_color(248, 250, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(51, 65, 85)
            pdf.set_font("Arial", "", 8)

            codigo = self._formatar_codigo_relatorio(item["codigo"])
            nome = self._resumir_texto(item["nome"], 62)
            apoio = self._fmt_int(item.get(chave_apoio, 0))

            pdf.cell(12, 6, str(idx), 1, 0, "C", fill)
            pdf.cell(22, 6, self._latin1_safe(codigo), 1, 0, "C", fill)
            pdf.cell(104, 6, self._latin1_safe(nome), 1, 0, "L", fill)
            pdf.cell(24, 6, self._fmt_int(item["qtd"]), 1, 0, "R", fill)
            pdf.cell(28, 6, apoio, 1, 1, "R", fill)
            fill = not fill

        pdf.ln(2)


    def _estimar_altura_cruzamento_simplificado(self, cruzamento):
        return 17 + (len(cruzamento["destinos"]) * 6) + 3


    def _desenhar_cabecalho_destinos_cruzamento_pdf(self, pdf):
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(22, 6, "COD.", 1, 0, "C", True)
        pdf.cell(144, 6, "FAZENDA DE PLANTIO", 1, 0, "L", True)
        pdf.cell(24, 6, "VIAGENS", 1, 1, "R", True)


    def _desenhar_cruzamentos_simplificados_pdf(self, pdf, cruzamentos):
        pdf.section_title(
            "Fluxos Executivos Muda -> Plantio",
            "Cada bloco mostra a origem e seus destinos ordenados do menor codigo para o maior.",
        )

        if not cruzamentos:
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(190, 6, "Nenhum cruzamento completo encontrado no periodo.", ln=1)
            return

        for cruzamento in cruzamentos:
            altura_estimada = self._estimar_altura_cruzamento_simplificado(cruzamento)
            if pdf.get_y() + altura_estimada > 278:
                pdf.add_page()
                pdf.section_title(
                    "Fluxos Executivos Muda -> Plantio",
                    "Continuidade das origens e destinos em ordem crescente de codigo.",
                )

            pdf.set_fill_color(43, 48, 56)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(130, 7, self._latin1_safe(self._resumir_texto(cruzamento["origem"], 62)), 0, 0, "L", True)
            resumo = f"{self._fmt_int(cruzamento['qtd'])} viagens | {self._fmt_int(cruzamento['destinos_ativos'])} destinos"
            pdf.cell(60, 7, self._latin1_safe(resumo), 0, 1, "R", True)

            self._desenhar_cabecalho_destinos_cruzamento_pdf(pdf)

            fill = False
            for destino in cruzamento["destinos"]:
                if fill:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)
                pdf.set_font("Arial", "", 8)
                pdf.set_text_color(51, 65, 85)

                codigo = self._formatar_codigo_relatorio(destino["codigo"])
                nome = self._resumir_texto(destino["nome"], 66)
                pdf.cell(22, 6, self._latin1_safe(codigo), 1, 0, "C", fill)
                pdf.cell(144, 6, self._latin1_safe(nome), 1, 0, "L", fill)
                pdf.cell(24, 6, self._fmt_int(destino["qtd"]), 1, 1, "R", fill)
                fill = not fill

            pdf.ln(3)

