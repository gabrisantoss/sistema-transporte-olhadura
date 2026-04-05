from __future__ import annotations

from .base import PDFRelatorio, RelatorioFormatacaoMixin, formatar_periodo_br


class RelatorioPdfGeralBuilder(RelatorioFormatacaoMixin):
    def criar_pdf_geral_fazenda(self, d_ini, d_fim, dados):
        if not dados:
            return None

        pdf = PDFRelatorio(
            titulo="RELATORIO ANALITICO DE FLUXO",
            periodo=formatar_periodo_br(d_ini, d_fim),
            total_viagens=dados["total_geral"],
        )
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        self._desenhar_resumo_pdf_geral(pdf, dados)
        if dados["grupos"]:
            pdf.add_page()
            pdf.section_title(
                "Detalhamento por Origem e Variedade",
                "",
            )

            total_blocos = len(dados["grupos"])
            for indice, grupo in enumerate(dados["grupos"], start=1):
                altura_estimada = self._estimar_altura_bloco_pdf_geral(grupo)
                if pdf.get_y() + altura_estimada > 278:
                    pdf.add_page()
                    pdf.section_title(
                        "Detalhamento por Origem e Variedade",
                        "Continuidade dos blocos validos de muda + variedade.",
                    )
                self._desenhar_bloco_pdf_geral(pdf, indice, total_blocos, grupo)

        self._desenhar_pendencias_pdf_geral(pdf, dados)

        return pdf

    def _desenhar_ranking_pdf(self, pdf, x, y, w, titulo, itens, total_geral):
        itens = itens[:5]
        alturas = [9 if item.get("subtitle") else 7 for item in itens] or [7]
        h = 12 + sum(alturas)

        pdf.set_draw_color(226, 232, 240)
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x, y, w, h, "DF")
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(x, y, w, 8, "F")

        pdf.set_xy(x + 3, y + 1.5)
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(30, 41, 59)
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
            fill = idx % 2 == 0
            if fill:
                pdf.set_fill_color(248, 250, 252)
                pdf.rect(x + 1, atual_y, w - 2, altura_item, "F")

            percentual = (item["qtd"] / total_geral * 100) if total_geral else 0
            label = self._resumir_texto(item["label"], 32 if w < 100 else 54)
            subtitle_raw = item.get("subtitle")
            subtitle = self._resumir_texto(subtitle_raw, 32 if w < 100 else 54) if subtitle_raw else ""

            pdf.set_xy(x + 3, atual_y + 0.9)
            pdf.set_font("Arial", "B", 8)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(8, 4, f"{idx}.", 0, 0)

            pdf.set_font("Arial", "", 8)
            pdf.cell(w - 38, 4, self._latin1_safe(label), 0, 0)

            pdf.set_font("Arial", "B", 8)
            pdf.cell(12, 4, self._fmt_int(item["qtd"]), 0, 0, "R")

            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(12, 4, f"{percentual:.1f}%", 0, 0, "R")

            if subtitle:
                pdf.set_xy(x + 11, atual_y + 4.7)
                pdf.set_font("Arial", "", 7)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(w - 20, 3, self._latin1_safe(subtitle), 0, 0)

            atual_y += altura_item

        return h + 4


    def _desenhar_resumo_pdf_geral(self, pdf, dados):
        pdf.section_title(
            "Resumo Executivo",
            "Visao consolidada do periodo, com ranking dos maiores volumes e alertas de consistencia.",
        )

        metricas = [
            ("Total de Viagens", self._fmt_int(dados["total_geral"]), "Somente viagens completas entram no detalhamento", (59, 64, 74)),
            ("Origens Ativas", self._fmt_int(dados["metricas"]["origens_ativas"]), "Origens com expedicao", (59, 130, 246)),
            ("Variedades Ativas", self._fmt_int(dados["metricas"]["variedades_ativas"]), "Variedades registradas", (22, 163, 74)),
            ("Destinos Ativos", self._fmt_int(dados["metricas"]["destinos_ativos"]), "Destinos de plantio", (217, 119, 6)),
        ]

        x_positions = [10, 108, 10, 108]
        y_positions = [50, 50, 72, 72]
        for idx, (titulo, valor, subtitulo, accent) in enumerate(metricas):
            pdf.metric_card(x_positions[idx], y_positions[idx], 92, 18, titulo, valor, subtitulo, accent=accent)

        pdf.set_y(96)
        pdf.section_title("Pendencias de Cadastro", "Campos vazios que merecem revisao antes da proxima exportacao.")

        pendencias = [
            ("Sem Variedade", self._fmt_int(dados["pendencias"]["sem_variedade"]), "Afeta agrupamento por variedade", (220, 38, 38)),
            ("Sem Destino", self._fmt_int(dados["pendencias"]["sem_destino"]), "Aparece como nao informado", (202, 138, 4)),
            ("Sem Origem", self._fmt_int(dados["pendencias"]["sem_origem"]), "Prejudica rastreabilidade", (79, 70, 229)),
        ]
        pend_y = pdf.get_y()
        x_cards = [10, 74, 138]
        for idx, (titulo, valor, subtitulo, accent) in enumerate(pendencias):
            pdf.metric_card(x_cards[idx], pend_y, 62, 16, titulo, valor, subtitulo, accent=accent)

        pdf.set_y(pend_y + 20)
        resumo_y = pdf.get_y()
        esquerda_h = self._desenhar_ranking_pdf(pdf, 10, resumo_y, 92, "Top Origens", dados["tops"]["origens"], dados["total_geral"])
        direita_h = self._desenhar_ranking_pdf(pdf, 108, resumo_y, 92, "Top Variedades", dados["tops"]["variedades"], dados["total_geral"])

        pdf.set_y(resumo_y + max(esquerda_h, direita_h) + 2)
        topo_y = pdf.get_y()
        esquerda_h = self._desenhar_ranking_pdf(pdf, 10, topo_y, 92, "Top Destinos", dados["tops"]["destinos"], dados["total_geral"])
        direita_h = self._desenhar_ranking_pdf(pdf, 108, topo_y, 92, "Top Blocos", dados["tops"]["grupos"], dados["total_geral"])
        pdf.set_y(topo_y + max(esquerda_h, direita_h))


    def _desenhar_info_bloco_pdf_geral(self, pdf, x, y, w, titulo, valor):
        pdf.set_draw_color(226, 232, 240)
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(x, y, w, 11, "DF")

        pdf.set_xy(x + 3, y + 1.2)
        pdf.set_font("Arial", "B", 6)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w - 6, 3, self._latin1_safe(titulo.upper()), 0, 2)

        pdf.set_x(x + 3)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(30, 41, 59)
        limite = 34 if w <= 50 else 50
        pdf.cell(w - 6, 4, self._latin1_safe(self._resumir_texto(valor, limite)), 0, 2)


    def _desenhar_cabecalho_pendencias_pdf_geral(self, pdf, titulo, descricao, quantidade, accent):
        pdf.set_fill_color(*accent)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(190, 7, self._latin1_safe(f"{titulo} ({self._fmt_int(quantidade)})"), ln=1, fill=True)

        pdf.set_fill_color(248, 250, 252)
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Arial", "", 7)
        pdf.cell(190, 5, self._latin1_safe(descricao), ln=1, fill=True)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(20, 6, "NOTA", 1, 0, "C", True)
        pdf.cell(24, 6, "DATA", 1, 0, "C", True)
        pdf.cell(73, 6, "REFERENCIA", 1, 0, "L", True)
        pdf.cell(73, 6, "DETALHE", 1, 1, "L", True)


    def _desenhar_pendencias_pdf_geral(self, pdf, dados):
        categorias = [
            (
                "sem_variedade",
                "Pendencias: Sem Variedade",
                "Notas com origem e/ou destino definidos, mas sem variedade preenchida.",
                (220, 38, 38),
            ),
            (
                "sem_destino",
                "Pendencias: Sem Destino",
                "Notas que ainda precisam receber a fazenda de plantio.",
                (202, 138, 4),
            ),
            (
                "sem_origem",
                "Pendencias: Sem Origem",
                "Notas sem fazenda de muda informada, o que prejudica a rastreabilidade.",
                (79, 70, 229),
            ),
        ]

        detalhes = dados.get("pendencias_detalhes", {})
        if not any(detalhes.get(chave) for chave, *_ in categorias):
            return

        pdf.add_page()
        pdf.section_title(
            "Pendencias Detalhadas",
            "Lista de notas com cadastro incompleto para revisao operacional.",
        )

        for chave, titulo, descricao, accent in categorias:
            itens = detalhes.get(chave, [])
            if not itens:
                continue

            if pdf.get_y() > 245:
                pdf.add_page()
                pdf.section_title(
                    "Pendencias Detalhadas",
                    "Continuidade das notas que precisam de revisao cadastral.",
                )

            self._desenhar_cabecalho_pendencias_pdf_geral(pdf, titulo, descricao, len(itens), accent)

            fill = False
            for item in itens:
                if pdf.get_y() + 6 > 278:
                    pdf.add_page()
                    pdf.section_title(
                        "Pendencias Detalhadas",
                        "Continuidade das notas que precisam de revisao cadastral.",
                    )
                    self._desenhar_cabecalho_pendencias_pdf_geral(pdf, titulo, descricao, len(itens), accent)

                if fill:
                    pdf.set_fill_color(248, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.set_font("Arial", "", 7)
                pdf.set_text_color(51, 65, 85)
                pdf.cell(20, 6, self._latin1_safe(self._resumir_texto(item["nota"], 10)), 1, 0, "C", fill)
                pdf.cell(24, 6, self._latin1_safe(item["data"]), 1, 0, "C", fill)
                pdf.cell(73, 6, self._latin1_safe(self._resumir_texto(item["referencia"], 44)), 1, 0, "L", fill)
                pdf.cell(73, 6, self._latin1_safe(self._resumir_texto(item["detalhe"], 44)), 1, 1, "L", fill)
                fill = not fill

            pdf.ln(4)


    def _estimar_altura_bloco_pdf_geral(self, grupo):
        preview = self._resumir_lista(grupo["talhoes"], limite=12)
        linhas_preview = max(1, (len(preview) // 92) + 1)
        return 36 + (linhas_preview * 4.5) + 6 + (len(grupo["destinos"]) * 6) + 10


    def _desenhar_bloco_pdf_geral(self, pdf, indice, total_blocos, grupo):
        pdf.set_fill_color(43, 48, 56)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 10)

        titulo_origem = f"{indice:02d}. {self._label_fazenda_relatorio(grupo['codigo_origem'], grupo['nome_origem'], 'MUDA')}"
        pdf.cell(190, 8, self._latin1_safe(self._resumir_texto(titulo_origem, 96)), border=0, ln=1, fill=True)

        cards_y = pdf.get_y() + 1
        self._desenhar_info_bloco_pdf_geral(pdf, 10, cards_y, 50, "Variedade", grupo["variedade"])
        self._desenhar_info_bloco_pdf_geral(
            pdf,
            64,
            cards_y,
            70,
            "Periodo",
            f"{grupo['inicio'].strftime('%d/%m/%Y')} a {grupo['fim'].strftime('%d/%m/%Y')}",
        )
        self._desenhar_info_bloco_pdf_geral(
            pdf,
            138,
            cards_y,
            62,
            "Resumo",
            f"{self._fmt_int(grupo['total'])} viagens | {self._fmt_int(len(grupo['destinos']))} destinos",
        )
        pdf.set_y(cards_y + 12)

        talhoes_preview = self._resumir_lista(grupo["talhoes"], limite=12)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_text_color(73, 80, 87)
        pdf.set_font("Arial", "", 7)
        pdf.multi_cell(
            190,
            4.5,
            self._latin1_safe(f"Talhoes observados: {talhoes_preview}"),
            border=0,
            fill=True,
        )

        pdf.ln(1)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(51, 65, 85)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(24, 6, "COD.", 1, 0, "C", True)
        pdf.cell(126, 6, "FAZENDA DE PLANTIO", 1, 0, "L", True)
        pdf.cell(40, 6, "VIAGENS", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(51, 65, 85)
        fill = False
        for destino in grupo["destinos"]:
            if fill:
                pdf.set_fill_color(248, 250, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.cell(24, 6, self._latin1_safe(self._formatar_codigo_relatorio(destino["codigo"])), border=1, align="C", fill=fill)
            pdf.cell(126, 6, self._latin1_safe(self._resumir_texto(destino["nome"], 72)), border=1, fill=fill)
            pdf.cell(40, 6, self._fmt_int(destino["qtd"]), border=1, ln=1, align="C", fill=fill)
            fill = not fill

        pdf.set_font("Arial", "I", 7)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(190, 5, f"Bloco {indice}/{total_blocos}", ln=1, align="R")
        pdf.ln(4)

