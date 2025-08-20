# importador.py
# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv
import certifi # Importa a nova biblioteca

# --- Configuração ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

LOTERIAS_API = {
    'megasena': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena',
    'lotofacil': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil',
    'quina': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/quina',
    'diadesorte': 'https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte'
}

# --- CORREÇÃO FINAL: Cabeçalhos mais completos para simular um navegador real ---
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- Funções do Banco de Dados (sem alterações) ---

def criar_tabela_se_nao_existir(conn):
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
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;",
            (loteria,)
        )
        resultado = cur.fetchone()[0]
        return resultado if resultado else 0

# --- Função Principal de Importação ---

def importar_resultados():
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
                # --- CORREÇÃO FINAL: Usamos os cabeçalhos e a verificação de certificado ---
                response = requests.get(url_base, headers=HEADERS, timeout=20, verify=certifi.where())
                response.raise_for_status()
                dados_api = response.json()
                ultimo_concurso_api = dados_api.get('numero')
            except requests.RequestException as e:
                print(f"Erro ao acessar a API da Caixa para {nome_loteria}: {e}")
                # DEBUG: Mostra os cabeçalhos que foram enviados na requisição que falhou
                if e.request:
                    print("Cabeçalhos enviados:", e.request.headers)
                continue

            if not ultimo_concurso_api:
                print("Não foi possível obter o número do último concurso da API.")
                continue
                
            print(f"Último concurso na API da Caixa: {ultimo_concurso_api}")

            if ultimo_concurso_api > ultimo_concurso_db:
                print(f"Novos resultados encontrados! Importando de {ultimo_concurso_db + 1} até {ultimo_concurso_api}...")
                
                # ... (resto do loop de importação, agora com os headers e verify) ...
                # (O código aqui dentro é o mesmo, só mudei a chamada requests.get)

                novos_registros = 0
                for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
                    try:
                        url_concurso = f"{url_base}/{concurso_num}"
                        res_concurso = requests.get(url_concurso, headers=HEADERS, timeout=20, verify=certifi.where())
                        # ... resto do código ...
                        res_concurso.raise_for_status()
                        dados_concurso = res_concurso.json()
                        dezenas_lista = dados_concurso.get('listaDezenas')
                        if not dezenas_lista:
                            continue
                        dezenas_str = " ".join(f"{int(n):02}" for n in dezenas_lista)
                        data_str = dados_concurso.get('dataApuracao')
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