# dividir_arquivo.py
import os

arquivo_grande = 'testecombinaçoes_final.txt'
linhas_por_arquivo = 1000000 # 1 milhão de linhas por arquivo
prefixo_saida = 'dados_parte_'

def dividir_arquivo_grande():
    try:
        with open(arquivo_grande, 'r', encoding='utf-8', errors='ignore') as f:
            print(f"Lendo o arquivo grande: {arquivo_grande}")
            
            contador_arquivos = 1
            contador_linhas = 0
            arquivo_saida = None
            
            for linha in f:
                if contador_linhas % linhas_por_arquivo == 0:
                    if arquivo_saida:
                        arquivo_saida.close()
                        print(f"  -> Arquivo finalizado.")
                    
                    nome_arquivo_saida = f"{prefixo_saida}{contador_arquivos}.txt"
                    arquivo_saida = open(nome_arquivo_saida, 'w', encoding='utf-8')
                    print(f"Criando novo arquivo: {nome_arquivo_saida}...")
                    contador_arquivos += 1
                
                arquivo_saida.write(linha)
                contador_linhas += 1
            
            if arquivo_saida:
                arquivo_saida.close()
                print(f"  -> Arquivo final finalizado.")
            
            print("\n--- PROCESSO DE DIVISÃO CONCLUÍDO! ---")
            print(f"Total de {contador_linhas} linhas divididas em {contador_arquivos - 1} arquivos.")

    except FileNotFoundError:
        print(f"ERRO: Arquivo '{arquivo_grande}' não encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

if __name__ == '__main__':
    dividir_arquivo_grande()