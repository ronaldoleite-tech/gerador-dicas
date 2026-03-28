# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template, send_from_directory, redirect
import random
import os

# --- Inicialização e Configuração ---
app = Flask(__name__)

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

# --- Funções Auxiliares ---

def validar_ancora(ancora_str, loteria):
    """Valida e retorna número âncora se válido"""
    if not ancora_str or not ancora_str.strip().isdigit():
        return []
    
    config = LOTTERY_CONFIG[loteria]
    try:
        num = int(ancora_str)
        if config['min_num'] <= num <= config['max_num']:
            return [num]
    except (ValueError, TypeError):
        pass
    return []

def gerar_jogos_aleatorios(loteria, count, dezenas, numeros_ancora=[]):
    """Gera jogos completamente aleatórios"""
    # SUPER SETE – caso especial
    if loteria == 'supersete':
        jogos = []
        for _ in range(count):
            jogo = [random.randint(0, 9) for _ in range(7)]
            jogos.append(" ".join(str(n) for n in jogo))
        return jogos

    # --- DEMAIS LOTERIAS seguem lógica normal ---
    config = LOTTERY_CONFIG[loteria]
    dezenas_a_gerar = dezenas - len(numeros_ancora)

    if dezenas_a_gerar < 0:
        return []

    universo = [n for n in range(config['min_num'], config['max_num'] + 1)
                if n not in numeros_ancora]

    if dezenas_a_gerar > len(universo):
        return []

    jogos_gerados = set()
    tentativas = 0
    max_tentativas = count * 100

    while len(jogos_gerados) < count and tentativas < max_tentativas:
        tentativas += 1

        numeros_novos = random.sample(universo, dezenas_a_gerar)
        jogo_completo = sorted(numeros_novos + numeros_ancora)

        jogo_formatado = " ".join(f"{num:02}" for num in jogo_completo)
        jogos_gerados.add(jogo_formatado)

    return list(jogos_gerados)

def gerar_dados_exemplo_estatisticas(loteria):
    """Gera dados de exemplo para estatísticas"""
    config = LOTTERY_CONFIG[loteria]
    
    # Gera frequência de exemplo
    frequencia = []
    for i in range(config['min_num'], config['max_num'] + 1):
        if i % 3 == 0:  # Apenas alguns números para exemplo
            frequencia.append({
                "numero": i,
                "frequencia": random.randint(5, 20)
            })
    
    # Gera resultados recentes de exemplo
    resultados = []
    for i in range(5):
        # Gera dezenas aleatórias
        dezenas = random.sample(
            range(config['min_num'], config['max_num'] + 1),
            config['num_bolas_sorteadas']
        )
        dezenas.sort()
        
        resultados.append({
            "concurso": 2777 - i,
            "data": f"{15+i}/03/2025",
            "dezenas": " ".join(f"{num:02}" for num in dezenas),
            "ganhadores": random.randint(0, 3),
            "acumulou": random.choice([True, False]),
            "mes_sorte": "Março",
            "valor_acumulado": random.randint(1000000, 10000000) + 0.0
        })
    
    return {
        "frequencia": frequencia,
        "resultados": resultados,
        "ultimo_concurso": 2777,
        "stats_primos": {0: 5, 1: 10, 2: 15, 3: 8},
        "stats_pares": {2: 12, 3: 18, 4: 10}
    }

# --- Rotas de Páginas ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# --- Endpoints da API ---

@app.route('/get-games/<int:count>')
def get_games(count):
    """Endpoint principal para gerar jogos"""
    try:
        loteria = request.args.get('loteria', 'megasena', type=str)
        estrategia = request.args.get('estrategia', 'aleatorio', type=str)  # Para compatibilidade
        dezenas = request.args.get('dezenas', type=int)
        ancora_str = request.args.get('ancora', '', type=str)
        
        # Validações
        if loteria not in LOTTERY_CONFIG:
            return jsonify({"error": "Loteria inválida"}), 400
        
        config = LOTTERY_CONFIG[loteria]
        
        # Define dezenas padrão se não especificado
        if dezenas is None:
            dezenas = config['default_dezenas']
        
        # Valida número âncora
        numeros_ancora = validar_ancora(ancora_str, loteria)
        
        # Ajusta dezenas se necessário
        if dezenas < len(numeros_ancora):
            dezenas = len(numeros_ancora)
        
        # Valida limites
        if dezenas < config['min_dezenas'] or dezenas > config['max_dezenas']:
            return jsonify({
                "error": f"Número de dezenas deve estar entre {config['min_dezenas']} e {config['max_dezenas']}"
            }), 400
        
        if count < 1 or count > 10:
            return jsonify({"error": "Quantidade de jogos deve estar entre 1 e 10"}), 400
        
        # Gera os jogos (sempre aleatório na versão simplificada)
        jogos = gerar_jogos_aleatorios(loteria, count, dezenas, numeros_ancora)
        
        if not jogos:
            return jsonify({"error": "Não foi possível gerar os jogos"}), 500
        
        return jsonify(jogos)
        
    except Exception as e:
        print(f"Erro em get_games: {str(e)}")
        return jsonify({"error": "Erro ao gerar jogos"}), 500

@app.route('/get-lottery-config')
def get_lottery_config():
    """Retorna configuração das loterias para o frontend"""
    return jsonify(LOTTERY_CONFIG)

@app.route('/get-stats')
def get_stats():
    """Retorna estatísticas de exemplo"""
    loteria = request.args.get('loteria', 'megasena', type=str)
    
    if loteria not in LOTTERY_CONFIG:
        return jsonify({"error": "Loteria inválida"}), 400
    
    dados = gerar_dados_exemplo_estatisticas(loteria)
    return jsonify(dados)

@app.route('/get-ultimos-resultados')
def get_ultimos_resultados():
    """Retorna resultados recentes de exemplo"""
    loteria = request.args.get('loteria', 'megasena', type=str)
    limite = request.args.get('limite', 5, type=int)
    
    if loteria not in LOTTERY_CONFIG:
        return jsonify({"error": "Loteria inválida"}), 400
    
    dados = gerar_dados_exemplo_estatisticas(loteria)
    # Limita os resultados conforme solicitado
    resultados_limitados = dados['resultados'][:limite]
    
    return jsonify(resultados_limitados)

@app.route('/get-stats-recentes')
def get_stats_recentes():
    """Retorna estatísticas recentes de exemplo"""
    loteria = request.args.get('loteria', 'megasena', type=str)
    
    if loteria not in LOTTERY_CONFIG:
        return jsonify({"error": "Loteria inválida"}), 400
    
    # Para simplificar, retorna a mesma frequência
    dados = gerar_dados_exemplo_estatisticas(loteria)
    return jsonify({"frequencia_recente": dados['frequencia']})

@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    """Endpoint para geração Monte Carlo (simulado)"""
    loteria = request.args.get('loteria', 'megasena', type=str)
    ancora_str = request.args.get('ancora', '', type=str)

    # SUPER SETE É CASO ESPECIAL
    if loteria == 'supersete':
        # Gera 1 número por coluna (0 a 9), sem ordenar!
        jogo = [random.randint(0, 9) for _ in range(7)]
        jogo_formatado = " ".join(str(num) for num in jogo)
        return jsonify({"jogo": jogo_formatado})

    # --- DEMAIS LOTERIAS continuam igual ---
    numeros_ancora = validar_ancora(ancora_str, loteria)
    config = LOTTERY_CONFIG[loteria]

    dezenas_a_gerar = config['num_bolas_sorteadas'] - len(numeros_ancora)

    universo = [n for n in range(config['min_num'], config['max_num'] + 1)
                if n not in numeros_ancora]

    if dezenas_a_gerar <= 0:
        jogo = sorted(numeros_ancora)
    else:
        numeros_novos = random.sample(universo, dezenas_a_gerar)
        jogo = sorted(numeros_novos + numeros_ancora)

    jogo_formatado = " ".join(f"{num:02}" for num in jogo)
    return jsonify({"jogo": jogo_formatado})

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    """Endpoint para feedback (simulado localmente)"""
    try:
        data = request.get_json()
        choice = data.get('choice')
        
        if choice not in ['sim', 'nao']:
            return jsonify({"error": "Escolha inválida"}), 400
        
        print(f"[FEEDBACK] Usuário escolheu: {choice}")
        
        return jsonify({
            "success": True, 
            "message": "Feedback recebido com sucesso!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-todos-resultados')
def get_todos_resultados():
    """Retorna todos os resultados de exemplo"""
    loteria = request.args.get('loteria', 'megasena', type=str)
    
    if loteria not in LOTTERY_CONFIG:
        return jsonify({"error": "Loteria inválida"}), 400
    
    dados = gerar_dados_exemplo_estatisticas(loteria)
    return jsonify(dados['resultados'])

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    return app.send_static_file('.well-known/assetlinks.json')

@app.route('/simulador')
def simulador():
    return redirect('/', 301)  # 301 = redirecionamento permanente

@app.route('/organizar-jogos', methods=['POST'])
def organizar_jogos():
    """Endpoint para o organizador de jogos"""
    try:
        data = request.get_json()
        loteria = data.get('loteria', 'megasena')
        numeros = data.get('numeros', [])
        quantidade = data.get('quantidade', 10)
        
        if loteria not in LOTTERY_CONFIG:
            return jsonify({"error": "Loteria inválida"}), 400
        
        config = LOTTERY_CONFIG[loteria]
        
        # Simulação de organização
        jogos_organizados = []
        for i in range(min(quantidade, 100)):  # Limite de 100 jogos
            # Seleciona números aleatórios da lista fornecida
            jogo = random.sample(numeros, min(len(numeros), config['num_bolas_sorteadas']))
            jogo.sort()
            jogos_organizados.append(" ".join(f"{num:02}" for num in jogo))
        
        return jsonify({
            "jogos": jogos_organizados,
            "total_jogos": len(jogos_organizados),
            "loteria": loteria
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ads.txt')
def ads():
    return send_from_directory('.', 'ads.txt')

# --- Execução ---
if __name__ == '__main__':
    # Configuração automática para Render ou Local
    port = int(os.environ.get('PORT', 10000))
    # Debug True apenas se não estiver no ambiente de produção (Render)
    is_prod = os.environ.get('RENDER') is not None
    
    if not is_prod:
        print("=" * 60)
        print("SERVIDOR LOCAL INICIADO")
        print(f"Endereço: http://localhost:{port}")
        print("=" * 60)
        print("\nEndpoints disponíveis:")
        print("  • /                     - Página principal")
        print("  • /get-games/<count>    - Gerar jogos")
        print("  • /get-stats            - Estatísticas")
        print("  • /get-ultimos-resultados - Resultados recentes")
        print("  • /get-lottery-config   - Configurações das loterias")
        print("  • /get-monte-carlo-game - Geração Monte Carlo")
        print("  • /organizar-jogos      - Organizador de jogos")
        print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=not is_prod)