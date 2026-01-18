# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template, send_from_directory
import random
import os

# --- Inicialização e Configuração ---
app = Flask(__name__)

# Configuração completa das loterias (Sync com o Frontend)
LOTTERY_CONFIG = {
    'maismilionaria': {
        'nome': '+Milionária',
        'min_num': 1, 'max_num': 50,
        'min_dezenas': 6, 'max_dezenas': 12,
        'num_bolas_sorteadas': 6,
        'default_dezenas': 6,
        'num_trevos_sorteados': 2,
        'min_trevo': 1, 'max_trevo': 6
    },
    'megasena': {
        'nome': 'Mega-Sena',
        'min_num': 1, 'max_num': 60,
        'min_dezenas': 6, 'max_dezenas': 20,
        'num_bolas_sorteadas': 6,
        'default_dezenas': 6
    },
    'quina': {
        'nome': 'Quina',
        'min_num': 1, 'max_num': 80,
        'min_dezenas': 5, 'max_dezenas': 15,
        'num_bolas_sorteadas': 5,
        'default_dezenas': 5
    },
    'lotofacil': {
        'nome': 'Lotofácil',
        'min_num': 1, 'max_num': 25,
        'min_dezenas': 15, 'max_dezenas': 20,
        'num_bolas_sorteadas': 15,
        'default_dezenas': 15
    },
    'diadesorte': {
        'nome': 'Dia de Sorte',
        'min_num': 1, 'max_num': 31,
        'min_dezenas': 7, 'max_dezenas': 15,
        'num_bolas_sorteadas': 7,
        'default_dezenas': 7
    },
    'duplasena': {
        'nome': 'Dupla Sena',
        'min_num': 1, 'max_num': 50,
        'min_dezenas': 6, 'max_dezenas': 15,
        'num_bolas_sorteadas': 6,
        'default_dezenas': 6
    },
    'lotomania': {
        'nome': 'Lotomania',
        'min_num': 1, 'max_num': 100,
        'min_dezenas': 50, 'max_dezenas': 50,
        'num_bolas_sorteadas': 20,
        'default_dezenas': 50
    },
    'timemania': {
        'nome': 'Timemania',
        'min_num': 1, 'max_num': 80,
        'min_dezenas': 10, 'max_dezenas': 10,
        'num_bolas_sorteadas': 7,
        'default_dezenas': 10
    },
    'supersete': {
        'nome': 'Super Sete',
        'min_num': 0, 'max_num': 9,
        'min_dezenas': 7, 'max_dezenas': 7,
        'num_bolas_sorteadas': 7,
        'default_dezenas': 7
    }
}

# --- Funções Auxiliares de Lógica ---

def validar_ancora(ancora_str, loteria):
    """Valida se o número âncora pertence ao intervalo da loteria"""
    if not ancora_str or not ancora_str.strip().isdigit():
        return []
    config = LOTTERY_CONFIG.get(loteria)
    if not config: return []
    try:
        num = int(ancora_str)
        if config['min_num'] <= num <= config['max_num']:
            return [num]
    except: pass
    return []

def gerar_jogos_aleatorios(loteria, count, dezenas, numeros_ancora=[]):
    """Gera combinações únicas baseadas na configuração"""
    config = LOTTERY_CONFIG[loteria]
    dezenas_a_gerar = dezenas - len(numeros_ancora)
    
    universo = [n for n in range(config['min_num'], config['max_num'] + 1) if n not in numeros_ancora]
    
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros_novos = random.sample(universo, dezenas_a_gerar)
        jogo_completo = sorted(numeros_novos + numeros_ancora)
        jogo_formatado = " ".join(f"{num:02}" for num in jogo_completo)
        jogos_gerados.add(jogo_formatado)
    
    return list(jogos_gerados)

def gerar_dados_simulados(loteria):
    """Gera estatísticas e resultados simulados para a interface visual"""
    config = LOTTERY_CONFIG[loteria]
    frequencia = [{"numero": i, "frequencia": random.randint(10, 50)} for i in random.sample(range(config['min_num'], config['max_num']+1), 6)]
    
    resultados = []
    for i in range(5):
        dezenas = sorted(random.sample(range(config['min_num'], config['max_num']+1), config['num_bolas_sorteadas']))
        resultados.append({
            "concurso": 3000 - i,
            "data": f"{20-i}/01/2026",
            "dezenas": " ".join(f"{num:02}" for num in dezenas),
            "acumulou": random.choice([True, False]),
            "valor_acumulado": random.randint(2000000, 50000000)
        })
    return {"frequencia": frequencia, "resultados": resultados}

# --- Rotas de Páginas ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

# --- Endpoints da API ---

@app.route('/get-games/<int:count>')
def get_games(count):
    try:
        loteria = request.args.get('loteria', 'megasena')
        dezenas = request.args.get('dezenas', type=int)
        ancora_str = request.args.get('ancora', '')

        if loteria not in LOTTERY_CONFIG:
            return jsonify({"error": "Loteria inválida"}), 400
        
        config = LOTTERY_CONFIG[loteria]
        if dezenas is None: dezenas = config['default_dezenas']
        
        numeros_ancora = validar_ancora(ancora_str, loteria)
        jogos = gerar_jogos_aleatorios(loteria, min(count, 10), dezenas, numeros_ancora)
        
        return jsonify(jogos)
    except Exception as e:
        return jsonify({"error": "Falha ao gerar jogos"}), 500

@app.route('/organizar-jogos', methods=['POST'])
def organizar_jogos():
    try:
        data = request.get_json()
        loteria = data.get('loteria', 'megasena')
        numeros = data.get('numeros', [])
        quantidade = min(data.get('quantidade', 10), 1000)
        
        if loteria not in LOTTERY_CONFIG or len(numeros) < LOTTERY_CONFIG[loteria]['num_bolas_sorteadas']:
            return jsonify({"error": "Dados insuficientes"}), 400
        
        config = LOTTERY_CONFIG[loteria]
        jogos = []
        for _ in range(quantidade):
            jogo = sorted(random.sample(numeros, config['num_bolas_sorteadas']))
            jogos.append(" ".join(f"{n:02}" for n in jogo))
            
        return jsonify({"jogos": jogos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-stats')
@app.route('/get-ultimos-resultados')
def api_stats():
    loteria = request.args.get('loteria', 'megasena')
    if loteria not in LOTTERY_CONFIG: return jsonify({"error": "Inválido"}), 400
    return jsonify(gerar_dados_simulados(loteria))

@app.route('/get-monte-carlo-game')
def monte_carlo():
    loteria = request.args.get('loteria', 'megasena')
    jogos = gerar_jogos_aleatorios(loteria, 1, LOTTERY_CONFIG[loteria]['num_bolas_sorteadas'])
    return jsonify({"jogo": jogos[0]})

@app.route('/get-lottery-config')
def get_lottery_config():
    return jsonify(LOTTERY_CONFIG)

@app.route('/submit-feedback', methods=['POST'])
def feedback():
    # Em produção, você poderia salvar isso em um banco ou log
    return jsonify({"success": True, "message": "Feedback recebido!"})

@app.route('/ads.txt')
def ads():
    return send_from_directory('.', 'ads.txt')

# --- Inicialização ---

if __name__ == '__main__':
    # Configuração automática para Render ou Local
    port = int(os.environ.get('PORT', 10000))
    # Debug True apenas se não estiver no ambiente de produção (Render)
    is_prod = os.environ.get('RENDER') is not None
    app.run(host='0.0.0.0', port=port, debug=not is_prod)