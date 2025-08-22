# exportador_de_frequencia.py
import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
LOTERIAS = ['megasena', 'quina', 'lotofacil', 'diadesorte']

def exportar_frequencias():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    dados_finais = {}

    for loteria in LOTERIAS:
        print(f"Processando {loteria}...")
        cur.execute("""
            SELECT numero::integer, COUNT(*) as frequencia
            FROM (
                SELECT unnest(string_to_array(dezenas, ' ')) as numero
                FROM resultados_sorteados
                WHERE tipo_loteria = %s
            ) as numeros_individuais
            GROUP BY numero
            ORDER BY numero::integer ASC;
        """, (loteria,))
        
        resultados = cur.fetchall()
        # Converte a lista de tuplas (numero, frequencia) em um dicionário
        frequencia_dict = {str(num): freq for num, freq in resultados}
        dados_finais[loteria] = frequencia_dict

    cur.close()
    conn.close()

    # Salva tudo em um único arquivo JSON
    with open('frequencias_para_app.json', 'w', encoding='utf-8') as f:
        json.dump(dados_finais, f, ensure_ascii=False, indent=4)
        
    print("\nArquivo 'frequencias_para_app.json' criado com sucesso!")
    print("Copie este arquivo para o diretório do seu projeto de aplicativo.")

if __name__ == '__main__':
    exportar_frequencias()