# backend.py
# -*- coding: utf-8 -*-
import psycopg2
import os
from flask import Flask, jsonify, request
import random
from collections import Counter
from dotenv import load_dotenv
import math
import re # Importa a biblioteca de expressões regulares para sanitização

# --- (Inicialização e Configuração - sem alterações) ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
app = Flask(__name__, static_folder='.', static_url_path='')
LOTTERY_CONFIG = {
    'megasena':   {'min_num': 1, 'max_num': 60, 'num_bolas_sorteadas': 6, 'default_dezenas': 6},
    'quina':      {'min_num': 1, 'max_num': 80, 'num_bolas_sorteadas': 5, 'default_dezenas': 5},
    'lotofacil':  {'min_num': 1, 'max_num': 25, 'num_bolas_sorteadas': 15, 'default_dezenas': 15},
    'diadesorte': {'min_num': 1, 'max_num': 31, 'num_bolas_sorteadas': 7, 'default_dezenas': 7}
}

# --- Funções Auxiliares e de Lógica ---

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def is_prime(n):
    if n < 2: return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0: return False
    return True

# --- ALTERAÇÃO 1: NOVA FUNÇÃO DE VALIDAÇÃO SEGURA ---
def validar_e_sanitizar_ancora(ancora_str, loteria):
    """
    Valida e limpa a string de entrada do usuário para os números âncora.
    - Remove caracteres perigosos para prevenir XSS e SQL Injection.
    - Converte para números inteiros.
    - Valida se os números estão dentro do intervalo da loteria.
    - Limita a quantidade de números âncora.
    """
    if not ancora_str:
        return []

    config = LOTTERY_CONFIG[loteria]
    
    # 1. Sanitização: Permite apenas números, vírgulas e espaços. Remove todo o resto.
    sanitized_str = re.sub(r'[^0-9,]', '', ancora_str)
    
    # 2. Validação Lógica
    numeros_ancora = set()
    try:
        parts = [p.strip() for p in sanitized_str.split(',') if p.strip()]
        for part in parts:
            num = int(part)
            if config['min_num'] <= num <= config['max_num']:
                numeros_ancora.add(num)
            else:
                # Ignora silenciosamente números fora do intervalo
                continue
    except (ValueError, TypeError):
        # Se a conversão falhar, retorna uma lista vazia
        return []
        
    # 3. Limitação: Permite no máximo 3 números âncora para simplificar a lógica.
    return sorted(list(numeros_ancora))[:3]


def gerar_jogo_monte_carlo(loteria='megasena', numeros_ancora=[]):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = config['num_bolas_sorteadas'] - len(numeros_ancora)
        if dezenas_a_gerar <= 0:
            return " ".join(f"{num:02}" for num in sorted(numeros_ancora))
        
        # ... (lógica de conexão e busca de frequência - sem alterações) ...
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a simulação de {loteria}.")
        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        
        # ... (lógica da simulação Monte Carlo - sem alterações) ...
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


def gerar_jogos_com_base_na_frequencia(loteria, count, dezenas, numeros_ancora=[]):
    conn = None
    try:
        dezenas_a_gerar = dezenas - len(numeros_ancora)
        if dezenas_a_gerar < 0: return [] # Caso inválido

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        if not resultados: raise ValueError(f"O banco de dados está vazio para {loteria}.")
        
        # Remove os números âncora da população de sorteio
        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia.keys())
        pesos = list(frequencia.values())
        
        jogos_gerados = set()
        while len(jogos_gerados) < count:
            if dezenas_a_gerar > 0:
                numeros_novos = frozenset(random.choices(numeros_possiveis, weights=pesos, k=dezenas_a_gerar))
                if len(numeros_novos) == dezenas_a_gerar:
                    jogo_completo = frozenset(numeros_novos.union(set(numeros_ancora)))
                    jogos_gerados.add(jogo_completo)
            else: # Caso o usuário já tenha fornecido todas as dezenas
                jogos_gerados.add(frozenset(numeros_ancora))

        return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]
    finally:
        if conn: conn.close()


def gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora=[]):
    config = LOTTERY_CONFIG[loteria]
    dezenas_a_gerar = dezenas - len(numeros_ancora)
    if dezenas_a_gerar < 0: return []
    
    # Remove os números âncora do universo de números possíveis
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

# --- ALTERAÇÃO 2: ENDPOINTS MODIFICADOS PARA ACEITAR NÚMEROS ÂNCORA ---
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
    
    # Garante que a quantidade de dezenas seja pelo menos a quantidade de números âncora
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

# ... (rota /get-stats e bloco de execução principal sem alterações) ...
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