# --- CONTEÚDO COMPLETO DO ARQUIVO backend.py (ATUALIZADO) ---

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

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- FUNÇÃO AUXILIAR PARA VERIFICAR NÚMEROS PRIMOS ---
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

# --- FUNÇÃO DA SIMULAÇÃO DE MONTE CARLO (EXISTENTE) ---
def gerar_jogo_monte_carlo():
    # ... (código existente, sem alterações)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados;")
        resultados = cur.fetchall()
        if not resultados:
            raise ValueError("O banco de dados está vazio para a simulação.")

        todos_os_numeros = []
        for linha in resultados:
            numeros_da_linha = [int(n) for n in linha[0].split()]
            todos_os_numeros.extend(numeros_da_linha)

        frequencia_historica = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia_historica.keys())
        pesos_historicos = list(frequencia_historica.values())
        
        simulacoes = 100000
        resultados_simulacao = Counter()

        for _ in range(simulacoes):
            sorteio_simulado = random.choices(numeros_possiveis, weights=pesos_historicos, k=6)
            resultados_simulacao.update(sorteio_simulado)
        
        jogo_monte_carlo = resultados_simulacao.most_common(6)
        numeros_do_jogo = [num for num, freq in jogo_monte_carlo]
        
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros_do_jogo))
        return jogo_formatado

    finally:
        if conn:
            conn.close()

# ... (outras funções de geração de jogos existentes, sem alterações) ...
def gerar_jogos_com_base_na_frequencia(count, dezenas=6):
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
            while len(jogo_atual) < dezenas:
                numero_sorteado = random.choices(numeros_possiveis, weights=pesos, k=1)[0]
                jogo_atual.add(numero_sorteado)
            
            jogo_formatado = " ".join(f"{num:02}" for num in sorted(list(jogo_atual)))
            jogos_gerados.add(jogo_formatado)
            tentativas += 1
            
        return list(jogos_gerados)
    finally:
        if conn:
            conn.close()

def gerar_jogos_puramente_aleatorios(count, dezenas=6):
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros = random.sample(range(1, 61), dezenas)
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros))
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)


# --- ROTAS DA APLICAÇÃO ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    try:
        jogo = gerar_jogo_monte_carlo()
        return jsonify({"jogo": jogo})
    except Exception as e:
        print(f"ERRO: Erro ao gerar jogo Monte Carlo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-games/<int:count>')
def get_games(count):
    try:
        usar_filtro = request.args.get('filtro', 'true', type=str).lower() == 'true'
        dezenas = request.args.get('dezenas', 6, type=int)
        
        if usar_filtro:
            jogos = gerar_jogos_com_base_na_frequencia(count, dezenas)
        else:
            jogos = gerar_jogos_puramente_aleatorios(count, dezenas)
        return jsonify(jogos)
    except Exception as e:
        print(f"ERRO: Erro ao buscar jogos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status_do_banco():
    # ... (código existente, sem alterações)
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
        
        # --- Cálculo de frequência (existente) ---
        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados;")
        ultimo_concurso = cur.fetchone()[0] or 0
        cur.execute("""
            SELECT numero::integer, COUNT(*) FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero FROM resultados_sorteados
            ) as numeros_individuais GROUP BY numero ORDER BY numero::integer ASC;
        """)
        frequencia_numeros = [{"numero": n, "frequencia": f} for n, f in cur.fetchall()]

        # --- NOVOS CÁLCULOS DE PRIMOS E PARES/ÍMPARES ---
        cur.execute("SELECT dezenas FROM resultados_sorteados;")
        todos_sorteios = cur.fetchall()
        
        contagem_primos_por_sorteio = []
        contagem_pares_por_sorteio = []

        for sorteio_tuple in todos_sorteios:
            numeros = [int(n) for n in sorteio_tuple[0].split()]
            # Apenas para jogos de 6 dezenas
            if len(numeros) == 6:
                primos_no_sorteio = sum(1 for n in numeros if is_prime(n))
                pares_no_sorteio = sum(1 for n in numeros if n % 2 == 0)
                contagem_primos_por_sorteio.append(primos_no_sorteio)
                contagem_pares_por_sorteio.append(pares_no_sorteio)

        stats_primos = Counter(contagem_primos_por_sorteio)
        stats_pares = Counter(contagem_pares_por_sorteio)

        return jsonify({
            "ultimo_concurso": ultimo_concurso,
            "frequencia": frequencia_numeros,
            "stats_primos": dict(stats_primos),
            "stats_pares": dict(stats_pares)
        })

    except Exception as e:
        print(f"ERRO: Erro ao buscar estatísticas: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)