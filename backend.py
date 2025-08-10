import psycopg2
import os
import random
from flask import Flask, jsonify

# --- CONFIGURAÇÃO ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# O nome do nosso arquivo de dados inicial
FILE_PATH_PARA_IMPORTAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados_parte_1.txt')

# --- Aplicação Flask ---
app = Flask(__name__, static_folder='.', static_url_path='')

# --- ROTA SECRETA PARA IMPORTAÇÃO ---
@app.route('/importar-dados-agora')
def rota_de_importacao():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Garante que a tabela exista
        cur.execute("""
            CREATE TABLE IF NOT EXISTS combinations (
                id SERIAL PRIMARY KEY,
                combination TEXT NOT NULL UNIQUE
            );
        """)

        # NÃO vamos limpar a tabela. Assim podemos adicionar mais dados depois.
        print("Tabela 'combinations' verificada.")
        
        # Inicia a leitura e inserção
        batch = []
        total_inserted_this_run = 0
        BATCH_SIZE = 10000
        
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
                    print(f"  -> Lote processado. Novas linhas: {total_inserted_this_run}...")

        if batch:
            insert_query = "INSERT INTO combinations (combination) VALUES (%s) ON CONFLICT (combination) DO NOTHING"
            cur.executemany(insert_query, batch)
            conn.commit()
            total_inserted_this_run += cur.rowcount if cur.rowcount is not None else 0

        return f"<h1>Importação Concluída!</h1><p>{total_inserted_this_run} novas linhas foram inseridas.</p>"
    except FileNotFoundError:
         return "<h1>Erro: Arquivo de dados não encontrado no servidor.</h1><p>Verifique se o 'dados_parte_1.txt' foi enviado corretamente para o GitHub.</p>", 404
    except Exception as e:
        return f"<h1>Erro na Importação:</h1><p>{e}</p>", 500
    finally:
        if conn:
            conn.close()

# --- ROTAS NORMAIS DA APLICAÇÃO ---
# Usaremos a versão final e mais robusta para a busca aleatória
@app.route('/get-games/<int:count>')
def get_games(count):
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM combinations;")
        total_rows = cur.fetchone()[0]

        if total_rows == 0: return jsonify([])
        
        sample_size = min(count, total_rows)
        random_offsets = random.sample(range(total_rows), sample_size)
        
        query = " UNION ALL ".join([f"(SELECT combination FROM combinations OFFSET {offset} LIMIT 1)" for offset in random_offsets])
        
        cur.execute(query)
        results = [row[0] for row in cur.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": "Erro no banco de dados"}), 500
    finally:
        if conn:
            conn.close()

# ... (outras rotas como /status, se você as manteve) ...
            
if __name__ == '__main__':
    app.run(debug=True)