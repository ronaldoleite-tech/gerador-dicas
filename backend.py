import psycopg2
import os
from flask import Flask, jsonify
import random
from collections import Counter

# --- CONFIGURAÇÃO ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# O nome do arquivo foi atualizado para o correto.
FILE_PATH_PARA_IMPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sorteados.txt')
BATCH_SIZE = 500

# --- Aplicação Flask ---
app = Flask(__name__, static_folder='.', static_url_path='')

# --- FUNÇÃO AUXILIAR PARA A LÓGICA DE GERAÇÃO ---
def gerar_jogos_com_base_na_frequencia(count):
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT dezenas FROM resultados_sorteados;")
        resultados = cur.fetchall()

        if not resultados:
            raise ValueError("O banco de dados de resultados está vazio. Execute a importação primeiro.")

        todos_os_numeros = []
        for linha in resultados:
            numeros_da_linha = [int(n) for n in linha[0].split()]
            todos_os_numeros.extend(numeros_da_linha)
        
        frequencia = Counter(todos_os_numeros)
        numeros_possiveis = list(frequencia.keys())
        pesos = list(frequencia.values())
        
        jogos_gerados = set()
        max_tentativas = count * 10
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

# --- ROTA DE IMPORTAÇÃO (PARA PREPARAR O BANCO DE DADOS) ---
@app.route('/importar-dados-agora')
def rota_de_importacao():
    print("ROTA DE IMPORTAÇÃO DE RESULTADOS ACIONADA!")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Conectado ao DB para importação.")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
                id SERIAL PRIMARY KEY,
                dezenas TEXT NOT NULL UNIQUE
            );
        """)
        print("Tabela 'resultados_sorteados' verificada/criada.")
        
        # A LINHA TRUNCATE FOI REMOVIDA DAQUI!
        # Agora o script apenas adicionará novos resultados que não existem no BD.
        
        batch = []
        total_inserted = 0
        with open(FILE_PATH_PARA_IMPORTAR, 'r', encoding='utf-8') as f:
            next(f) 

            for line in f:
                numeros = line.strip().split() 
                if len(numeros) == 6:
                    linha_formatada = " ".join(sorted(numeros, key=int))
                    batch.append((linha_formatada,))
                
                if len(batch) >= BATCH_SIZE:
                    insert_query = "INSERT INTO resultados_sorteados (dezenas) VALUES (%s) ON CONFLICT (dezenas) DO NOTHING"
                    cur.executemany(insert_query, batch)
                    novos_registros = cur.rowcount if cur.rowcount is not None else 0
                    total_inserted += novos_registros
                    conn.commit()
                    print(f"  -> Lote processado. {novos_registros} novos concursos adicionados.")
                    batch = []

        if batch:
            insert_query = "INSERT INTO resultados_sorteados (dezenas) VALUES (%s) ON CONFLICT (dezenas) DO NOTHING"
            cur.executemany(insert_query, batch)
            novos_registros = cur.rowcount if cur.rowcount is not None else 0
            total_inserted += novos_registros
            conn.commit()

        return f"<h1>Importação Concluída!</h1><p><b>{total_inserted}</b> novos concursos foram adicionados ao banco de dados.</p>"
    except Exception as e:
        print(f"ERRO NA IMPORTAÇÃO: {e}")
        return f"<h1>Erro durante a importação:</h1><p>{e}</p>", 500
    finally:
        if conn:
            conn.close()
            print("Conexão de importação fechada.")


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-games/<int:count>')
def get_games(count):
    try:
        jogos = gerar_jogos_com_base_na_frequencia(count)
        return jsonify(jogos)
    except Exception as e:
        print(f"Erro ao buscar jogos: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/status')
def status_do_banco():
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))