# importador.py
# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

LOTERIAS_API = {
    'megasena': 'https://loteriascaixa-api.herokuapp.com/api/megasena',
    'lotofacil': 'https://loteriascaixa-api.herokuapp.com/api/lotofacil',
    'quina': 'https://loteriascaixa-api.herokuapp.com/api/quina',
    'diadesorte': 'https://loteriascaixa-api.herokuapp.com/api/diadesorte'
}

def criar_tabela_se_nao_existir(conn):
    with conn.cursor() as cur:
        # --- ALTERAÇÃO: Adicionamos as colunas 'ganhadores' e 'acumulou' ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                tipo_loteria VARCHAR(50) NOT NULL,
                concurso INTEGER NOT NULL,
                data_sorteio DATE,
                dezenas VARCHAR(255) NOT NULL,
                ganhadores INTEGER,
                acumulou BOOLEAN,
                UNIQUE (tipo_loteria, concurso)
            );
        """)
        conn.commit()
    print("Tabela 'resultados_sorteados' verificada/criada com sucesso.")

def get_ultimo_concurso(conn, loteria):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultado = cur.fetchone()[0]
        return resultado if resultado else 0

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
                url_latest = f"{url_base}/latest"
                response = requests.get(url_latest, timeout=30)
                response.raise_for_status()
                dados_api = response.json()
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

                        dezenas_lista = dados_concurso.get('dezenas')
                        if not dezenas_lista: continue
                        
                        dezenas_str = " ".join(sorted(dezenas_lista))
                        data_str = dados_concurso.get('data')
                        data_formatada = f"{data_str[6:]}-{data_str[3:5]}-{data_str[:2]}"
                        
                        # --- ALTERAÇÃO: Captura dos novos dados ---
                        acumulou = dados_concurso.get('acumulou', False)
                        # Pega os ganhadores da primeira faixa de premiação
                        ganhadores_faixa1 = 0
                        if dados_concurso.get('premiacoes') and len(dados_concurso['premiacoes']) > 0:
                            ganhadores_faixa1 = dados_concurso['premiacoes'][0].get('ganhadores', 0)

                        with conn.cursor() as cur:
                            # --- ALTERAÇÃO: Insere os novos dados no banco ---
                            cur.execute(
                                """
                                INSERT INTO resultados_sorteados (tipo_loteria, concurso, data_sorteio, dezenas, ganhadores, acumulou)
                                VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (tipo_loteria, concurso) DO NOTHING;
                                """,
                                (nome_loteria, concurso_num, data_formatada, dezenas_str, ganhadores_faixa1, acumulou)
                            )
                        novos_registros += 1
                    except Exception as e:
                        print(f"  - Erro ao processar concurso {concurso_num}: {e}. Pulando.")
                
                conn.commit()
                print(f"Sucesso! {novos_registros} novos resultados para {nome_loteria} foram importados.")
            else:
                print("Nenhum novo resultado para importar. O banco de dados está atualizado.")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
    finally:
        if conn:
            conn.close()
            print("\nConexão com o banco de dados fechada.")

if __name__ == "__main__":
    importar_resultados()