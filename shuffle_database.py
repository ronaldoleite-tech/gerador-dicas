import psycopg2
import os
import time

# Cole a sua Internal Connection URL aqui
DATABASE_URL = os.environ.get('DATABASE_URL_FOR_SHUFFLE', 'COLE_SUA_URL_AQUI_SE_FOR_RODAR_LOCALMENTE')

def shuffle_table():
    conn = None
    print("--- INICIANDO PROCESSO DE EMBARALHAMENTO DO BANCO DE DADOS ---")
    print("AVISO: Este processo pode levar muito tempo!")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # Aumenta o timeout da transação para aguentar a operação longa
        conn.autocommit = True 
        cur = conn.cursor()

        print("\nPasso 1 de 3: Criando uma nova tabela embaralhada (combinations_shuffled)...")
        start_time = time.time()
        # Este comando cria a nova tabela já com os dados embaralhados
        cur.execute("""
            CREATE TABLE combinations_shuffled AS
            SELECT combination FROM combinations ORDER BY RANDOM();
        """)
        end_time = time.time()
        print(f"  -> Tabela embaralhada criada com sucesso em {end_time - start_time:.2f} segundos.")

        print("\nPasso 2 de 3: Deletando a tabela antiga e renomeando a nova...")
        start_time = time.time()
        cur.execute("DROP TABLE combinations;")
        cur.execute("ALTER TABLE combinations_shuffled RENAME TO combinations;")
        end_time = time.time()
        print(f"  -> Tabelas trocadas com sucesso em {end_time - start_time:.2f} segundos.")

        print("\nPasso 3 de 3: Recriando a chave primária e a regra de unicidade...")
        start_time = time.time()
        cur.execute("ALTER TABLE combinations ADD COLUMN id SERIAL PRIMARY KEY;")
        cur.execute("ALTER TABLE combinations ADD CONSTRAINT combination_unique UNIQUE (combination);")
        end_time = time.time()
        print(f"  -> Chave primária e regra UNIQUE recriadas com sucesso em {end_time - start_time:.2f} segundos.")

        print("\n--- PROCESSO CONCLUÍDO! Seu banco de dados foi permanentemente embaralhado. ---")

    except Exception as e:
        print(f"\n--- OCORREU UM ERRO DURANTE O EMBARALHAMENTO ---")
        print(f"Erro: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    shuffle_table()