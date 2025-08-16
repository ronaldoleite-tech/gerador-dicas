# --- INÍCIO DO importador.py PRONTO PARA O FUTURO ---

import psycopg2
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# --- CONFIGURAÇÃO CENTRAL DAS LOTERIAS ---
# Para adicionar uma nova loteria, basta adicionar uma entrada neste dicionário.
# A chave (ex: 'megasena') será salva no banco de dados.
# O valor (ex: 'sorteadosmegasena.txt') é o nome do arquivo a ser lido.
# ========================================================================
LOTERIAS_A_IMPORTAR = {
    'megasena': 'sorteadosmegasena.txt',
    'quina': 'sorteadosquina.txt',
    'lotofacil': 'sorteadoslotofacil.txt'
}
# ========================================================================

def realizar_importacao():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        print("ERRO: A variável DATABASE_URL não foi encontrada. Verifique seu arquivo .env")
        return

    conn = None
    try:
        print("INFO: Tentando conectar ao banco de dados...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("INFO: CONEXÃO COM O BANCO DE DADOS REALIZADA COM SUCESSO!")

        # --- ATUALIZAÇÃO AUTOMÁTICA DA ESTRUTURA DA TABELA ---
        print("INFO: Verificando e atualizando a estrutura da tabela 'resultados_sorteados'...")
        # 1. Adiciona a nova coluna 'tipo_loteria' se ela não existir.
        cur.execute("ALTER TABLE resultados_sorteados ADD COLUMN IF NOT EXISTS tipo_loteria VARCHAR(50);")
        # 2. Remove a antiga restrição de concurso único (se existir).
        cur.execute("ALTER TABLE resultados_sorteados DROP CONSTRAINT IF EXISTS resultados_sorteados_concurso_key;")
        # 3. Adiciona a nova chave única composta para permitir o mesmo número de concurso em loterias diferentes.
        cur.execute("ALTER TABLE resultados_sorteados ADD CONSTRAINT resultados_sorteados_concurso_loteria_unique UNIQUE (concurso, tipo_loteria);")
        conn.commit()
        print("INFO: Estrutura da tabela atualizada com sucesso.")

        total_inserido_geral = 0

        # --- LOOP PARA PROCESSAR CADA LOTERIA CONFIGURADA ---
        for tipo_loteria, nome_arquivo in LOTERIAS_A_IMPORTAR.items():
            print(f"\n--- Iniciando processamento para: {tipo_loteria.upper()} ---")
            
            caminho_arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_arquivo)
            
            if not os.path.exists(caminho_arquivo):
                print(f"AVISO: Arquivo '{nome_arquivo}' não encontrado. Pulando para a próxima loteria.")
                continue

            BATCH_SIZE = 500
            batch = []
            total_inserido_loteria = 0
            
            with open(caminho_arquivo, 'r', encoding='cp1252') as f:
                print(f"INFO: Lendo o arquivo '{nome_arquivo}'...")
                next(f)  # Pula o cabeçalho

                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 2:  # Precisa de pelo menos concurso e uma dezena
                        continue
                    
                    try:
                        num_concurso = int(parts[0])
                        dezenas = parts[1:]
                        linha_formatada = " ".join(sorted(dezenas, key=int))
                        # Adiciona o tipo de loteria ao lote
                        batch.append((num_concurso, linha_formatada, tipo_loteria))
                    except ValueError:
                        print(f"AVISO [{tipo_loteria.upper()}]: Linha ignorada por formato inválido: {line.strip()}")
                        continue
                    
                    if len(batch) >= BATCH_SIZE:
                        insert_query = "INSERT INTO resultados_sorteados (concurso, dezenas, tipo_loteria) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING"
                        cur.executemany(insert_query, batch)
                        novos_registros = cur.rowcount if cur.rowcount is not None else 0
                        total_inserido_loteria += novos_registros
                        conn.commit()
                        if novos_registros > 0:
                            print(f"INFO [{tipo_loteria.upper()}]: Lote inserido. {novos_registros} novos registros adicionados.")
                        batch = []

            if batch:
                insert_query = "INSERT INTO resultados_sorteados (concurso, dezenas, tipo_loteria) VALUES (%s, %s, %s) ON CONFLICT (concurso, tipo_loteria) DO NOTHING"
                cur.executemany(insert_query, batch)
                novos_registros = cur.rowcount if cur.rowcount is not None else 0
                total_inserido_loteria += novos_registros
                conn.commit()
                if novos_registros > 0:
                    print(f"INFO [{tipo_loteria.upper()}]: Lote final inserido. {novos_registros} novos registros adicionados.")
            
            print(f"--- Finalizado para {tipo_loteria.upper()}: {total_inserido_loteria} novos concursos adicionados. ---")
            total_inserido_geral += total_inserido_loteria

        print("\n========================================================")
        print("IMPORTAÇÃO GERAL CONCLUÍDA COM SUCESSO!")
        print(f"{total_inserido_geral} novos concursos foram adicionados no total.")
        print("========================================================\n")

    except Exception as e:
        print(f"\nERRO: Um erro inesperado ocorreu durante a importação: {e}\n")
    finally:
        if conn:
            conn.close()
            print("INFO: Conexão com o banco de dados fechada.")

if __name__ == "__main__":
    realizar_importacao()

# --- FIM DO importador.py ---