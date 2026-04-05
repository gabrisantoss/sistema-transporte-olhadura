# App Notas - Sistema de Transporte

Aplicativo desktop em Python/PyQt5 para operacao de transporte da safra, com:

- lancamento e edicao de notas
- historico com filtros e exportacao
- dashboards e relatorios em Excel/PDF
- cadastro de motoristas, fazendas e variedades
- integracao com mapa e apoio de backup

## Como rodar

1. Crie um ambiente virtual.
2. Instale as dependencias de `requirements.txt`.
3. Opcionalmente, copie `app_notas.env.example` para `app_notas.env` e preencha as chaves.
4. Execute:

```bash
python main.py
```

## Configuracao local

O projeto le variaveis do sistema operacional e tambem um arquivo local `app_notas.env`.

Variaveis suportadas:

- `APP_NOTAS_OPENWEATHER_API_KEY`
- `APP_NOTAS_TELEGRAM_TOKEN`
- `APP_NOTAS_TELEGRAM_CHAT_ID`
- `APP_NOTAS_BACKUP_PATH`
- `APP_NOTAS_MAX_BACKUPS`

## Estrutura principal

- `main.py`: bootstrap da aplicacao, splash screen e inicializacao
- `main_window.py`: janela principal e abas
- `database.py`: conexao SQLite, schema e operacoes principais
- `reporting/`: base compartilhada para formatacao, PDFs e coleta de dados dos relatorios
- `tabs/`: interfaces por area funcional
- `workers.py`: tarefas em background para clima e Telegram
- `backup_manager.py`: backup local e no Drive
- `mapa_sistema.py`: app auxiliar para mapas e coordenadas
- `script_insercao.py`: utilitario para insercao/correcao em lote no banco

## Observacoes

- O banco principal fica em `transporte.db`.
- O seed inicial pode ser carregado de uma planilha local nao versionada em `seed_transporte_local.xlsm`.
- `tab_relatorios.py` agora concentra mais a UI e os gatilhos de exportacao; a base compartilhada, a coleta de dados e os builders de PDF foram movidos para `reporting/`.

## Proximos passos recomendados

- continuar separando a logica de relatorios em modulos menores
- criar testes para `database.py` e `script_insercao.py`
- mover artefatos gerados para pastas dedicadas fora da raiz
- revisar o fluxo de backup e restore com logs mais claros
