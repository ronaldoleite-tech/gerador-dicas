# --- INÍCIO DO CÓDIGO FINAL E INTELIGENTE ---

import psycopg2
import os
from flask import Flask, jsonify, request
import random
from collections import Counter
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (se ele existir no ambiente local)
load_dotenv()

# --- Aplicação Flask ---
app = Flask(__name__, static_folder='.', static_url_path='')

# --- FUNÇÃO CENTRAL DE CONEXÃO (INTELIGENTE) ---
def get_db_connection():
    """
    Cria e retorna uma nova conexão.
    Detecta se está no ambiente de produção (Render) ou local.
    """
    # O Render define a variável DATABASE_URL automaticamente no ambiente de produção.
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # Se a variável existe, estamos no Render. Conecte-se usando ela.
        print("INFO: Conectando ao banco de dados de produção (Render)...")
        conn = psycopg2.connect(database_url)
    else:
        # Se não, estamos no ambiente local. Use a conexão direta à prova de bugs.
        print("INFO: Conectando ao banco de dados LOCAL...")
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            dbname="sorte_analisada_local",
            user="postgres",
            password="Dev12345"  # Sua senha local
        )
    return conn

# --- LÓGICA DE GERAÇÃO DE JOGOS (MÉTODO 1: COM FILTRO) ---
def gerar_jogos_com_base_na_frequencia(count):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados;")
        resultados = cur.fetchall()
        if not resultados:
            raise ValueError("O banco de dados está vazio.")
        
        todos_os_numeros = []
        for linha in resultados:
            numeros_da_linha = [int(n) for n in linha[0].split()]
            todos_os_numeros.extend(numeros_da_linha)
            
        frequencia = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia.keys())
        pesos = list(frequencia.values())
        
        jogos_gerados = set()
        max_tentativas = count * 20 
        tentativas = 0
        
        while len(jogos_gerados) < count and tentativas < max_tentativas:
            jogo_atual = set()
            while len(jogo_atual) < 6:
                numero_sorteado = random.choices(numeros_possiveis, weights=pesos, k=1)[0]
                jogo_atual.add(numero_sorteado)
            
            jogo_formatado = " ".join(f"{num:02}" for num in sorted(list(jogo_atual)))
            jogos_gerados.add(jogo_formatado)
            tentativas += 1
            
        return list(jogos_gerados)
    finally:
        if conn:
            conn.close()

# --- LÓGICA DE GERAÇÃO DE JOGOS (MÉTODO 2: PURO ALEATÓRIO) ---
def gerar_jogos_puramente_aleatorios(count):
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros = random.sample(range(1, 61), 6)
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros))
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)


# --- ROTAS DA APLICAÇÃO ---

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-games/<int:count>')
def get_games(count):
    try:
        usar_filtro = request.args.get('filtro', 'true', type=str).lower() == 'true'

        if usar_filtro:
            print("INFO: Gerando jogos com filtro de frequência.")
            jogos = gerar_jogos_com_base_na_frequencia(count)
        else:
            print("INFO: Gerando jogos puramente aleatórios (sem filtro).")
            jogos = gerar_jogos_puramente_aleatorios(count)
        
        return jsonify(jogos)
    except Exception as e:
        print(f"ERRO: Erro ao buscar jogos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status_do_banco():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM resultados_sorteados;")
        total_rows = cur.fetchone()[0]
        return jsonify({"status": "conectado", "total_de_concursos_no_bd": total_rows})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
@app.route('/get-stats')
def get_stats():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados;")
        ultimo_concurso_result = cur.fetchone()
        ultimo_concurso = ultimo_concurso_result[0] if ultimo_concurso_result else 0

        cur.execute("""
            SELECT numero::integer, COUNT(*) as frequencia
            FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero
                FROM resultados_sorteados
            ) as numeros_individuais
            GROUP BY numero
            ORDER BY frequencia DESC;
        """)
        frequencia_numeros = cur.fetchall()
        
        stats_data = [{"numero": n, "frequencia": f} for n, f in frequencia_numeros]

        return jsonify({
            "ultimo_concurso": ultimo_concurso,
            "frequencia": stats_data
        })
    except Exception as e:
        print(f"ERRO: Erro ao buscar estatísticas: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- FIM DO CÓDIGO FINAL E INTELIGENTE ---