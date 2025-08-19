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
# Constante para estratégias de dezenas quentes/frias
CONCURSOS_RECENTES = 100

# --- Funções Auxiliares e de Lógica ---

def get_db_connection():
    # Adicionar uma verificação para a tabela de feedback
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            choice VARCHAR(4) NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
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

# NOVA FUNÇÃO PRINCIPAL para gerar jogos com base na frequência
def gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora=[], estrategia='geral'):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = dezenas - len(numeros_ancora)
        if dezenas_a_gerar < 0: return []

        conn = get_db_connection()
        cur = conn.cursor()
        
        # SQL dinâmico baseado na estratégia
        if estrategia in ['quentes', 'frias']:
            # Busca apenas os últimos N concursos
            cur.execute("""
                SELECT dezenas FROM resultados_sorteados 
                WHERE tipo_loteria = %s 
                ORDER BY concurso DESC 
                LIMIT %s;
            """, (loteria, CONCURSOS_RECENTES))
        else: # Estratégia 'geral'
            cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        
        resultados = cur.fetchall()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a estratégia '{estrategia}' em {loteria}.")
        
        todos_os_numeros_sorteados = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia = Counter(todos_os_numeros_sorteados)
        
        numeros_possiveis = []
        pesos = []
        
        if estrategia == 'frias':
            # Para dezenas frias, o peso é o inverso da frequência
            universo_possivel = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
            max_freq = max(frequencia.values()) if frequencia else 1
            
            for num in universo_possivel:
                freq_num = frequencia.get(num, 0) # Frequência do número (0 se nunca saiu)
                numeros_possiveis.append(num)
                pesos.append(max_freq - freq_num + 1) # +1 para garantir que o peso não seja zero
        else: # Para 'geral' e 'quentes', o peso é a própria frequência
            numeros_possiveis = list(frequencia.keys())
            pesos = list(frequencia.values())

        if not numeros_possiveis: # Fallback para aleatório se não houver dados
             return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)

        jogos_gerados = set()
        while len(jogos_gerados) < count:
            if dezenas_a_gerar > 0:
                numeros_novos = frozenset(random.choices(numeros_possiveis, weights=pesos, k=dezenas_a_gerar))
                if len(numeros_novos) == dezenas_a_gerar: # Garante que não haja números repetidos
                    jogo_completo = frozenset(numeros_novos.union(set(numeros_ancora)))
                    jogos_gerados.add(jogo_completo)
            else:
                jogos_gerados.add(frozenset(numeros_ancora))
                break # Sai do loop se não precisa gerar mais números

        return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]
    finally:
        if conn: conn.close()


def gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora=[]):
    config = LOTTERY_CONFIG[loteria]
    dezenas_a_gerar = dezenas - len(numeros_ancora)
    if dezenas_a_gerar < 0: return []
    
    universo = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]

    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros_novos = random.sample(universo, dezenas_a_gerar)
        jogo_completo = sorted(numeros_novos + numeros_ancora)
        jogo_formatado = " ".join(f"{num:02}" for num in jogo_completo)
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)


# --- Endpoints da API ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Endpoint do Monte Carlo (sem alterações significativas)
@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    loteria = request.args.get('loteria', 'megasena', type=str)
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    try:
        # A simulação Monte Carlo por padrão usa a frequência geral
        jogo = gerar_jogo_monte_carlo(loteria, numeros_ancora)
        return jsonify({"jogo": jogo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ENDPOINT DE GERAÇÃO DE JOGOS ATUALIZADO
@app.route('/get-games/<int:count>')
def get_games(count):
    loteria = request.args.get('loteria', 'megasena', type=str)
    estrategia = request.args.get('estrategia', 'geral', type=str) # Novo parâmetro
    dezenas = request.args.get('dezenas', LOTTERY_CONFIG[loteria]['default_dezenas'], type=int)
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    
    if dezenas < len(numeros_ancora):
        dezenas = len(numeros_ancora)

    try:
        if estrategia == 'aleatorio':
            jogos = gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
        else: # 'geral', 'quentes', 'frias'
            jogos = gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora, estrategia)
        return jsonify(jogos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NOVO ENDPOINT PARA FEEDBACK
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

# Endpoint de estatísticas (sem alterações)
@app.route('/get-stats')
def get_stats():
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
    usar_filtro = request.args.get('filtro', 'true', type=str).lower() == 'true'
    dezenas = request.args.get('dezenas', LOTTERY_CONFIG[loteria]['default_dezenas'], type=int)
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    
    if dezenas < len(numeros_ancora):
        dezenas = len(numeros_ancora)

    try:
        if usar_filtro:
            jogos = gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora)
        else:
            jogos = gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
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