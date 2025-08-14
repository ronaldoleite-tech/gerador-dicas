import psycopg2
import os
from dotenv import load_dotenv

def realizar_importacao():
    load_dotenv()
    DATABASE_URL = os.environ.get('DATABASE_URL')
    FILE_PATH_PARA_IMPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sorteados.txt')
    BATCH_SIZE = 500

    if not DATABASE_URL:
        print("ERRO: A variável de ambiente DATABASE_URL não foi definida.")
        return

    print("INFO: Iniciando o script de importação.")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("INFO: Conectado ao DB para importação.")

        # Recriar a tabela garante que a estrutura esteja correta
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                concurso INT UNIQUE NOT NULL,
                dezenas TEXT NOT NULL
            );
        """)
        print("INFO: Tabela 'resultados_sorteados' (com coluna 'concurso') verificada/criada.")
        
        batch = []
        total_inserted = 0
        
        with open(FILE_PATH_PARA_IMPORTAR, 'r', encoding='utf-8') as f:
            next(f) # Pula a primeira linha (cabeçalho)

            for line in f:
                parts = line.strip().split()
                if len(parts) >= 7: # Garante que a linha tem o concurso + 6 dezenas
                    try:
                        num_concurso = int(parts[0])
                        dezenas = parts[1:]
                        # Ordena as dezenas para garantir um formato único
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
        print("IMPORTAÇÃO CONCLUÍDA!")
        print(f"{total_inserted} novos concursos foram adicionados ao banco de dados.")
        print("========================================================\n")

    except FileNotFoundError:
        print(f"ERRO: O arquivo '{FILE_PATH_PARA_IMPORTAR}' não foi encontrado.")
    except Exception as e:
        print(f"\nERRO: Um erro inesperado ocorreu durante a importação: {e}\n")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    realizar_importacao()