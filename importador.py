import psycopg2
import os
from dotenv import load_dotenv

def realizar_importacao():
    """
    Script para popular o banco de dados com os resultados dos sorteios.
    Este script deve ser executado manualmente, não como parte do servidor web.
    """
    # Carrega as variáveis de ambiente de um arquivo .env (ótimo para desenvolvimento local)
    load_dotenv()
    
    # Pega as configurações do ambiente
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

        # Garante que a tabela exista
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                dezenas TEXT NOT NULL UNIQUE
            );
        """)
        print("INFO: Tabela 'resultados_sorteados' verificada/criada.")
        
        batch = []
        total_inserted = 0
        
        # Abre o arquivo de sorteios e processa em lotes
        with open(FILE_PATH_PARA_IMPORTAR, 'r', encoding='utf-8') as f:
            next(f) # Pula a primeira linha (cabeçalho)

            for line in f:
                numeros = line.strip().split() 
                if len(numeros) == 6:
                    # Ordena os números para garantir um formato único
                    linha_formatada = " ".join(sorted(numeros, key=int))
                    batch.append((linha_formatada,))
                
                # Quando o lote atingir o tamanho máximo, insere no banco
                if len(batch) >= BATCH_SIZE:
                    insert_query = "INSERT INTO resultados_sorteados (dezenas) VALUES (%s) ON CONFLICT (dezenas) DO NOTHING"
                    cur.executemany(insert_query, batch)
                    novos_registros = cur.rowcount if cur.rowcount is not None else 0
                    total_inserted += novos_registros
                    conn.commit()
                    print(f"INFO: Lote inserido. {novos_registros} novos registros adicionados.")
                    batch = []

        # Insere qualquer registro restante no lote final
        if batch:
            insert_query = "INSERT INTO resultados_sorteados (dezenas) VALUES (%s) ON CONFLICT (dezenas) DO NOTHING"
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

# Este bloco permite que o script seja executado diretamente pelo terminal
if __name__ == "__main__":
    realizar_importacao()  