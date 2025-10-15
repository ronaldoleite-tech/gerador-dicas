# -*- coding: utf-8 -*-
import psycopg2
import os
from flask import Flask, jsonify, request, render_template, send_from_directory
import random
from collections import Counter
import math
import re
from datetime import date
import numpy as np

# --- Inicialização e Configuração ---
app = Flask(__name__)

LOTTERY_CONFIG = {
    'maismilionaria': {'min_num': 1, 'max_num': 50,   'min_dezenas': 6,  'max_dezenas': 12, 'num_bolas_sorteadas': 6,  'default_dezenas': 6, 'num_trevos_sorteados': 2, 'min_trevo': 1, 'max_trevo': 6},
    'megasena':   {'min_num': 1, 'max_num': 60,   'min_dezenas': 6,  'max_dezenas': 20, 'num_bolas_sorteadas': 6,  'default_dezenas': 6},
    'quina':      {'min_num': 1, 'max_num': 80,   'min_dezenas': 5,  'max_dezenas': 15, 'num_bolas_sorteadas': 5,  'default_dezenas': 5},
    'lotofacil':  {'min_num': 1, 'max_num': 25,   'min_dezenas': 15, 'max_dezenas': 20, 'num_bolas_sorteadas': 15, 'default_dezenas': 15},
    'diadesorte': {'min_num': 1, 'max_num': 31,   'min_dezenas': 7,  'max_dezenas': 15, 'num_bolas_sorteadas': 7,  'default_dezenas': 7},
    'duplasena':  {'min_num': 1, 'max_num': 50,   'min_dezenas': 6,  'max_dezenas': 15, 'num_bolas_sorteadas': 6,  'default_dezenas': 6},
    'lotomania':  {'min_num': 1, 'max_num': 100,  'min_dezenas': 50, 'max_dezenas': 50, 'num_bolas_sorteadas': 20, 'default_dezenas': 50},
    'timemania':  {'min_num': 1, 'max_num': 80,   'min_dezenas': 10, 'max_dezenas': 10, 'num_bolas_sorteadas': 7,  'default_dezenas': 10},
    'supersete':  {'min_num': 0, 'max_num': 9,    'min_dezenas': 7,  'max_dezenas': 7,  'num_bolas_sorteadas': 7,  'default_dezenas': 7}
}

CONCURSOS_RECENTES = 100

# --- Funções de Banco de Dados e Lógica ---
def get_db_connection():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
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
    if not ancora_str or not re.match(r'^\d+$', ancora_str.strip()): return []
    config = LOTTERY_CONFIG[loteria]
    try:
        num = int(ancora_str)
        if config['min_num'] <= num <= config['max_num']: return [num]
        else: return []
    except (ValueError, TypeError): return []

# --- FUNÇÕES DAS ESTRATÉGIAS DE GERAÇÃO ---

def gerar_jogo_monte_carlo(loteria='megasena', numeros_ancora=[]):
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        dezenas_a_gerar = config['num_bolas_sorteadas'] - len(numeros_ancora)
        if dezenas_a_gerar <= 0: return " ".join(f"{num:02}" for num in sorted(numeros_ancora))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        resultados = cur.fetchall()
        cur.close()
        if not resultados: raise ValueError(f"O banco de dados está vazio para a simulação de {loteria}.")
        
        todos_os_numeros = [int(n) for linha in resultados for n in linha[0].split() if int(n) not in numeros_ancora]
        frequencia_historica = Counter(todos_os_numeros)
        numeros_possiveis, pesos_historicos = list(frequencia_historica.keys()), list(frequencia_historica.values())
        
        resultados_simulacao = Counter()
        for _ in range(100000):
            sorteio_simulado = random.choices(numeros_possiveis, weights=pesos_historicos, k=dezenas_a_gerar)
            resultados_simulacao.update(sorteio_simulado)
        
        numeros_da_simulacao, pesos_da_simulacao = list(resultados_simulacao.keys()), list(resultados_simulacao.values())
        numeros_novos = set()
        while len(numeros_novos) < dezenas_a_gerar:
            numeros_novos.add(random.choices(numeros_da_simulacao, weights=pesos_da_simulacao, k=1)[0])
        
        jogo_final = sorted(list(numeros_novos.union(set(numeros_ancora))))
        return " ".join(f"{num:02}" for num in jogo_final)
    finally:
        if conn: conn.close()

def _analisar_perfil_historico(loteria, resultados):
    config = LOTTERY_CONFIG[loteria]
    somas, paridades, distribuicoes_quadrantes = [], [], []
    
    universo_max = config['max_num']
    limite_q1, limite_q2, limite_q3 = math.ceil(universo_max / 4), math.ceil(universo_max / 4) * 2, math.ceil(universo_max / 4) * 3

    for linha in resultados:
        dezenas = [int(n) for n in linha[0].split()]

        if loteria == 'duplasena':
            dezenas = dezenas[:config['num_bolas_sorteadas']]

        num_dezenas_sorteadas_neste_concurso = len(dezenas)
        
        if num_dezenas_sorteadas_neste_concurso == 0: continue
        
        somas.append(sum(dezenas))
        num_pares = sum(1 for d in dezenas if d % 2 == 0)
        paridades.append((num_pares, num_dezenas_sorteadas_neste_concurso - num_pares))
        
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
    num_dezenas_no_jogo = len(dezenas)

    if perfil["soma_ideal"][0] <= sum(dezenas) <= perfil["soma_ideal"][1]: score += 1
    
    num_pares = sum(1 for d in dezenas if d % 2 == 0)
    if (num_pares, num_dezenas_no_jogo - num_pares) in perfil["paridade_ideal"]: score += 1
    
    universo_max = config['max_num']
    limite_q1, limite_q2, limite_q3 = math.ceil(universo_max / 4), math.ceil(universo_max / 4) * 2, math.ceil(universo_max / 4) * 3
    
    quadrantes = {1 if d <= limite_q1 else 2 if d <= limite_q2 else 3 if d <= limite_q3 else 4 for d in dezenas}
    if len(quadrantes) >= perfil["quadrantes_ideal"]: score += 1
    return score

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
        if not resultados: 
            return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)
        
        todos_os_numeros_sorteados = []
        for linha in resultados:
            dezenas_do_concurso = [int(n) for n in linha[0].split()]
            
            if loteria == 'duplasena':
                dezenas_do_concurso = dezenas_do_concurso[:config['num_bolas_sorteadas']]
            
            todos_os_numeros_sorteados.extend(dezenas_do_concurso)
        
        frequencia = Counter(n for n in todos_os_numeros_sorteados if n not in numeros_ancora)
        
        universo_disponivel = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
        
        jogos_gerados = set()
        
        while len(jogos_gerados) < count:
            numeros_novos = set()
            
            if estrategia == 'frias':
                numeros_com_frequencia = set(frequencia.keys())
                numeros_totalmente_frios = [n for n in universo_disponivel if n not in numeros_com_frequencia]
                
                if len(numeros_totalmente_frios) < dezenas_a_gerar:
                    frequencia_ordenada = sorted(frequencia.items(), key=lambda item: item[1])
                    for num, _ in frequencia_ordenada:
                        if num not in numeros_totalmente_frios and num not in numeros_ancora:
                            numeros_totalmente_frios.append(num)
                            if len(numeros_totalmente_frios) >= dezenas_a_gerar:
                                break
                
                k_frias = min(dezenas_a_gerar, len(numeros_totalmente_frios))
                if k_frias > 0:
                    numeros_novos.update(random.sample(numeros_totalmente_frios, k_frias))
                
                while len(numeros_novos) < dezenas_a_gerar:
                    num_extra = random.choice(universo_disponivel)
                    numeros_novos.add(num_extra)
            
            elif estrategia == 'mistas':
                numeros_quentes = list(frequencia.keys())
                pesos_quentes = [frequencia[n] for n in numeros_quentes]
                
                numeros_totalmente_frios = [n for n in universo_disponivel if n not in frequencia]
                if len(numeros_totalmente_frios) < dezenas_a_gerar:
                    frequencia_ordenada = sorted(frequencia.items(), key=lambda item: item[1])
                    for num, _ in frequencia_ordenada:
                        if num not in numeros_totalmente_frios and num not in numeros_ancora:
                            numeros_totalmente_frios.append(num)
                            if len(numeros_totalmente_frios) >= dezenas_a_gerar:
                                break
                numeros_frios_disponiveis = list(set(numeros_totalmente_frios))

                if not numeros_quentes and not numeros_frios_disponiveis:
                    return gerar_jogos_puramente_aleatorios(loteria, count, dezenas, numeros_ancora)

                num_a_gerar_quentes = math.ceil(dezenas_a_gerar / 2)
                num_a_gerar_frios = math.floor(dezenas_a_gerar / 2)

                if numeros_quentes:
                    dezenas_quentes_selecionadas = set()
                    k_quentes = min(num_a_gerar_quentes, len(numeros_quentes))
                    while len(dezenas_quentes_selecionadas) < k_quentes:
                        dezena = random.choices(numeros_quentes, weights=pesos_quentes, k=1)[0]
                        dezenas_quentes_selecionadas.add(dezena)
                    numeros_novos.update(dezenas_quentes_selecionadas)

                if numeros_frios_disponiveis:
                    dezenas_frias_selecionadas = set(random.sample(numeros_frios_disponiveis, min(num_a_gerar_frios, len(numeros_frios_disponiveis))))
                    numeros_novos.update(dezenas_frias_selecionadas)
                
                while len(numeros_novos) < dezenas_a_gerar:
                    num_extra = random.choice(universo_disponivel)
                    numeros_novos.add(num_extra)

            else:
                pesos_completos = [frequencia.get(n, 1) for n in universo_disponivel]

                if dezenas_a_gerar > len(universo_disponivel):
                    break
                
                while len(numeros_novos) < dezenas_a_gerar:
                    num_sorteado = random.choices(universo_disponivel, weights=pesos_completos, k=1)[0]
                    numeros_novos.add(num_sorteado)

            jogo_completo = frozenset(numeros_novos.union(set(numeros_ancora)))
            if len(jogo_completo) == dezenas: 
                jogos_gerados.add(jogo_completo)
                
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
    today = date.today().isoformat()
    return render_template('index.html', current_date=today)

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
       
@app.route('/get-games/<int:count>')
def get_games(count):
    loteria = request.args.get('loteria', 'megasena', type=str)
    estrategia = request.args.get('estrategia', 'geral', type=str)
    dezenas = request.args.get('dezenas', type=int)
    if dezenas is None: dezenas = LOTTERY_CONFIG[loteria]['default_dezenas']
    ancora_str = request.args.get('ancora', '', type=str)
    numeros_ancora = validar_e_sanitizar_ancora(ancora_str, loteria)
    
    if dezenas < len(numeros_ancora): dezenas = len(numeros_ancora)
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
        if choice not in ['sim', 'nao']: return jsonify({"error": "Escolha inválida"}), 400
        
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
        
        if loteria == 'duplasena':
            cur.execute(f"""
                SELECT numero::integer, COUNT(*) FROM (
                    SELECT (string_to_array(dezenas, ' '))[i]::integer as numero 
                    FROM resultados_sorteados 
                    CROSS JOIN generate_series(1, {config['num_bolas_sorteadas']}) as i
                    WHERE tipo_loteria = %s
                ) as numeros_individuais 
                GROUP BY numero ORDER BY numero::integer ASC;
            """, (loteria,))
        else:
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
            numeros_completos = [int(n) for n in sorteio_tuple[0].split()]
            
            if loteria == 'duplasena':
                numeros = numeros_completos[:config['num_bolas_sorteadas']]
            else:
                numeros = numeros_completos
            
            if len(numeros) >= config['num_bolas_sorteadas']:
                primos_no_sorteio = sum(1 for n in numeros if is_prime(n))
                pares_no_sorteio = sum(1 for n in numeros if n % 2 == 0)
                contagem_primos.update([primos_no_sorteio])
                contagem_pares.update([pares_no_sorteio])

        cur.close()
        return jsonify({
            "ultimo_concurso": ultimo_concurso,
            "frequencia": frequencia_numeros,
            "stats_primos": dict(contagem_primos),
            "stats_pares": dict(contagem_pares)
        })
    except Exception as e:
        print(f"Erro em get_stats para {loteria}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/get-ultimos-resultados')
def get_ultimos_resultados():
    loteria = request.args.get('loteria', 'megasena', type=str)
    limite = request.args.get('limite', 20, type=int)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT concurso, data_sorteio, dezenas, ganhadores, acumulou, mes_sorte, 
                   valor_acumulado, trevos, time_coracao, valor_proximo_concurso
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC 
            LIMIT %s;
        """, (loteria, limite))
        
        resultados = []
        for row in cur.fetchall():
            data_formatada = row[1].strftime('%d/%m/%Y') if isinstance(row[1], date) else row[1]
            
            dezenas_formatadas = row[2]
            
            valor_premio = None
            if row[9] is not None:
                valor_premio = float(row[9])
            elif row[6] is not None:
                valor_premio = float(row[6])
            
            resultados.append({
                "concurso": row[0],
                "data": data_formatada,
                "dezenas": dezenas_formatadas,
                "ganhadores": row[3],
                "acumulou": row[4],
                "mes_sorte": row[5],
                "valor_acumulado": valor_premio,
                "trevos": row[7] if row[7] else None,
                "time_coracao": row[8] if row[8] else None
            })
            
        cur.close()
        return jsonify(resultados)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/get-stats-recentes')
def get_stats_recentes():
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if loteria == 'duplasena':
            cur.execute(f"""
                SELECT numero::integer, COUNT(*) FROM (
                    SELECT (string_to_array(dezenas, ' '))[i]::integer as numero 
                    FROM resultados_sorteados 
                    CROSS JOIN generate_series(1, {config['num_bolas_sorteadas']}) as i
                    WHERE tipo_loteria = %s ORDER BY concurso DESC LIMIT %s
                ) as numeros_individuais 
                GROUP BY numero ORDER BY numero::integer ASC;
            """, (loteria, CONCURSOS_RECENTES))
        else:
            cur.execute("""
                SELECT numero::integer, COUNT(*) FROM (
                    SELECT unnest(string_to_array(dezenas, ' ')) as numero FROM resultados_sorteados 
                    WHERE tipo_loteria = %s ORDER BY concurso DESC LIMIT %s
                ) as numeros_individuais GROUP BY numero ORDER BY numero::integer ASC;
            """, (loteria, CONCURSOS_RECENTES))
            
        frequencia_numeros_recentes = [{"numero": n, "frequencia": f} for n, f in cur.fetchall()]
        cur.close()
        return jsonify({"frequencia_recente": frequencia_numeros_recentes})
    except Exception as e:
        print(f"Erro em get_stats_recentes para {loteria}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/ads.txt')
def ads():
    return send_from_directory('.', 'ads.txt')

@app.route('/simulador')
def simulador():
    return render_template('simulador.html')

@app.route('/get-todos-resultados')
def get_todos_resultados():
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT concurso, data_sorteio, dezenas, ganhadores, acumulou, mes_sorte, 
                   valor_acumulado, trevos, time_coracao, valor_proximo_concurso
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC;
        """, (loteria,))
        
        resultados = []
        for row in cur.fetchall():
            data_formatada = row[1].strftime('%d/%m/%Y') if isinstance(row[1], date) else row[1]
            
            valor_premio = None
            if row[9] is not None:
                valor_premio = float(row[9])
            elif row[6] is not None:
                valor_premio = float(row[6])
            
            resultados.append({
                "concurso": row[0],
                "data": data_formatada,
                "dezenas": row[2],
                "ganhadores": row[3],
                "acumulou": row[4],
                "mes_sorte": row[5],
                "valor_acumulado": valor_premio,
                "trevos": row[7] if row[7] else None,
                "time_coracao": row[8] if row[8] else None
            })
            
        cur.close()
        return jsonify(resultados)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/landing')
def promocional():
    return render_template('landing.html')    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('RENDER') is None
    app.run(host='0.0.0.0', port=port, debug=debug_mode)