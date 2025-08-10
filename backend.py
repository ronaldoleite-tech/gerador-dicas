import psycopg2
import os
import time
from flask import Flask, jsonify
import random

# --- CONFIGURAÇÃO ---
DATABASE_URL = os.environ.get('DATABASE_URL')
FILE_PATH_PARA_IMPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testecombinaçoes_final.txt')
BATCH_SIZE = 10000

# --- Aplicação Flask ---
app = Flask(__name__, static_folder='.', static_url_path='')

# --- ROTA SECRETA PARA IMPORTAÇÃO ---
@app.route('/importar-dados-agora')
def rota_de_importacao():
    print("ROTA DE IMPORTAÇÃO INTELIGENTE ACIONADA!")
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Conectado ao DB para importação.")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS combinations (
                id SERIAL PRIMARY KEY,
                combination TEXT NOT NULL UNIQUE
            );
        """)
        print("Tabela 'combinations' verificada/criada.")
        
        cur.execute("TRUNCATE TABLE combinations;")
        print("Tabela 'combinations' limpa para nova importação.")
        
        batch = []
        total_inserted_this_run = 0
        with open(FILE_PATH_PARA_IMPORTAR, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                clean_line = line.strip()
                if clean_line:
                    batch.append((clean_line,))
                
                if len(batch) >= BATCH_SIZE:
                    insert_query = "INSERT INTO combinations (combination) VALUES (%s) ON CONFLICT (combination) DO NOTHING"
                    cur.executemany(insert_query, batch)
                    conn.commit()
                    total_inserted_this_run += cur.rowcount if cur.rowcount is not None else 0
                    batch = []
                    print(f"  -> Lote processado. Novas linhas inseridas nesta execução: {total_inserted_this_run}...")

        if batch:
            insert_query = "INSERT INTO combinations (combination) VALUES (%s) ON CONFLICT (combination) DO NOTHING"
            cur.executemany(insert_query, batch)
            conn.commit()
            total_inserted_this_run += cur.rowcount if cur.rowcount is not None else 0

        return f"<h1>Processo de Importação Concluído!</h1><p>{total_inserted_this_run} novas linhas foram inseridas no banco de dados.</p>"
    except Exception as e:
        print(f"ERRO NA IMPORTAÇÃO: {e}")
        return f"<h1>Erro durante a importação:</h1><p>{e}</p>", 500
    finally:
        if conn:
            conn.close()
            print("Conexão de importação fechada.")

# --- ROTAS NORMAIS DA APLICAÇÃO ---
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get-games/<int:count>')
def get_games(count):
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        query = "SELECT combination FROM combinations ORDER BY RANDOM() LIMIT %s;"
        cur.execute(query, (count,))
        results = [row[0] for row in cur.fetchall()]
        return jsonify(results)
    except Exception as e:
        print(f"Erro ao buscar jogos: {e}")
        return jsonify({"error": "Erro no banco de dados"}), 500
    finally:
        if conn:
            conn.close()

# Rota de Status
@app.route('/status')
def status_do_banco():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM combinations;")
        total_rows = cur.fetchone()[0]
        return jsonify({"status": "conectado", "total_de_linhas": total_rows})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        if conn:
            conn.close()
            
if __name__ == '__main__':
    app.run(debug=True)