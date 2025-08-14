import psycopg2
import os
from flask import Flask, jsonify, request
import random
from collections import Counter

# --- CONFIGURAÇÃO ---
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- Aplicação Flask ---
app = Flask(__name__, static_folder='.', static_url_path='')


# --- LÓGICA DE GERAÇÃO DE JOGOS (MÉTODO 1: COM FILTRO) ---
def gerar_jogos_com_base_na_frequencia(count):
    """
    Gera jogos com base na frequência dos números sorteados anteriormente.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados;")
        resultados = cur.fetchall()
        if not resultados:
            raise ValueError("O banco de dados está vazio. Execute o script 'importador.py' primeiro.")
        
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
            while len(jogo_atual) < 6:
                numero_sorteado = random.choices(numeros_possiveis, weights=pesos, k=1)[0]
                jogo_atual.add(numero_sorteado)
            
            jogo_formatado = " ".join(f"{num:02}" for num in sorted(list(jogo_atual)))
            jogos_gerados.add(jogo_formatado)
            tentativas += 1
            
        return list(jogos_gerados)
    finally:
        if conn:
            conn.close()

# --- LÓGICA DE GERAÇÃO DE JOGOS (MÉTODO 2: PURO ALEATÓRIO) ---
def gerar_jogos_puramente_aleatorios(count):
    """
    Gera jogos de forma 100% aleatória, sem usar o banco de dados.
    """
    jogos_gerados = set()
    while len(jogos_gerados) < count:
        numeros = random.sample(range(1, 61), 6)
        jogo_formatado = " ".join(f"{num:02}" for num in sorted(numeros))
        jogos_gerados.add(jogo_formatado)
    return list(jogos_gerados)


# --- ROTAS DA APLICAÇÃO ---

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-games/<int:count>')
def get_games(count):
    """
    Rota principal que gera os jogos.
    Verifica o parâmetro 'filtro' na URL para decidir qual método usar.
    """
    try:
        usar_filtro = request.args.get('filtro', 'true', type=str).lower() == 'true'

        if usar_filtro:
            print("INFO: Gerando jogos com filtro de frequência.")
            jogos = gerar_jogos_com_base_na_frequencia(count)
        else:
            print("INFO: Gerando jogos puramente aleatórios (sem filtro).")
            jogos = gerar_jogos_puramente_aleatorios(count)
        
        return jsonify(jogos)
    except Exception as e:
        print(f"ERRO: Erro ao buscar jogos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status_do_banco():
    """ Rota para verificar a saúde e o conteúdo do banco de dados. """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM resultados_sorteados;")
        total_rows = cur.fetchone()[0]
        return jsonify({"status": "conectado", "total_de_concursos_no_bd": total_rows})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

@app.route('/get-stats')
def get_stats():
    """ Rota para buscar estatísticas do banco de dados. """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 1. Obter o número do último concurso
        cur.execute("SELECT MAX(concurso) FROM resultados_sorteados;")
        ultimo_concurso_result = cur.fetchone()
        ultimo_concurso = ultimo_concurso_result[0] if ultimo_concurso_result else 0

        # 2. Obter a frequência de todos os números
        cur.execute("""
            SELECT numero::integer, COUNT(*) as frequencia
            FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero
                FROM resultados_sorteados
            ) as numeros_individuais
            GROUP BY numero
            ORDER BY frequencia DESC;
        """)
        frequencia_numeros = cur.fetchall()
        
        # Formata os dados para o frontend
        stats_data = [{"numero": n, "frequencia": f} for n, f in frequencia_numeros]

        return jsonify({
            "ultimo_concurso": ultimo_concurso,
            "frequencia": stats_data
        })
    except Exception as e:
        print(f"ERRO: Erro ao buscar estatísticas: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()