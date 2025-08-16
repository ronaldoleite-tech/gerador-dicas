# --- Conteúdo FINAL E CORRIGIDO para importador_local.py ---
import psycopg2
import os

# --- CONEXÃO DIRETA COM O BANCO DE DADOS LOCAL ---
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        dbname="sorte_analisada_local",
        user="postgres",
        password="Dev12345" # Verifique se esta é sua senha local correta
    )

LOTERIAS_A_IMPORTAR = {
    'megasena': 'sorteadosmegasena.txt',
    'quina': 'sorteadosquina.txt',
    'lotofacil': 'sorteadoslotofacil.txt'
}

def realizar_importacao():
    conn = None
    try:
        print("INFO: Conectando ao banco de dados LOCAL...")
        conn = get_db_connection()
        cur = conn.cursor()
        print("INFO: Conexão bem-sucedida.")

        print("INFO: Atualizando estrutura da tabela...")
        # Adiciona a coluna se ela não existir
        cur.execute("ALTER TABLE resultados_sorteados ADD COLUMN IF NOT EXISTS tipo_loteria VARCHAR(50);")
        
        # --- MUDANÇA PRINCIPAL E FINAL AQUI ---
        # 1. Tenta remover a restrição antiga de concurso único (NÃO dá erro se não existir)
        cur.execute("ALTER TABLE resultados_sorteados DROP CONSTRAINT IF EXISTS resultados_sorteados_concurso_key;")
        # 2. Tenta remover a nova restrição (para garantir que possamos recriá-la)
        cur.execute("ALTER TABLE resultados_sorteados DROP CONSTRAINT IF EXISTS resultados_sorteados_concurso_loteria_unique;")
        # 3. Adiciona a nova restrição correta (concurso + loteria)
        cur.execute("ALTER TABLE resultados_sorteados ADD CONSTRAINT resultados_sorteados_concurso_loteria_unique UNIQUE (concurso, tipo_loteria);")
        conn.commit()
        print("INFO: Estrutura da tabela atualizada com a nova regra de unicidade.")

        total_inserido_geral = 0
        for tipo_loteria, nome_arquivo in LOTERIAS_A_IMPORTAR.items():
            print(f"\n--- Processando: {tipo_loteria.upper()} ---")
            caminho_arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_arquivo)
            if not os.path.exists(caminho_arquivo):
                print(f"AVISO: Arquivo '{nome_arquivo}' não encontrado. Pulando.")
                continue

            with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                print(f"INFO: Lendo '{nome_arquivo}'...")
                next(f)
                batch = []
                for line in f:
                    try:
                        parts = line.strip().split()
                        if len(parts) < 2: continue
                        num_concurso = int(parts[0])
                        dezenas = " ".join(sorted(parts[1:], key=int))
                        batch.append((num_concurso, dezenas, tipo_loteria))
                    except ValueError:
                        continue
                
                if batch:
                    insert_query = "INSERT INTO resultados_sorteados (concurso, dezenas, tipo_loteria) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING"
                    cur.executemany(insert_query, batch)
                    conn.commit()
                    print(f"INFO: {cur.rowcount} novos registros de {tipo_loteria.upper()} inseridos.")
                    total_inserido_geral += cur.rowcount
        
        print(f"\nIMPORTAÇÃO CONCLUÍDA. Total de novos registros: {total_inserido_geral}")

    except Exception as e:
        print(f"\nERRO DURANTE A IMPORTAÇÃO: {e}\n")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexão fechada.")

if __name__ == "__main__":
    realizar_importacao()