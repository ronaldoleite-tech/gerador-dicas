# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                tipo_loteria VARCHAR(50) NOT NULL,
                concurso INTEGER NOT NULL,
                data_sorteio DATE,
                dezenas VARCHAR(255) NOT NULL,
                ganhadores INTEGER,
                acumulou BOOLEAN,
                mes_sorte VARCHAR(50),
                valor_acumulado DECIMAL(18, 2),
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

def processar_valor_acumulado(valor_acumulado, acumulou):
    """Processa o valor acumulado de forma mais robusta"""
    if not acumulou:
        return 0.0  # Se não acumulou, valor é 0
    
    if valor_acumulado is None:
        return None  # Valor desconhecido
    
    try:
        # Converte string para float se necessário
        if isinstance(valor_acumulado, str):
            # Remove R$, pontos e vírgulas, converte vírgula em ponto
            valor_limpo = valor_acumulado.replace('R$', '').replace('.', '').replace(',', '.').strip()
            return float(valor_limpo)
        return float(valor_acumulado)
    except (ValueError, TypeError):
        print(f"  ! Erro ao processar valor_acumulado: {valor_acumulado}")
        return None

def processar_data(data_str):
    """Processa a data de forma mais robusta"""
    try:
        if len(data_str) == 10 and '/' in data_str:
            # Formato dd/mm/yyyy
            return f"{data_str[6:]}-{data_str[3:5]}-{data_str[:2]}"
        else:
            # Tentar outros formatos
            print(f"  ! Formato de data inesperado: {data_str}")
            return data_str
    except Exception as e:
        print(f"  ! Erro ao processar data: {data_str} - {e}")
        return None

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
                print(f"Consultando API: {url_latest}")
                response = requests.get(url_latest, timeout=30)
                response.raise_for_status()
                dados_api = response.json()
                ultimo_concurso_api = dados_api.get('concurso')
                
                # Debug: mostrar alguns dados da API
                print(f"Dados da API: concurso={ultimo_concurso_api}, "
                      f"acumulou={dados_api.get('acumulou')}, "
                      f"valorAcumulado={dados_api.get('valorAcumulado')}")
                
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
                        
                        # Processar dados com mais validação
                        dezenas_lista = dados_concurso.get('dezenas')
                        if not dezenas_lista: 
                            print(f"  ! Concurso {concurso_num}: sem dezenas")
                            continue
                        
                        dezenas_str = " ".join(sorted(dezenas_lista))
                        data_str = dados_concurso.get('data')
                        if not data_str:
                            print(f"  ! Concurso {concurso_num}: sem data")
                            continue
                            
                        data_formatada = processar_data(data_str)
                        if not data_formatada:
                            continue
                        
                        acumulou = dados_concurso.get('acumulou', False)
                        valor_acumulado_raw = dados_concurso.get('valorAcumulado')
                        valor_acumulado = processar_valor_acumulado(valor_acumulado_raw, acumulou)
                        
                        ganhadores_faixa1 = 0
                        if dados_concurso.get('premiacoes') and len(dados_concurso['premiacoes']) > 0:
                            ganhadores_faixa1 = dados_concurso['premiacoes'][0].get('ganhadores', 0)
                        
                        # Mês da Sorte (apenas para Dia de Sorte)
                        mes_sorte = None
                        if nome_loteria == 'diadesorte':
                            mes_sorte = dados_concurso.get('mesSorte')

                        # Debug para o último concurso
                        if concurso_num == ultimo_concurso_api:
                            print(f"  > ÚLTIMO CONCURSO - Dados processados:")
                            print(f"    Concurso: {concurso_num}")
                            print(f"    Data: {data_formatada}")
                            print(f"    Dezenas: {dezenas_str}")
                            print(f"    Acumulou: {acumulou}")
                            print(f"    Valor bruto: {valor_acumulado_raw}")
                            print(f"    Valor processado: {valor_acumulado}")
                            print(f"    Ganhadores: {ganhadores_faixa1}")

                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO resultados_sorteados (
                                    tipo_loteria, concurso, data_sorteio, dezenas, 
                                    ganhadores, acumulou, mes_sorte, valor_acumulado
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (tipo_loteria, concurso) DO UPDATE SET 
                                    data_sorteio = EXCLUDED.data_sorteio, 
                                    dezenas = EXCLUDED.dezenas, 
                                    ganhadores = EXCLUDED.ganhadores,
                                    acumulou = EXCLUDED.acumulou,
                                    mes_sorte = EXCLUDED.mes_sorte,
                                    valor_acumulado = EXCLUDED.valor_acumulado;
                                """,
                                (
                                    nome_loteria,
                                    concurso_num,
                                    data_formatada,
                                    dezenas_str,
                                    ganhadores_faixa1,
                                    acumulou,
                                    mes_sorte,
                                    valor_acumulado
                                )
                            )
                                
                        novos_registros += 1
                        
                    except Exception as e:
                        print(f"  - Erro ao processar concurso {concurso_num}: {e}. Pulando.")
                
                conn.commit()
                print(f"Sucesso! {novos_registros} novos resultados para {nome_loteria} foram importados.")
                
                # Verificar se o último registro foi inserido corretamente
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT concurso, acumulou, valor_acumulado, ganhadores 
                        FROM resultados_sorteados 
                        WHERE tipo_loteria = %s 
                        ORDER BY concurso DESC 
                        LIMIT 1
                    """, (nome_loteria,))
                    ultimo_registro = cur.fetchone()
                    if ultimo_registro:
                        print(f"  > Último registro no DB: concurso={ultimo_registro[0]}, "
                              f"acumulou={ultimo_registro[1]}, "
                              f"valor={ultimo_registro[2]}, "
                              f"ganhadores={ultimo_registro[3]}")
                
            else:
                print("Nenhum novo resultado para importar. O banco de dados está atualizado.")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("\nConexão com o banco de dados fechada.")

if __name__ == "__main__":
    importar_resultados()