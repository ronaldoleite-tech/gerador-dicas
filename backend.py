# -*- coding: utf-8 -*-
"""
Backend Flask para o aplicativo Sorte Analisada.
Este servidor fornece endpoints de API para:
- Servir a página principal (index.html).
- Gerar jogos de loteria (aleatórios ou baseados em frequência).
- Gerar um jogo especial usando a simulação de Monte Carlo.
- Fornecer dados estatísticos sobre sorteios passados.
"""

# --- Importações de Bibliotecas ---
import psycopg2  # Adaptador de banco de dados PostgreSQL para Python
import os        # Para acessar variáveis de ambiente (como a URL do banco de dados)
from flask import Flask, jsonify, request  # Framework web para criar a API
import random    # Para geração de números aleatórios
from collections import Counter # Para contar a frequência de números
from dotenv import load_dotenv  # Para carregar variáveis de ambiente de um arquivo .env localmente
import math      # Para a função de raiz quadrada no cálculo de números primos

# --- Inicialização e Configuração ---

# Carrega as variáveis de ambiente do arquivo .env (essencial para desenvolvimento local)
load_dotenv()

# Pega a URL de conexão do banco de dados a partir das variáveis de ambiente
DATABASE_URL = os.environ.get('DATABASE_URL')

# Inicializa a aplicação Flask
# static_folder='.' e static_url_path='' fazem com que o servidor sirva arquivos do diretório raiz
app = Flask(__name__, static_folder='.', static_url_path='')

# Configuração central com as regras para cada loteria.
# Isso evita "números mágicos" e facilita a adição de novas loterias no futuro.
LOTTERY_CONFIG = {
    'megasena': {'min_num': 1, 'max_num': 60, 'num_bolas_sorteadas': 6, 'default_dezenas': 6},
    'quina':    {'min_num': 1, 'max_num': 80, 'num_bolas_sorteadas': 5, 'default_dezenas': 5},
    'lotofacil':{'min_num': 1, 'max_num': 25, 'num_bolas_sorteadas': 15, 'default_dezenas': 15}
}

# --- Funções Auxiliares e de Lógica ---

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def is_prime(n):
    """Verifica se um número é primo. Otimizado para performance."""
    if n < 2: return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0: return False
    return True

# >>> INÍCIO DA SEÇÃO MODIFICADA <<<
def gerar_jogo_monte_carlo(loteria='megasena'):
    """
    Gera um jogo único usando a simulação de Monte Carlo.
    A lógica simula milhares de sorteios baseados na frequência histórica dos números.
    O resultado da simulação é então usado como um novo conjunto de pesos para
    sortear um jogo final, garantindo variedade a cada execução.
    
    Args:
        loteria (str): O tipo de loteria para a simulação.
        
    Returns:
        str: Uma string com os números do jogo gerado, formatados e ordenados.
    """
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
            # A simulação continua a mesma, com reposição para ser mais rápida
            sorteio_simulado = random.choices(numeros_possiveis, weights=pesos_historicos, k=config['num_bolas_sorteadas'])
            resultados_simulacao.update(sorteio_simulado)
        
        # --- ALTERAÇÃO PRINCIPAL AQUI ---
        # Em vez de pegar os mais comuns, usamos o resultado da simulação como novos pesos.
        
        # 1. Prepara os novos dados para o sorteio final
        numeros_da_simulacao = list(resultados_simulacao.keys())
        pesos_da_simulacao = list(resultados_simulacao.values())
        
        # 2. Gera um jogo único e sem repetição usando os novos pesos
        numeros_do_jogo = set()
        # Usamos um loop para garantir que o jogo tenha o número de dezenas correto,
        # já que random.choices pode retornar números repetidos.
        while len(numeros_do_jogo) < config['num_bolas_sorteadas']:
            # Sorteia um número de cada vez para evitar repetições
            numero_sorteado = random.choices(numeros_da_simulacao, weights=pesos_da_simulacao, k=1)[0]
            numeros_do_jogo.add(numero_sorteado)
            
        return " ".join(f"{num:02}" for num in sorted(list(numeros_do_jogo)))
    
    finally:
        if conn: conn.close()
# >>> FIM DA SEÇÃO MODIFICADA <<<

def gerar_jogos_com_base_na_frequencia(loteria, count, dezenas):
    """
    Gera uma quantidade de jogos únicos baseados na frequência histórica dos números.
    Números que saíram mais vezes no passado têm mais chance de serem escolhidos.
    
    Args:
        loteria (str): O tipo de loteria.
        count (int): Quantos jogos gerar.
        dezenas (int): Quantas dezenas por jogo.
        
    Returns:
        list: Uma lista de strings, onde cada string é um jogo formatado.
    """
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
        # Loop para garantir que jogos duplicados não sejam retornados
        while len(jogos_gerados) < count:
            jogo_atual = frozenset(random.choices(numeros_possiveis, weights=pesos, k=dezenas))
            if len(jogo_atual) == dezenas:
                jogos_gerados.add(jogo_atual)
            
        return [" ".join(f"{num:02}" for num in sorted(list(jogo))) for jogo in jogos_gerados]
    finally:
        if conn: conn.close()

def gerar_jogos_puramente_aleatorios(loteria, count, dezenas):
    """
    Gera jogos de forma 100% aleatória (surpresinha), ignorando o histórico.
    
    Args:
        loteria (str): O tipo de loteria.
        count (int): Quantos jogos gerar.
        dezenas (int): Quantas dezenas por jogo.
        
    Returns:
        list: Uma lista de strings, onde cada string é um jogo formatado.
    """
    config = LOTTERY_CONFIG[loteria]
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros = random.sample(range(config['min_num'], config['max_num'] + 1), dezenas)
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros))
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)

# --- Endpoints da API (Rotas Flask) ---

@app.route('/')
def index():
    """Endpoint principal. Serve o arquivo estático 'index.html'."""
    return app.send_static_file('index.html')

@app.route('/get-monte-carlo-game')
def get_monte_carlo_game():
    """Endpoint para obter um único jogo gerado pela simulação de Monte Carlo."""
    loteria = request.args.get('loteria', 'megasena', type=str)
    try:
        jogo = gerar_jogo_monte_carlo(loteria)
        return jsonify({"jogo": jogo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Retorna erro 500 em caso de falha

@app.route('/get-games/<int:count>')
def get_games(count):
    """Endpoint para gerar múltiplos jogos, com ou sem filtro de frequência."""
    # Captura os parâmetros da URL (ex: ?loteria=quina&filtro=true&dezenas=7)
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
    """
    Endpoint para obter dados estatísticos completos de uma loteria.
    Retorna o último concurso, a frequência de cada número, a contagem de primos por sorteio
    e a contagem de pares/ímpares por sorteio.
    """
    loteria = request.args.get('loteria', 'megasena', type=str)
    conn = None
    try:
        config = LOTTERY_CONFIG[loteria]
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Busca o número do último concurso registrado
        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        ultimo_concurso = cur.fetchone()[0] or 0
        
        # Query para contar a frequência de cada dezena
        cur.execute("""
            SELECT numero::integer, COUNT(*) FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero FROM resultados_sorteados WHERE tipo_loteria = %s
            ) as numeros_individuais GROUP BY numero ORDER BY numero::integer ASC;
        """, (loteria,))
        frequencia_numeros = [{"numero": n, "frequencia": f} for n, f in cur.fetchall()]

        # Busca todos os sorteios para calcular estatísticas de primos e pares
        cur.execute("SELECT dezenas FROM resultados_sorteados WHERE tipo_loteria = %s;", (loteria,))
        todos_sorteios = cur.fetchall()
        
        contagem_primos = Counter()
        contagem_pares = Counter()
        
        for sorteio_tuple in todos_sorteios:
            numeros = [int(n) for n in sorteio_tuple[0].split()]
            if len(numeros) == config['num_bolas_sorteadas']: # Processa apenas sorteios com o número correto de bolas
                primos_no_sorteio = sum(1 for n in numeros if is_prime(n))
                pares_no_sorteio = sum(1 for n in numeros if n % 2 == 0)
                contagem_primos.update([primos_no_sorteio])
                contagem_pares.update([pares_no_sorteio])
        
        # Retorna todos os dados em um único objeto JSON
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

# --- Bloco de Execução Principal ---

if __name__ == '__main__':
    """
    Este bloco só é executado quando o script é rodado diretamente (e não quando é importado).
    É usado para iniciar o servidor de desenvolvimento do Flask.
    Em produção (como na Render), um servidor WSGI como o Gunicorn é usado para rodar a 'app'.
    """
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)