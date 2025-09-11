# --- CÓDIGO COMPLETO E FINAL para backend.py ---

# -*- coding: utf-8 -*-
import psycopg2
import os
from flask import Flask, jsonify, request, render_template # <-- render_template foi adicionado
import random
from collections import Counter
from dotenv import load_dotenv
import math
import re
from datetime import date
import numpy as np

# --- Inicialização e Configuração ---
load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
# Flask agora procurará a pasta 'templates' automaticamente
app = Flask(__name__) 
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
    if not ancora_str or not re.match(r'^\d+$', ancora_str.strip()):
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

# --- FUNÇÕES DAS ESTRATÉGIAS DE GERAÇÃO ---

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

# --- FUNÇÕES PARA A ESTRATÉGIA SORTE ANALISADA PREMIUM ---

def _analisar_perfil_historico(loteria, resultados):
    config = LOTTERY_CONFIG[loteria]
    somas, paridades, distribuicoes_quadrantes = [], [], []
    limite_q1 = math.ceil(config['max_num'] / 4)
    limite_q2, limite_q3 = limite_q1 * 2, limite_q1 * 3

    for linha in resultados:
        dezenas = [int(n) for n in linha[0].split()]
        if len(dezenas) != config['num_bolas_sorteadas']: continue
        somas.append(sum(dezenas))
        num_pares = sum(1 for d in dezenas if d % 2 == 0)
        paridades.append((num_pares, config['num_bolas_sorteadas'] - num_pares))
        quadrantes = set()
        for d in dezenas:
            if d <= limite_q1: quadrantes.add(1)
            elif d <= limite_q2: quadrantes.add(2)
            elif d <= limite_q3: quadrantes.add(3)
            else: quadrantes.add(4)
        distribuicoes_quadrantes.append(len(quadrantes))

    soma_ideal = (int(np.percentile(somas, 25)), int(np.percentile(somas, 75))) if somas else (0, 0)
    paridade_ideal = Counter(paridades).most_common(2) if paridades else []
    quadrantes_ideal = Counter(distribuicoes_quadrantes).most_common(1)[0][0] if distribuicoes_quadrantes else 3

    return {"soma_ideal": soma_ideal, "paridade_ideal": [p[0] for p in paridade_ideal], "quadrantes_ideal": quadrantes_ideal}

def _calcular_score_do_jogo(jogo_set, perfil, config):
    score = 0
    dezenas = list(jogo_set)
    if perfil["soma_ideal"][0] <= sum(dezenas) <= perfil["soma_ideal"][1]:
        score += 1
    num_pares = sum(1 for d in dezenas if d % 2 == 0)
    if (num_pares, config['num_bolas_sorteadas'] - num_pares) in perfil["paridade_ideal"]:
        score += 1
    limite_q1 = math.ceil(config['max_num'] / 4)
    limite_q2, limite_q3 = limite_q1 * 2, limite_q1 * 3
    quadrantes = {1 if d <= limite_q1 else 2 if d <= limite_q2 else 3 if d <= limite_q3 else 4 for d in dezenas}
    if len(quadrantes) >= perfil["quadrantes_ideal"]:
        score += 1
    return score

def gerar_jogo_sorte_analisada_premium(loteria='megasena'):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = config['num_bolas_sorteadas']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        if not resultados: raise ValueError("Base de dados histórica não encontrada para análise.")
        
        perfil_historico = _analisar_perfil_historico(loteria, resultados)
        combinacoes_passadas = {frozenset(int(n) for n in linha[0].split()) for linha in resultados}

        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split()]
        frequencia_historica = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia_historica.keys())
        pesos_historicos = list(frequencia_historica.values())
        
        pool_candidatos = set()
        num_candidatos = 200
        while len(pool_candidatos) < num_candidatos:
            jogo_candidato = frozenset(random.choices(numeros_possiveis, weights=pesos_historicos, k=dezenas_a_gerar))
            if len(jogo_candidato) == dezenas_a_gerar:
                pool_candidatos.add(jogo_candidato)
        
        candidatos_unicos = [jogo for jogo in pool_candidatos if jogo not in combinacoes_passadas]
        
        if not candidatos_unicos:
            while True:
                jogo_aleatorio = frozenset(random.sample(range(config['min_num'], config['max_num'] + 1), dezenas_a_gerar))
                if jogo_aleatorio not in combinacoes_passadas:
                    return " ".join(f"{num:02}" for num in sorted(list(jogo_aleatorio)))

        jogos_pontuados = [( _calcular_score_do_jogo(jogo_set, perfil_historico, config), jogo_set) for jogo_set in candidatos_unicos]
        jogos_pontuados.sort(key=lambda x: x[0], reverse=True)
        
        melhor_score = jogos_pontuados[0][0]
        melhores_jogos = [jogo for score, jogo in jogos_pontuados if score == melhor_score]
        
        jogo_escolhido = random.choice(melhores_jogos)
        return " ".join(f"{num:02}" for num in sorted(list(jogo_escolhido)))
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
        if estrategia in ['quentes', 'frias', 'mistas']:
            query += " ORDER BY concurso DESC LIMIT %s"
            params.append(CONCURSOS_RECENTES)
        
        cur.execute(query, tuple(params))
        resultados = cur.fetchall()
        cur.close()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a estratégia '{estrategia}' em {loteria}.")
        
        todos_os_numeros_sorteados = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia = Counter(todos_os_numeros_sorteados)
        universo_possivel = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
        
        jogos_gerados = set()
        
        if estrategia == 'frias':
            numeros_possiveis = [n for n in universo_possivel if n not in frequencia]
            if len(numeros_possiveis) < dezenas_a_gerar:
                 numeros_possiveis.extend([item[0] for item in frequencia.most_common()[:-len(numeros_possiveis)-1:-1]])
            pesos = None
        
        elif estrategia == 'mistas':
            numeros_quentes = list(frequencia.keys())
            pesos_quentes = list(frequencia.values())
            numeros_frios = [n for n in universo_possivel if n not in frequencia]
            if len(numeros_frios) < dezenas_a_gerar:
                numeros_frios.extend([item[0] for item in frequencia.most_common()[:-len(numeros_frios)-1:-1]])
            
            if not numeros_quentes or not numeros_frios:
                return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)

            while len(jogos_gerados) < count:
                numeros_novos = set()
                if dezenas_a_gerar > 0:
                    num_a_gerar_quentes = math.ceil(dezenas_a_gerar / 2)
                    num_a_gerar_frios = math.floor(dezenas_a_gerar / 2)
                    num_a_gerar_quentes = min(num_a_gerar_quentes, len(numeros_quentes))
                    num_a_gerar_frios = min(num_a_gerar_frios, len(numeros_frios))

                    dezenas_quentes_selecionadas = set()
                    while len(dezenas_quentes_selecionadas) < num_a_gerar_quentes:
                        dezena = random.choices(numeros_quentes, weights=pesos_quentes, k=1)[0]
                        dezenas_quentes_selecionadas.add(dezena)

                    dezenas_frias_selecionadas = set(random.sample(numeros_frios, num_a_gerar_frios))
                    numeros_novos = dezenas_quentes_selecionadas.union(dezenas_frias_selecionadas)

                    while len(numeros_novos) < dezenas_a_gerar:
                        universo_completo = list(set(numeros_quentes + numeros_frios))
                        numeros_novos.add(random.choice(universo_completo))

                jogo_completo = frozenset(numeros_novos.union(set(numeros_ancora)))
                if len(jogo_completo) == dezenas:
                    jogos_gerados.add(jogo_completo)

            return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]

        else: # Estratégia 'geral' ou 'quentes'
            numeros_possiveis = list(frequencia.keys())
            pesos = list(frequencia.values())

        if not numeros_possiveis:
             return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
             
        while len(jogos_gerados) < count:
            if dezenas_a_gerar > 0:
                numeros_novos = set()
                if pesos is None: # Lógica para 'frias'
                    k = min(dezenas_a_gerar, len(numeros_possiveis))
                    numeros_novos = set(random.sample(numeros_possiveis, k))
                else: # Lógica para 'geral' e 'quentes'
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
    # Usa o método render_template, que procura na pasta 'templates'
    return render_template('index.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

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

@app.route('/get-sorte-analisada-premium-game')
def get_sorte_analisada_premium_game():
    loteria = request.args.get('loteria', 'megasena', type=str)
    try:
        jogo = gerar_jogo_sorte_analisada_premium(loteria)
        return jsonify({"jogo": jogo})
    except Exception as e:
        print(f"ERRO em /get-sorte-analisada-premium-game: {e}")
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

@app.route('/get-ultimos-resultados')
def get_ultimos_resultados():
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT concurso, data_sorteio, dezenas, ganhadores, acumulou, mes_sorte 
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC 
            LIMIT 20;
        """, (loteria,))
        
        resultados = []
        for row in cur.fetchall():
            data_formatada = row[1].strftime('%d/%m/%Y') if isinstance(row[1], date) else row[1]
            
            resultados.append({
                "concurso": row[0],
                "data": data_formatada,
                "dezenas": row[2],
                "ganhadores": row[3],
                "acumulou": row[4],
                "mes_sorte": row[5]
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