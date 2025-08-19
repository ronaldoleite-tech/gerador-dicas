# importador.py
import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Constantes de Configuração ---
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- ALTERAÇÃO AQUI: ADICIONAMOS A NOVA LOTERIA À LISTA DE IMPORTAÇÃO ---
LOTTERY_FILES = {
    'megasena': 'sorteadosmegasena.txt',
    'quina': 'sorteadosquina.txt',
    'lotofacil': 'sorteadoslotofacil.txt',
    'diadesorte': 'sorteadosdiadesorte.txt'  # <-- ESTA É A LINHA QUE FALTAVA
}

BATCH_SIZE = 500

def process_file(cursor, loteria, filename):
    """
    Processa um único arquivo de sorteio e insere os novos registros no banco de dados.
    """
    file_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(file_path):
        print(f"AVISO: Arquivo '{filename}' não encontrado. Pulando a importação para '{loteria}'.")
        return 0

    print(f"INFO: Processando arquivo '{filename}' para a loteria '{loteria}'...")
    
    newly_inserted = 0
    # Usamos latin-1 para compatibilidade máxima com arquivos gerados no Windows
    with open(file_path, 'r', encoding='latin-1') as f:
        try:
            header = next(f).strip().split('\t')
            col_indices = list(range(1, len(header)))

            batch = []
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
                        batch = []

                except (ValueError, IndexError):
                    print(f"AVISO: Linha com formato inesperado no arquivo {filename}: {line.strip()}")
                    continue
            
            if batch:
                insert_query = "INSERT INTO resultados_sorteados (concurso, tipo_loteria, dezenas) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING;"
                cursor.executemany(insert_query, batch)
                newly_inserted += cursor.rowcount
        
        except StopIteration:
            print(f"AVISO: O arquivo '{filename}' está vazio ou possui apenas o cabeçalho.")

    print(f"INFO: '{filename}' processado. {newly_inserted} novos registros adicionados.")
    return newly_inserted

def main():
    """
    Função principal que orquestra a conexão com o banco e a importação dos arquivos.
    """
    if not DATABASE_URL:
        print("ERRO: A variável de ambiente DATABASE_URL não foi encontrada. Verifique o arquivo .env")
        return

    conn = None
    try:
        print("INFO: Conectando ao banco de dados...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("INFO: Conexão com o banco de dados estabelecida com sucesso.")

        print("INFO: Verificando/Criando a tabela 'resultados_sorteados'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                concurso INT NOT NULL,
                tipo_loteria VARCHAR(20) NOT NULL,
                dezenas TEXT NOT NULL,
                UNIQUE(concurso, tipo_loteria)
            );
        """)
        print("INFO: Tabela 'resultados_sorteados' pronta.")

        total_inserted = 0
        for loteria, filename in LOTTERY_FILES.items():
            inserted_count = process_file(cur, loteria, filename)
            total_inserted += inserted_count
            conn.commit()

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

if __name__ == "__main__":
    main()