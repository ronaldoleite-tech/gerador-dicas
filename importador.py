# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import datetime

# Carrega variáveis do .env
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

# APIs das loterias
LOTERIAS_API = {
    "megasena": "https://loteriascaixa-api.herokuapp.com/api/megasena",
    "lotofacil": "https://loteriascaixa-api.herokuapp.com/api/lotofacil",
    "quina": "https://loteriascaixa-api.herokuapp.com/api/quina",
    "diadesorte": "https://loteriascaixa-api.herokuapp.com/api/diadesorte",
}

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL não está definida no .env")

    # Esconde senha para debug
    parsed = urlparse(DATABASE_URL)
    safe_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
    print(f"Conectando ao banco: {safe_url}")

    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def criar_tabela(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resultados_sorteados (
            id SERIAL PRIMARY KEY,
            tipo_loteria VARCHAR(50) NOT NULL,
            concurso INTEGER NOT NULL,
            data_sorteio DATE,
            dezenas VARCHAR(255) NOT NULL,
            ganhadores INTEGER DEFAULT 0,
            acumulou BOOLEAN DEFAULT FALSE,
            mes_sorte VARCHAR(50),
            valor_acumulado DECIMAL(18, 2),
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tipo_loteria, concurso)
        );
    """)
    conn.commit()
    cur.close()
    print("✅ Tabela verificada/criada")

def get_ultimo_concurso(conn, loteria):
    cur = conn.cursor()
    cur.execute("SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
    r = cur.fetchone()[0]
    cur.close()
    return r if r else 0

def formatar_data(data_str):
    """
    Converte data do formato DD/MM/YYYY para YYYY-MM-DD (formato ISO)
    """
    if not data_str:
        return None
    
    try:
        # Se a data já está no formato correto (YYYY-MM-DD), retorna ela
        if len(data_str) == 10 and data_str[4] == '-' and data_str[7] == '-':
            return data_str
            
        # Se está no formato DD/MM/YYYY, converte para YYYY-MM-DD
        if '/' in data_str:
            data_obj = datetime.strptime(data_str, '%d/%m/%Y')
            return data_obj.strftime('%Y-%m-%d')
            
        # Se está no formato DD-MM-YYYY, converte para YYYY-MM-DD  
        if '-' in data_str and len(data_str) == 10:
            partes = data_str.split('-')
            if len(partes[0]) == 2:  # DD-MM-YYYY
                data_obj = datetime.strptime(data_str, '%d-%m-%Y')
                return data_obj.strftime('%Y-%m-%d')
                
        return data_str
    except Exception as e:
        print(f"⚠️ Erro ao formatar data '{data_str}': {e}")
        return None

def importar_resultados():
    print("🚀 Iniciando importação...")

    try:
        conn = get_db_connection()
        criar_tabela(conn)

        for nome, url_base in LOTERIAS_API.items():
            print(f"\n📌 Loteria: {nome.upper()}")

            ultimo_concurso_db = get_ultimo_concurso(conn, nome)
            print(f"Último no banco: {ultimo_concurso_db}")

            try:
                # Pega o último disponível na API
                r = requests.get(f"{url_base}/latest", timeout=30).json()
                ultimo_concurso_api = r.get("concurso")
                print(f"Último na API: {ultimo_concurso_api}")

                if not ultimo_concurso_api or ultimo_concurso_api <= ultimo_concurso_db:
                    print("Nenhum novo concurso para importar.")
                    continue

                novos = 0
                erros = 0
                
                for c in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
                    try:
                        print(f"➡️ Importando concurso {c}...")
                        dados = requests.get(f"{url_base}/{c}", timeout=30).json()
                        if not dados:
                            print(f"⚠️ Falha ao buscar concurso {c}")
                            erros += 1
                            continue

                        dezenas = " ".join(sorted(map(str, dados.get("dezenas", []))))
                        data_original = dados.get("data")
                        data_formatada = formatar_data(data_original)
                        
                        if data_original and not data_formatada:
                            print(f"⚠️ Data inválida no concurso {c}: {data_original}")
                            erros += 1
                            continue
                            
                        acumulou = dados.get("acumulou", False)
                        ganhadores = 0
                        if dados.get("premiacoes"):
                            ganhadores = dados["premiacoes"][0].get("ganhadores", 0)
                        mes_sorte = dados.get("mesSorte") if nome == "diadesorte" else None
                        valor_acumulado = None
                        if acumulou:
                            valor_acumulado = dados.get("valorEstimadoProximoConcurso")

                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO resultados_sorteados
                            (tipo_loteria, concurso, data_sorteio, dezenas, ganhadores, acumulou, mes_sorte, valor_acumulado)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (tipo_loteria, concurso) DO NOTHING;
                        """, (nome, c, data_formatada, dezenas, ganhadores, acumulou, mes_sorte, valor_acumulado))
                        conn.commit()
                        cur.close()
                        novos += 1
                        
                    except Exception as e:
                        print(f"❌ Erro ao importar concurso {c}: {e}")
                        erros += 1
                        continue

                print(f"✅ Importados {novos} novos concursos para {nome}")
                if erros > 0:
                    print(f"⚠️ {erros} erros durante a importação de {nome}")
                    
            except Exception as e:
                print(f"❌ Erro ao processar loteria {nome}: {e}")
                continue

        conn.close()
        print("\n🎉 Importação concluída!")
        
    except Exception as e:
        print(f"❌ Erro fatal na importação: {e}")
        raise

if __name__ == "__main__":
    importar_resultados()