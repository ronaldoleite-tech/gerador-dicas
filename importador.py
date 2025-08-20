# importador.py
# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

# --- Configuração ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

LOTERIAS_API = {
    'megasena': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena',
    'lotofacil': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil',
    'quina': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/quina',
    'diadesorte': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte'
}

# --- CORREÇÃO: Adicionamos um cabeçalho para simular um navegador e evitar o erro 403 ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Funções do Banco de Dados ---

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

        # Itera sobre cada loteria configurada
        for nome_loteria, url_base in LOTERIAS_API.items():
            print(f"\n--- Verificando Loteria: {nome_loteria.upper()} ---")
            
            ultimo_concurso_db = get_ultimo_concurso(conn, nome_loteria)
            print(f"Último concurso no banco de dados: {ultimo_concurso_db}")

            # Pega o último concurso da API da Caixa
            try:
                # --- CORREÇÃO: Usamos o cabeçalho na requisição ---
                response = requests.get(url_base, headers=HEADERS, timeout=15)
                response.raise_for_status() # Lança um erro se a requisição falhar (como 403)
                dados_api = response.json()
                ultimo_concurso_api = dados_api.get('numero')
            except requests.RequestException as e:
                print(f"Erro ao acessar a API da Caixa para {nome_loteria}: {e}")
                continue # Pula para a próxima loteria

            if not ultimo_concurso_api:
                print("Não foi possível obter o número do último concurso da API.")
                continue
                
            print(f"Último concurso na API da Caixa: {ultimo_concurso_api}")

            # Compara e importa os concursos faltantes
            if ultimo_concurso_api > ultimo_concurso_db:
                print(f"Novos resultados encontrados! Importando de {ultimo_concurso_db + 1} até {ultimo_concurso_api}...")
                
                novos_registros = 0
                for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
                    try:
                        url_concurso = f"{url_base}/{concurso_num}"
                        # --- CORREÇÃO: Usamos o cabeçalho na requisição ---
                        res_concurso = requests.get(url_concurso, headers=HEADERS, timeout=15)
                        res_concurso.raise_for_status()
                        dados_concurso = res_concurso.json()

                        # Extrai e formata os dados
                        dezenas_lista = dados_concurso.get('listaDezenas')
                        if not dezenas_lista:
                            print(f"  - Concurso {concurso_num} sem lista de dezenas. Pulando.")
                            continue
                        
                        dezenas_str = " ".join(f"{int(n):02}" for n in dezenas_lista)
                        data_str = dados_concurso.get('dataApuracao')
                        # Formata a data de DD/MM/YYYY para YYYY-MM-DD
                        data_formatada = f"{data_str[6:]}-{data_str[3:5]}-{data_str[:2]}"

                        # Insere no banco de dados
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
                    except (KeyError, TypeError) as e:
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