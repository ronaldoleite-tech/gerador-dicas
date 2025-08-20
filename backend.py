# backend.py
# -*- coding: utf-8 -*-
import psycopg2
import os
from flask import Flask, jsonify, request
import random
from collections import Counter
from dotenv import load_dotenv
import math
import re
from datetime import date # IMPORTANTE: Adicionado para formatar a data

# --- Inicialização e Configuração ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
app = Flask(__name__, static_folder='.', static_url_path='')
LOTTERY_CONFIG = {
    'megasena':   {'min_num': 1, 'max_num': 60, 'num_bolas_sorteadas': 6, 'default_dezenas': 6},
    'quina':      {'min_num': 1, 'max_num': 80, 'num_bolas_sorteadas': 5, 'default_dezenas': 5},
    'lotofacil':  {'min_num': 1, 'max_num': 25, 'num_bolas_sorteadas': 15, 'default_dezenas': 15},
    'diadesorte': {'min_num': 1, 'max_num': 31, 'num_bolas_sorteadas': 7, 'default_dezenas': 7}
}
CONCURSOS_RECENTES = 100

# --- Funções Auxiliares e de Lógica ---

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                choice VARCHAR(4) NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
    return conn

def is_prime(n):
    if n < 2: return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0: return False
    return True

def validar_e_sanitizar_ancora(ancora_str, loteria):
    if not ancora_str or not ancora_str.strip().isdigit():
        return []
    config = LOTTERY_CONFIG[loteria]
    try:
        num = int(ancora_str)
        if config['min_num'] <= num <= config['max_num']:
            return [num]
        else:
            return []
    except (ValueError, TypeError):
        return []

def gerar_jogo_monte_carlo(loteria='megasena', numeros_ancora=[]):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = config['num_bolas_sorteadas'] - len(numeros_ancora)
        if dezenas_a_gerar <= 0:
            return " ".join(f"{num:02}" for num in sorted(numeros_ancora))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        cur.close()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a simulação de {loteria}.")
        
        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia_historica = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia_historica.keys())
        pesos_historicos = list(frequencia_historica.values())
        simulacoes = 100000
        resultados_simulacao = Counter()
        for _ in range(simulacoes):
            sorteio_simulado = random.choices(numeros_possiveis, weights=pesos_historicos, k=dezenas_a_gerar)
            resultados_simulacao.update(sorteio_simulado)
        
        numeros_da_simulacao = list(resultados_simulacao.keys())
        pesos_da_simulacao = list(resultados_simulacao.values())
        
        numeros_novos = set()
        while len(numeros_novos) < dezenas_a_gerar:
            numero_sorteado = random.choices(numeros_da_simulacao, weights=pesos_da_simulacao, k=1)[0]
            numeros_novos.add(numero_sorteado)
        
        jogo_final = sorted(list(numeros_novos.union(set(numeros_ancora))))
        return " ".join(f"{num:02}" for num in jogo_final)
    
    finally:
        if conn: conn.close()

def gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora=[], estrategia='geral'):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = dezenas - len(numeros_ancora)
        if dezenas_a_gerar < 0: return []
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = "SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s"
        params = [loteria]
        if estrategia in ['quentes', 'frias']:
            query += " ORDER BY concurso DESC LIMIT %s"
            params.append(CONCURSOS_RECENTES)
        
        cur.execute(query, tuple(params))
        resultados = cur.fetchall()
        cur.close()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a estratégia '{estrategia}' em {loteria}.")
        
        todos_os_numeros_sorteados = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia = Counter(todos_os_numeros_sorteados)
        universo_possivel = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
        
        if estrategia == 'frias':
            numeros_possiveis = [n for n in universo_possivel if n not in frequencia]
            if len(numeros_possiveis) < dezenas_a_gerar:
                 numeros_possiveis.extend([item[0] for item in frequencia.most_common()[:-len(numeros_possiveis)-1:-1]])
            pesos = None
        else:
            numeros_possiveis = list(frequencia.keys())
            pesos = list(frequencia.values())
        if not numeros_possiveis:
             return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
        jogos_gerados = set()
        while len(jogos_gerados) < count:
            if dezenas_a_gerar > 0:
                numeros_novos = set()
                if pesos is None:
                    k = min(dezenas_a_gerar, len(numeros_possiveis))
                    numeros_novos = set(random.sample(numeros_possiveis, k))
                else:
                    while len(numeros_novos) < dezenas_a_gerar:
                        numero_sorteado = random.choices(numeros_possiveis, weights=pesos, k=1)[0]
                        numeros_novos.add(numero_sorteado)
                
                jogo_completo = frozenset(numeros_novos.union(set(numeros_ancora)))
                jogos_gerados.add(jogo_completo)
            else:
                jogos_gerados.add(frozenset(numeros_ancora))
                break
        return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]
    finally:
        if conn: conn.close()

def gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora=[]):
    config = LOTTERY_CONFIG[loteria]
    dezenas_a_gerar = dezenas - len(numeros_ancora)
    if dezenas_a_gerar < 0: return []
    
    universo = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
    k = min(dezenas_a_gerar, len(universo))
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros_novos = random.sample(universo, k)
        jogo_completo = sorted(numeros_novos + numeros_ancora)
        jogo_formatado = " ".join(f"{num:02}" for num in jogo_completo)
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)

# --- Endpoints da API ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    loteria = request.args.get('loteria', 'megasena', type=str)
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    try:
        jogo = gerar_jogo_monte_carlo(loteria, numeros_ancora)
        return jsonify({"jogo": jogo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-games/<int:count>')
def get_games(count):
    loteria = request.args.get('loteria', 'megasena', type=str)
    estrategia = request.args.get('estrategia', 'geral', type=str)
    dezenas = request.args.get('dezenas', type=int)
    if dezenas is None:
        dezenas = LOTTERY_CONFIG[loteria]['default_dezenas']
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    
    if dezenas < len(numeros_ancora):
        dezenas = len(numeros_ancora)
    try:
        if estrategia == 'aleatorio':
            jogos = gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
        else:
            jogos = gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora, estrategia)
        return jsonify(jogos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    conn = None
    try:
        data = request.get_json()
        choice = data.get('choice')
        if choice not in ['sim', 'nao']:
            return jsonify({"error": "Escolha inválida"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO feedback (choice) VALUES (%s);", (choice,))
        conn.commit()
        cur.close()
        return jsonify({"success": True, "message": "Feedback recebido!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

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
        cur.close()
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

# --- NOVO ENDPOINT PARA A SEÇÃO DE ÚLTIMOS RESULTADOS ---
@app.route('/get-ultimos-resultados')
def get_ultimos_resultados():
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT concurso, data_sorteio, dezenas, ganhadores, acumulou 
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC 
            LIMIT 36;
        """, (loteria,))
        
        resultados = []
        for row in cur.fetchall():
            # Formata a data para o padrão brasileiro (DD/MM/YYYY)
            data_formatada = row[1].strftime('%d/%m/%Y') if isinstance(row[1], date) else row[1]
            
            resultados.append({
                "concurso": row[0],
                "data": data_formatada,
                "dezenas": row[2],
                "ganhadores": row[3],
                "acumulou": row[4]
            })
            
        cur.close()
        return jsonify(resultados)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('RENDER') is None
    app.run(host='0.0.0.0', port=port, debug=debug_mode)