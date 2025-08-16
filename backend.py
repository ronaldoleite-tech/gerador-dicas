# --- CONTEÚDO COMPLETO DO ARQUIVO backend.py (CORRIGIDO) ---

import psycopg2
import os
from flask import Flask, jsonify, request
import random
from collections import Counter
from dotenv import load_dotenv
import math

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
app = Flask(__name__, static_folder='.', static_url_path='')

# --- CONFIGURAÇÃO CENTRAL DE LOTERIAS (COM A CORREÇÃO) ---
LOTTERY_CONFIG = {
    'megasena': {'min_num': 1, 'max_num': 60, 'min_dezenas': 6, 'max_dezenas': 20, 'num_bolas_sorteadas': 6, 'default_dezenas': 6},
    'quina':    {'min_num': 1, 'max_num': 80, 'min_dezenas': 5, 'max_dezenas': 15, 'num_bolas_sorteadas': 5, 'default_dezenas': 5},
    'lotofacil':{'min_num': 1, 'max_num': 25, 'min_dezenas': 15, 'max_dezenas': 20, 'num_bolas_sorteadas': 15, 'default_dezenas': 15}
}

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def is_prime(n):
    if n < 2: return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0: return False
    return True

def gerar_jogo_monte_carlo(loteria='megasena'):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a simulação de {loteria}.")

        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split()]
        frequencia_historica = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia_historica.keys())
        pesos_historicos = list(frequencia_historica.values())

        simulacoes = 100000
        resultados_simulacao = Counter()
        for _ in range(simulacoes):
            sorteio_simulado = random.choices(numeros_possiveis, weights=pesos_historicos, k=config['num_bolas_sorteadas'])
            resultados_simulacao.update(sorteio_simulado)
        
        jogo_monte_carlo = resultados_simulacao.most_common(config['num_bolas_sorteadas'])
        numeros_do_jogo = [num for num, freq in jogo_monte_carlo]
        
        return " ".join(f"{num:02}" for num in sorted(numeros_do_jogo))
    finally:
        if conn: conn.close()

def gerar_jogos_com_base_na_frequencia(loteria, count, dezenas):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        if not resultados: raise ValueError(f"O banco de dados está vazio para {loteria}.")
        
        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split()]
        frequencia = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia.keys())
        pesos = list(frequencia.values())
        
        jogos_gerados = set()
        max_tentativas = count * 1000
        tentativas = 0
        while len(jogos_gerados) < count and tentativas < max_tentativas:
            jogo_atual = frozenset(random.choices(numeros_possiveis, weights=pesos, k=dezenas))
            if len(jogo_atual) == dezenas:
                jogos_gerados.add(jogo_atual)
            tentativas += 1
            
        return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]
    finally:
        if conn: conn.close()

def gerar_jogos_puramente_aleatorios(loteria, count, dezenas):
    config = LOTTERY_CONFIG[loteria]
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros = random.sample(range(config['min_num'], config['max_num'] + 1), dezenas)
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros))
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    loteria = request.args.get('loteria', 'megasena', type=str)
    try:
        jogo = gerar_jogo_monte_carlo(loteria)
        return jsonify({"jogo": jogo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-games/<int:count>')
def get_games(count):
    loteria = request.args.get('loteria', 'megasena', type=str)
    usar_filtro = request.args.get('filtro', 'true', type=str).lower() == 'true'
    dezenas = request.args.get('dezenas', LOTTERY_CONFIG[loteria]['default_dezenas'], type=int)
    try:
        if usar_filtro:
            jogos = gerar_jogos_com_base_na_frequencia(loteria, count, dezenas)
        else:
            jogos = gerar_jogos_puramente_aleatorios(loteria, count, dezenas)
        return jsonify(jogos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-stats')
def get_stats():
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        ultimo_concurso = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT numero::integer, COUNT(*) FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero FROM resultados_sorteados WHERE tipo_loteria = %s
            ) as numeros_individuais GROUP BY numero ORDER BY numero::integer ASC;
        """, (loteria,))
        frequencia_numeros = [{"numero": n, "frequencia": f} for n, f in cur.fetchall()]

        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        todos_sorteios = cur.fetchall()
        
        contagem_primos = Counter()
        contagem_pares = Counter()
        
        for sorteio_tuple in todos_sorteios:
            numeros = [int(n) for n in sorteio_tuple[0].split()]
            if len(numeros) == config['num_bolas_sorteadas']:
                primos_no_sorteio = sum(1 for n in numeros if is_prime(n))
                pares_no_sorteio = sum(1 for n in numeros if n % 2 == 0)
                contagem_primos.update([primos_no_sorteio])
                contagem_pares.update([pares_no_sorteio])
        
        return jsonify({
            "ultimo_concurso": ultimo_concurso,
            "frequencia": frequencia_numeros,
            "stats_primos": dict(contagem_primos),
            "stats_pares": dict(contagem_pares)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)