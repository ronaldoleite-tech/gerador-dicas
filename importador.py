# importador.py
# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv

# --- Configuração ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- ATUALIZAÇÃO: Usando a nova API do Heroku ---
# A API espera os nomes das loterias em minúsculas e sem acentos
LOTERIAS_API = {
    'megasena': 'https://loteriascaixa-api.herokuapp.com/api/megasena',
    'lotofacil': 'https://loteriascaixa-api.herokuapp.com/api/lotofacil',
    'quina': 'https://loteriascaixa-api.herokuapp.com/api/quina',
    'diadesorte': 'https://loteriascaixa-api.herokuapp.com/api/diadesorte'
}

# --- Funções do Banco de Dados (sem alterações) ---

def criar_tabela_se_nao_existir(conn):
    """Garante que a tabela de resultados exista no banco de dados."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                tipo_loteria VARCHAR(50) NOT NULL,
                concurso INTEGER NOT NULL,
                data_sorteio DATE,
                dezenas VARCHAR(255) NOT NULL,
                UNIQUE (tipo_loteria, concurso)
            );
        """)
        conn.commit()
    print("Tabela 'resultados_sorteados' verificada/criada com sucesso.")

def get_ultimo_concurso(conn, loteria):
    """Busca o número do último concurso registrado para uma loteria específica."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;",
            (loteria,)
        )
        resultado = cur.fetchone()[0]
        return resultado if resultado else 0

# --- Função Principal de Importação ---

def importar_resultados():
    """Função principal que orquestra a busca e inserção de novos resultados."""
    conn = None
    try:
        print("Conectando ao banco de dados...")
        conn = psycopg2.connect(DATABASE_URL)
        criar_tabela_se_nao_existir(conn)

        for nome_loteria, url_base in LOTERIAS_API.items():
            print(f"\n--- Verificando Loteria: {nome_loteria.upper()} ---")
            
            ultimo_concurso_db = get_ultimo_concurso(conn, nome_loteria)
            print(f"Último concurso no banco de dados: {ultimo_concurso_db}")

            try:
                # Busca o último concurso disponível na nova API
                url_latest = f"{url_base}/latest"
                response = requests.get(url_latest, timeout=30) # Aumentado o timeout para Heroku
                response.raise_for_status()
                dados_api = response.json()
                # ATUALIZAÇÃO: O campo agora é 'concurso'
                ultimo_concurso_api = dados_api.get('concurso')
            except requests.RequestException as e:
                print(f"Erro ao acessar a API para {nome_loteria}: {e}")
                continue

            if not ultimo_concurso_api:
                print("Não foi possível obter o número do último concurso da API.")
                continue
                
            print(f"Último concurso na API: {ultimo_concurso_api}")

            if ultimo_concurso_api > ultimo_concurso_db:
                print(f"Novos resultados encontrados! Importando de {ultimo_concurso_db + 1} até {ultimo_concurso_api}...")
                
                novos_registros = 0
                for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
                    try:
                        url_concurso = f"{url_base}/{concurso_num}"
                        res_concurso = requests.get(url_concurso, timeout=30)
                        res_concurso.raise_for_status()
                        dados_concurso = res_concurso.json()

                        # ATUALIZAÇÃO: O campo de dezenas agora é 'dezenas'
                        dezenas_lista = dados_concurso.get('dezenas')
                        if not dezenas_lista:
                            print(f"  - Concurso {concurso_num} sem dezenas. Pulando.")
                            continue
                        
                        dezenas_str = " ".join(sorted(dezenas_lista)) # A API retorna strings, não precisa formatar
                        # ATUALIZAÇÃO: O campo de data agora é 'data'
                        data_str = dados_concurso.get('data')
                        data_formatada = f"{data_str[6:]}-{data_str[3:5]}-{data_str[:2]}"

                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO resultados_sorteados (tipo_loteria, concurso, data_sorteio, dezenas)
                                VALUES (%s, %s, %s, %s) ON CONFLICT (tipo_loteria, concurso) DO NOTHING;
                                """,
                                (nome_loteria, concurso_num, data_formatada, dezenas_str)
                            )
                        novos_registros += 1
                    except requests.RequestException as e:
                        print(f"  - Erro ao buscar concurso {concurso_num}: {e}. Pulando.")
                    except (KeyError, TypeError, IndexError) as e:
                        print(f"  - Erro ao processar dados do concurso {concurso_num}: {e}. Pulando.")
                
                conn.commit()
                print(f"Sucesso! {novos_registros} novos resultados para {nome_loteria} foram importados.")
            else:
                print("Nenhum novo resultado para importar. O banco de dados está atualizado.")

    except psycopg2.Error as e:
        print(f"Erro de banco de dados: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            conn.close()
            print("\nConexão com o banco de dados fechada.")

if __name__ == "__main__":
    importar_resultados()