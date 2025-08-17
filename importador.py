import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

# Mapeamento dos arquivos para os tipos de loteria
LOTTERY_FILES = {
    'megasena': 'sorteadosmegasena.txt',
    'quina': 'sorteadosquina.txt',
    'lotofacil': 'sorteadoslotofacil.txt'
}

def process_file(cursor, loteria, filename):
    """Processa um arquivo de sorteio e insere no banco de dados."""
    file_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(file_path):
        print(f"AVISO: Arquivo '{filename}' não encontrado. Pulando.")
        return 0

    print(f"INFO: Processando arquivo '{filename}' para a loteria '{loteria}'...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        header = next(f).strip().split('\t') # Lê o cabeçalho
        col_indices = list(range(1, len(header))) # Pega os índices das dezenas

        batch = []
        BATCH_SIZE = 500
        newly_inserted = 0

        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < len(header):
                continue
            
            try:
                concurso = int(parts[0])
                dezenas = sorted([int(parts[i]) for i in col_indices])
                dezenas_str = " ".join(f"{d:02}" for d in dezenas)
                batch.append((concurso, loteria, dezenas_str))

                if len(batch) >= BATCH_SIZE:
                    insert_query = "INSERT INTO resultados_sorteados (concurso, tipo_loteria, dezenas) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING;"
                    cursor.executemany(insert_query, batch)
                    newly_inserted += cursor.rowcount
                    conn.commit()
                    batch = []

            except (ValueError, IndexError):
                print(f"AVISO: Linha com formato inesperado no arquivo {filename}: {line.strip()}")
                continue
        
        # Insere o lote final
        if batch:
            insert_query = "INSERT INTO resultados_sorteados (concurso, tipo_loteria, dezenas) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING;"
            cursor.executemany(insert_query, batch)
            newly_inserted += cursor.rowcount
            conn.commit()

    print(f"INFO: '{filename}' processado. {newly_inserted} novos registros adicionados.")
    return newly_inserted

if not DATABASE_URL:
    print("ERRO: A variável de ambiente DATABASE_URL não foi encontrada. Verifique o arquivo .env")
else:
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("INFO: Conexão com o banco de dados estabelecida.")

        # Cria a tabela se ela não existir (com a coluna 'tipo_loteria')
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                concurso INT NOT NULL,
                tipo_loteria VARCHAR(20) NOT NULL,
                dezenas TEXT NOT NULL,
                UNIQUE(concurso, tipo_loteria)
            );
        """)
        print("INFO: Tabela 'resultados_sorteados' verificada/criada.")

        total_inserted = 0
        for loteria, filename in LOTTERY_FILES.items():
            total_inserted += process_file(cur, loteria, filename)

        print("\n========================================================")
        print("IMPORTAÇÃO CONCLUÍDA!")
        print(f"Total de {total_inserted} novos registros adicionados ao banco de dados.")
        print("========================================================\n")

    except psycopg2.Error as e:
        print(f"\nERRO DE BANCO DE DADOS: {e}\n")
    except Exception as e:
        print(f"\nERRO INESPERADO: {e}\n")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexão com o banco de dados fechada.")