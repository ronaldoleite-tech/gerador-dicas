# --- INÍCIO DO importador.py CORRIGIDO ---

import psycopg2
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

def realizar_importacao():
    # Pega a URL de conexão do ambiente (do arquivo .env)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        print("ERRO: A variável DATABASE_URL não foi encontrada. Verifique seu arquivo .env")
        return

    conn = None
    try:
        print("INFO: Tentando conectar ao banco de dados...")
        # A conexão agora usa a variável DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("INFO: CONEXÃO COM O BANCO DE DADOS REALIZADA COM SUCESSO!")

        FILE_PATH_PARA_IMPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sorteados.txt')
        BATCH_SIZE = 500

        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                concurso INT UNIQUE NOT NULL,
                dezenas TEXT NOT NULL
            );
        """)
        print("INFO: Tabela 'resultados_sorteados' verificada/criada.")
        
        batch = []
        total_inserted = 0
        
        # O encoding 'cp1252' é ótimo para arquivos de texto do Windows
        with open(FILE_PATH_PARA_IMPORTAR, 'r', encoding='cp1252') as f:
            print("INFO: Arquivo 'sorteados.txt' aberto com sucesso.")
            next(f) 

            for line in f:
                parts = line.strip().split()
                if len(parts) >= 7:
                    try:
                        num_concurso = int(parts[0])
                        dezenas = parts[1:]
                        linha_formatada = " ".join(sorted(dezenas, key=int))
                        batch.append((num_concurso, linha_formatada))
                    except ValueError:
                        print(f"AVISO: Linha ignorada por formato inválido: {line.strip()}")
                        continue
                
                if len(batch) >= BATCH_SIZE:
                    insert_query = "INSERT INTO resultados_sorteados (concurso, dezenas) VALUES (%s, %s) ON CONFLICT (concurso) DO NOTHING"
                    cur.executemany(insert_query, batch)
                    novos_registros = cur.rowcount if cur.rowcount is not None else 0
                    total_inserted += novos_registros
                    conn.commit()
                    print(f"INFO: Lote inserido. {novos_registros} novos registros adicionados.")
                    batch = []

        if batch:
            insert_query = "INSERT INTO resultados_sorteados (concurso, dezenas) VALUES (%s, %s) ON CONFLICT (concurso) DO NOTHING"
            cur.executemany(insert_query, batch)
            novos_registros = cur.rowcount if cur.rowcount is not None else 0
            total_inserted += novos_registros
            conn.commit()
            print(f"INFO: Lote final inserido. {novos_registros} novos registros adicionados.")

        print("\n========================================================")
        print("IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"{total_inserted} novos concursos foram adicionados ao banco de dados.")
        print("========================================================\n")

    except Exception as e:
        print(f"\nERRO: Um erro inesperado ocorreu durante a importação: {e}\n")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    realizar_importacao()

# --- FIM DO importador.py CORRIGIDO ---