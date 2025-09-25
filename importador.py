# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv
from urllib.parse import urlparse

# Carrega variáveis do .env
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# APIs das loterias
LOTERIAS_API = {
    "megasena": "https://loteriascaixa-api.herokuapp.com/api/megasena",
    "lotofacil": "https://loteriascaixa-api.herokuapp.com/api/lotofacil",
    "quina": "https://loteriascaixa-api.herokuapp.com/api/quina",
    "diadesorte": "https://loteriascaixa-api.herokuapp.com/api/diadesorte",
    "duplasena": "https://loteriascaixa-api.herokuapp.com/api/duplasena",
    "lotomania": "https://loteriascaixa-api.herokuapp.com/api/lotomania"
}

# Configuration constants
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

def get_db_connection():
    """Retorna uma conexão com o banco de dados PostgreSQL."""
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL não está definida no .env")

    # Esconde senha para debug
    parsed = urlparse(DATABASE_URL)
    safe_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
    logger.info(f"Conectando ao banco: {safe_url}")

    try:
        return psycopg2.connect(DATABASE_URL, connect_timeout=10)
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco de dados: {e}")
        raise

@contextmanager
def get_db_connection_context():
    """Context manager para gerenciar conexões com o banco de dados."""
    conn = None
    try:
        logger.info("Conectando ao banco de dados...")
        conn = get_db_connection()
        yield conn
    except Exception as e:
        logger.error(f"Erro no contexto da conexão com banco de dados: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Conexão com o banco de dados fechada.")

def verificar_e_atualizar_estrutura_tabela(conn):
    """Verifica e atualiza a estrutura da tabela para compatibilidade."""
    with conn.cursor() as cur:
        # Primeiro, verifica se a tabela existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'resultados_sorteados'
            );
        """)
        tabela_existe = cur.fetchone()[0]
        
        if not tabela_existe:
            logger.info("Tabela 'resultados_sorteados' não existe. Criando tabela completa...")
            cur.execute("""
                CREATE TABLE resultados_sorteados (
                    id SERIAL PRIMARY KEY,
                    tipo_loteria VARCHAR(50) NOT NULL,
                    concurso INTEGER NOT NULL,
                    data_sorteio DATE,
                    dezenas VARCHAR(255) NOT NULL,
                    ganhadores INTEGER DEFAULT 0,
                    acumulou BOOLEAN DEFAULT FALSE,
                    mes_sorte VARCHAR(50),
                    valor_acumulado DECIMAL(18, 2),
                    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tipo_loteria, concurso)
                );
            """)
        else:
            logger.info("Tabela 'resultados_sorteados' existe. Verificando/adicionando colunas...")
            
            # Verifica quais colunas existem
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'resultados_sorteados';
            """)
            colunas_existentes = [row[0] for row in cur.fetchall()]
            
            # Lista de colunas necessárias e seus tipos
            colunas_necessarias = {
                'data_sorteio': 'DATE',
                'dezenas': 'VARCHAR(255) NOT NULL',
                'ganhadores': 'INTEGER DEFAULT 0',
                'acumulou': 'BOOLEAN DEFAULT FALSE',
                'mes_sorte': 'VARCHAR(50)',
                'valor_acumulado': 'DECIMAL(18, 2)',
                'data_importacao': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            # Adiciona colunas que não existem
            for coluna, tipo in colunas_necessarias.items():
                if coluna not in colunas_existentes:
                    logger.info(f"Adicionando coluna '{coluna}' do tipo {tipo}...")
                    try:
                        cur.execute(f"""
                            ALTER TABLE resultados_sorteados 
                            ADD COLUMN {coluna} {tipo};
                        """)
                    except Exception as e:
                        logger.warning(f"Não foi possível adicionar a coluna '{coluna}'. Pode já existir ou haver outro problema: {e}")
            
            # Garante que os valores padrão estejam corretos
            if 'ganhadores' in colunas_existentes:
                cur.execute("""
                    UPDATE resultados_sorteados 
                    SET ganhadores = 0 
                    WHERE ganhadores IS NULL;
                """)
                cur.execute("""
                    ALTER TABLE resultados_sorteados 
                    ALTER COLUMN ganhadores SET DEFAULT 0;
                """)
            
            if 'acumulou' in colunas_existentes:
                cur.execute("""
                    UPDATE resultados_sorteados 
                    SET acumulou = FALSE 
                    WHERE acumulou IS NULL;
                """)
                cur.execute("""
                    ALTER TABLE resultados_sorteados 
                    ALTER COLUMN acumulou SET DEFAULT FALSE;
                """)
            
            # Adiciona a restrição UNIQUE se não existir
            cur.execute("""
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resultados_sorteados_tipo_loteria_concurso_key') THEN
                        ALTER TABLE resultados_sorteados ADD CONSTRAINT resultados_sorteados_tipo_loteria_concurso_key UNIQUE (tipo_loteria, concurso);
                    END IF;
                END $$;
            """)

        # Criar índices se não existirem (melhora performance de busca)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tipo_concurso 
            ON resultados_sorteados (tipo_loteria, concurso);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_sorteio 
            ON resultados_sorteados (data_sorteio);
        """)
        
        conn.commit()
    
    logger.info("✅ Estrutura da tabela verificada e atualizada com sucesso.")

def get_ultimo_concurso(conn, loteria: str) -> int:
    """Obtém o número do último concurso para uma loteria específica no banco de dados."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", 
            (loteria,)
        )
        resultado = cur.fetchone()[0]
        return resultado if resultado else 0

def processar_valor_acumulado(valor_acumulado_api: Any, acumulou: bool) -> Optional[float]:
    """Processa o valor acumulado vindo da API, tratando formatos e nulos."""
    if not acumulou:
        return 0.0
    
    if valor_acumulado_api is None:
        return None
    
    try:
        if isinstance(valor_acumulado_api, str):
            # Remove "R$", pontos de milhar e substitui vírgula por ponto para decimal
            valor_limpo = (valor_acumulado_api
                          .replace('R$', '')
                          .replace('.', '')
                          .replace(',', '.')
                          .strip())
            return float(valor_limpo) if valor_limpo else 0.0
        return float(valor_acumulado_api)
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Erro ao processar valor acumulado '{valor_acumulado_api}': {e}. Retornando None.")
        return None

def processar_data(data_str: str) -> Optional[str]:
    """Converte a string de data da API para o formato 'YYYY-MM-DD' do PostgreSQL."""
    if not data_str:
        return None
        
    try:
        # Tenta o formato dd/mm/yyyy (comum na API)
        if len(data_str) == 10 and '/' in data_str:
            parsed_date = datetime.strptime(data_str, '%d/%m/%Y')
            return parsed_date.strftime('%Y-%m-%d')
        
        # Tenta outros formatos comuns
        for fmt in ['%Y-%m-%d', '%d-%m-%Y']:
            try:
                parsed_date = datetime.strptime(data_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"⚠️ Formato de data inesperado para '{data_str}'. Retornando None.")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro genérico ao processar data '{data_str}': {e}. Retornando None.")
        return None

def fazer_requisicao_api(url: str, max_tentativas: int = MAX_RETRIES) -> Optional[Dict[Any, Any]]:
    """Realiza uma requisição HTTP GET à API com lógica de retentativa."""
    for tentativa in range(max_tentativas):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"⏳ Timeout na requisição para {url} (tentativa {tentativa + 1}/{max_tentativas}).")
        except requests.exceptions.ConnectionError:
            logger.warning(f"🌐 Erro de conexão para {url} (tentativa {tentativa + 1}/{max_tentativas}).")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Requisição API falhou para {url} (tentativa {tentativa + 1}/{max_tentativas}): {e}")
        
        if tentativa < max_tentativas - 1:
            import time
            time.sleep(2 ** tentativa) # Exponential backoff
    
    logger.error(f"❌ Todas as {max_tentativas} tentativas falharam para: {url}")
    return None

def extrair_dados_concurso(dados_api: Dict[Any, Any], nome_loteria: str) -> Optional[Dict[str, Any]]:
    """Extrai e valida os dados de um concurso da resposta da API."""
    try:
        concurso = dados_api.get('concurso')
        if not concurso:
            logger.warning("Campo 'concurso' ausente nos dados da API. Pulando registro.")
            return None
        
        dezenas_lista = dados_api.get('dezenas')
        if not dezenas_lista:
            logger.warning(f"Campo 'dezenas' ausente para o concurso {concurso}. Pulando registro.")
            return None
        
        data_str = dados_api.get('data')
        if not data_str:
            logger.warning(f"Campo 'data' ausente para o concurso {concurso}. Pulando registro.")
            return None
        
        # CORREÇÃO: Manter a ordem original para Dupla Sena, ordenar para outras loterias
        if nome_loteria == 'duplasena':
            # Para Dupla Sena: manter a ordem original do sorteio
            dezenas_str = " ".join(map(str, dezenas_lista))
            logger.info(f"📋 Dupla Sena - Mantendo ordem original: {dezenas_str}")
        else:
            # Para outras loterias: ordenar numericamente (comportamento anterior)
            dezenas_str = " ".join(sorted(map(str, dezenas_lista), key=int))
            logger.info(f"📋 {nome_loteria} - Dezenas ordenadas: {dezenas_str}")
        
        data_sorteio = processar_data(data_str)
        
        if not data_sorteio:
            logger.warning(f"Data inválida para o concurso {concurso}. Pulando registro.")
            return None
        
        acumulou = dados_api.get('acumulou', False)
        valor_acumulado_api = dados_api.get('valorEstimadoProximoConcurso') or dados_api.get('valorAcumulado')
        valor_acumulado = processar_valor_acumulado(valor_acumulado_api, acumulou)
        
        # Extrai ganhadores da primeira faixa de premiação
        ganhadores = 0
        premiacoes = dados_api.get('premiacoes', [])
        if premiacoes and len(premiacoes) > 0:
            ganhadores = premiacoes[0].get('ganhadores', 0)
        
        # Mês da Sorte (apenas para Dia de Sorte)
        mes_sorte = dados_api.get('mesSorte') if nome_loteria == 'diadesorte' else None
        
        return {
            'concurso': concurso,
            'data_sorteio': data_sorteio,
            'dezenas': dezenas_str,
            'ganhadores': ganhadores,
            'acumulou': acumulou,
            'mes_sorte': mes_sorte,
            'valor_acumulado': valor_acumulado
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair dados do concurso {dados_api.get('concurso', 'N/A')}: {e}. Dados brutos: {dados_api}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair dados do concurso {dados_api.get('concurso', 'N/A')}: {e}. Dados brutos: {dados_api}")
        return None

def inserir_ou_atualizar_resultado(conn, nome_loteria: str, dados_processados: Dict[str, Any]) -> bool:
    """Insere ou atualiza um resultado de concurso no banco de dados."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO resultados_sorteados (
                    tipo_loteria, concurso, data_sorteio, dezenas, 
                    ganhadores, acumulou, mes_sorte, valor_acumulado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tipo_loteria, concurso) DO UPDATE SET 
                    data_sorteio = EXCLUDED.data_sorteio, 
                    dezenas = EXCLUDED.dezenas, 
                    ganhadores = EXCLUDED.ganhadores,
                    acumulou = EXCLUDED.acumulou,
                    mes_sorte = EXCLUDED.mes_sorte,
                    valor_acumulado = EXCLUDED.valor_acumulado,
                    data_importacao = CURRENT_TIMESTAMP;
                """,
                (
                    nome_loteria,
                    dados_processados['concurso'],
                    dados_processados['data_sorteio'],
                    dados_processados['dezenas'],
                    dados_processados['ganhadores'],
                    dados_processados['acumulou'],
                    dados_processados['mes_sorte'],
                    dados_processados['valor_acumulado']
                )
            )
        return True
    except psycopg2.Error as e:
        logger.error(f"❌ Erro do PostgreSQL ao inserir/atualizar resultado do concurso {dados_processados.get('concurso')} ({nome_loteria}): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao inserir/atualizar resultado do concurso {dados_processados.get('concurso')} ({nome_loteria}): {e}")
        return False

def processar_loteria(conn, nome_loteria: str, url_base: str):
    """Processa a importação de resultados para uma loteria específica."""
    logger.info(f"\n--- 📌 Iniciando processamento para: {nome_loteria.upper()} ---")
    
    ultimo_concurso_db = get_ultimo_concurso(conn, nome_loteria)
    logger.info(f"✅ Último concurso de {nome_loteria.upper()} no banco de dados: {ultimo_concurso_db}")
    
    # Obtém o último concurso da API
    url_latest = f"{url_base}/latest"
    logger.info(f"🔎 Buscando último concurso na API: {url_latest}")
    dados_api_latest = fazer_requisicao_api(url_latest)
    
    if not dados_api_latest:
        logger.error(f"❌ Falha ao obter último concurso da API para {nome_loteria}. Pulando esta loteria.")
        return
    
    ultimo_concurso_api = dados_api_latest.get('concurso')
    if not ultimo_concurso_api:
        logger.error(f"❌ Não foi possível obter o número do último concurso da API para {nome_loteria}. Pulando esta loteria.")
        return
    
    logger.info(f"✅ Último concurso de {nome_loteria.upper()} na API: {ultimo_concurso_api}")
    
    if ultimo_concurso_api <= ultimo_concurso_db:
        logger.info(f"➡️ {nome_loteria.upper()}: Nenhum novo resultado para importar. O banco de dados está atualizado.")
        return
    
    # Importa novos resultados
    logger.info(f"🚀 {nome_loteria.upper()}: Novos resultados encontrados! Importando de {ultimo_concurso_db + 1} até {ultimo_concurso_api}...")
    
    novos_registros_count = 0
    erros_count = 0
    
    for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
        logger.info(f"➡️ Importando concurso {concurso_num} de {nome_loteria}...")
        try:
            url_concurso = f"{url_base}/{concurso_num}"
            dados_concurso = fazer_requisicao_api(url_concurso)
            
            if not dados_concurso:
                logger.warning(f"⚠️ Falha ao obter dados do concurso {concurso_num} de {nome_loteria}. Pulando.")
                erros_count += 1
                continue
            
            dados_processados = extrair_dados_concurso(dados_concurso, nome_loteria)
            
            if not dados_processados:
                logger.warning(f"⚠️ Falha ao processar dados do concurso {concurso_num} de {nome_loteria}. Pulando.")
                erros_count += 1
                continue
            
            if inserir_ou_atualizar_resultado(conn, nome_loteria, dados_processados):
                novos_registros_count += 1
            else:
                erros_count += 1
                
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao processar concurso {concurso_num} de {nome_loteria}: {e}. Pulando.")
            erros_count += 1
    
    # Commit das mudanças após processar todos os concursos de uma loteria
    try:
        conn.commit()
        logger.info(f"✅ Sucesso! {novos_registros_count} novos/atualizados resultados para {nome_loteria.upper()} importados.")
        if erros_count > 0:
            logger.warning(f"⚠️ Ocorreram erros em {erros_count} concursos de {nome_loteria.upper()}.")
        
        verificar_ultimo_registro_importado(conn, nome_loteria)
        
    except Exception as e:
        logger.error(f"❌ Erro ao fazer commit das mudanças para {nome_loteria.upper()}: {e}")
        conn.rollback()

def verificar_ultimo_registro_importado(conn, nome_loteria: str):
    """Verifica e exibe o último registro importado para uma loteria específica."""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT concurso, data_sorteio, ganhadores, acumulou, valor_acumulado
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC 
            LIMIT 1;
        """, (nome_loteria,))
        
        ultimo_registro = cur.fetchone()
        if ultimo_registro:
            logger.info(f"🔎 Último registro de {nome_loteria.upper()} no DB: "
                       f"concurso={ultimo_registro[0]}, data_sorteio={ultimo_registro[1]}, "
                       f"ganhadores={ultimo_registro[2]}, acumulou={ultimo_registro[3]}, "
                       f"valor_acumulado={ultimo_registro[4]}")
        else:
            logger.info(f"🔎 Nenhum registro encontrado para {nome_loteria.upper()} no DB.")

def importar_resultados():
    """Função principal para iniciar o processo de importação de resultados das loterias."""
    logger.info("🚀 Iniciando importação de resultados das loterias...")
    try:
        with get_db_connection_context() as conn:
            verificar_e_atualizar_estrutura_tabela(conn)
            
            for nome_loteria, url_base in LOTERIAS_API.items():
                try:
                    processar_loteria(conn, nome_loteria, url_base)
                except Exception as e:
                    logger.error(f"❌ Erro crítico ao processar {nome_loteria}: {e}. Tentando próxima loteria.")
                    continue
                    
    except Exception as e:
        logger.critical(f"❌ Erro fatal durante o processo de importação: {e}")
        raise

if __name__ == "__main__":
    importar_resultados()
    logger.info("🎉 Processo de importação concluído.")