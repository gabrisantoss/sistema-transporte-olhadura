import sqlite3
import shutil
import sys
import os

DB_PATH = "transporte.db"
BKP_PATH = "transporte_bkp_padronizacao.db"

def padronizar_banco():
    # 1. Backup de Segurança
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BKP_PATH)
        print(f">>> 1. BACKUP CRIADO: {BKP_PATH}")
    else:
        print(f"!!! ERRO: Banco {DB_PATH} não encontrado.")
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print(">>> 2. INICIANDO PADRONIZAÇÃO DE DADOS...\n")

        # --- PASSO A: Limpeza geral (Maiúsculas e sem espaços sobrando) ---
        cursor.execute("UPDATE notas SET faz_muda_nome = UPPER(TRIM(faz_muda_nome)) WHERE faz_muda_nome IS NOT NULL")
        cursor.execute("UPDATE notas SET faz_plantio_nome = UPPER(TRIM(faz_plantio_nome)) WHERE faz_plantio_nome IS NOT NULL")
        cursor.execute("UPDATE notas SET variedade_nome = UPPER(TRIM(variedade_nome)) WHERE variedade_nome IS NOT NULL")
        print("[-] Limpeza de strings (Maiúsculas/Trim) aplicada em todas as notas.")

        # --- PASSO B: Sincronização de Código -> Nome (Garante que o mesmo código tem o mesmo nome) ---
        # 1. Atualiza as origens (faz_muda_nome) com base na tabela mestre 'fazendas'
        cursor.execute("""
            UPDATE notas 
            SET faz_muda_nome = UPPER(TRIM((SELECT nome FROM fazendas WHERE fazendas.codigo = notas.faz_muda_cod)))
            WHERE faz_muda_cod IS NOT NULL 
              AND EXISTS (SELECT 1 FROM fazendas WHERE fazendas.codigo = notas.faz_muda_cod)
        """)
        print(f"[-] Nomes de ORIGEM sincronizados com a tabela mestre: {cursor.rowcount} registros verificados/alterados.")

        # 2. Aplica hardcode de segurança para os códigos específicos trabalhados hoje (caso não existam na tabela mestre)
        fazendas_map = {
            '1031594': 'FAZ BREJO LIMPO',
            '103154': 'FAZ IPANEMA A',
            '103161': 'FAZ MATA DA CHUVA B',
            '103156': 'FAZ LIMOEIRO A'
        }

        for cod, nome in fazendas_map.items():
            cursor.execute("UPDATE notas SET faz_muda_nome = ? WHERE faz_muda_cod = ?", (nome, cod))
            # Caso a coluna faz_plantio_cod esteja preenchida, padroniza também o destino
            cursor.execute("UPDATE notas SET faz_plantio_nome = ? WHERE faz_plantio_cod = ?", (nome, cod))
            
        print("[-] Garantia de integridade para Brejo Limpo, Ipanema A, Mata da Chuva B e Limoeiro A aplicada.")

        # Salva as alterações
        conn.commit()
        print("\n>>> 3. SUCESSO! Banco de dados padronizado e limpo.")

    except Exception as e:
        conn.rollback()
        print(f"\n!!! ERRO FATAL DURANTE A EXECUÇÃO: {e}")
        print(">>> Alterações revertidas (Rollback). O banco de dados está intacto.")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    padronizar_banco()
