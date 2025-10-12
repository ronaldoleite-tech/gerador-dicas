# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 1. CONEXÃO COM O BANCO DE DADOS ---
def get_db_connection():
    """Retorna uma conexão com o banco de dados PostgreSQL."""
    try:
        return psycopg2.connect(DATABASE_URL, connect_timeout=10)
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco de dados: {e}")
        raise

# --- 2. LÓGICA DE IMPORTAÇÃO (COM MELHORIAS E COMPATIBILIDADE) ---

LOTERIAS_API = {
    'maismilionaria': 'https://loteriascaixa-api.herokuapp.com/api/maismilionaria',
    'megasena': 'https://loteriascaixa-api.herokuapp.com/api/megasena',
    'lotofacil': 'https://loteriascaixa-api.herokuapp.com/api/lotofacil',
    'quina': 'https://loteriascaixa-api.herokuapp.com/api/quina',
    'lotomania': 'https://loteriascaixa-api.herokuapp.com/api/lotomania',
    'timemania': 'https://loteriascaixa-api.herokuapp.com/api/timemania',
    'duplasena': 'https://loteriascaixa-api.herokuapp.com/api/duplasena',
    'diadesorte': 'https://loteriascaixa-api.herokuapp.com/api/diadesorte',
    'supersete': 'https://loteriascaixa-api.herokuapp.com/api/supersete'
}

# Configuration constants
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

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
        # Verifica se a tabela existe
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
                    trevos VARCHAR(20),
                    time_coracao VARCHAR(100),
                    valor_proximo_concurso NUMERIC(15,2),
                    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tipo_loteria, concurso)
                );
            """)
            logger.info("✅ Tabela 'resultados_sorteados' criada com sucesso.")
        else:
            logger.info("Tabela 'resultados_sorteados' existe. Verificando/adicionando colunas...")
            
            # Obtém colunas existentes
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'resultados_sorteados';
            """)
            colunas_existentes = {row[0] for row in cur.fetchall()}
            
            # Colunas para verificar/adicionar
            colunas_para_adicionar = {
                'trevos': 'VARCHAR(20)',
                'time_coracao': 'VARCHAR(100)',
                'valor_proximo_concurso': 'NUMERIC(15,2)'
            }
            
            # Adiciona colunas faltantes
            for coluna, tipo in colunas_para_adicionar.items():
                if coluna not in colunas_existentes:
                    logger.info(f"➕ Adicionando coluna '{coluna}'...")
                    try:
                        cur.execute(f"ALTER TABLE resultados_sorteados ADD COLUMN {coluna} {tipo};")
                        logger.info(f"✅ Coluna '{coluna}' adicionada com sucesso.")
                    except Exception as e:
                        logger.error(f"❌ Erro ao adicionar coluna '{coluna}': {e}")

        # Cria índices para melhor performance
        try:
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tipo_loteria_concurso 
                ON resultados_sorteados(tipo_loteria, concurso);
            """)
            logger.info("✅ Índice verificado/criado com sucesso.")
        except Exception as e:
            logger.error(f"❌ Erro ao criar índice: {e}")
        
        conn.commit()
    
    logger.info("✅ Estrutura da tabela verificada e atualizada com sucesso.")

def verificar_estrutura_tabela(conn):
    """Verifica a estrutura atual da tabela"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'resultados_sorteados'
            ORDER BY ordinal_position;
        """)
        colunas = cur.fetchall()
        logger.info("📋 Estrutura atual da tabela:")
        for coluna in colunas:
            logger.info(f"   - {coluna[0]} ({coluna[1]}, nullable: {coluna[2]})")    

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
            return float(valor_limpo) if valor_limpo else None
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
        
        # Tenta outros formatos comuns caso o acima falhe
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
    try:
        concurso = dados_api.get('concurso')
        if not concurso:
            logger.warning("Campo 'concurso' ausente nos dados da API. Pulando registro.")
            return None
        
        # Obter data_str dos dados da API
        data_str = dados_api.get('data')
        if not data_str:
            logger.warning(f"Campo 'data' ausente para o concurso {concurso}. Pulando registro.")
            return None
        
        dezenas_lista = dados_api.get('dezenas')
        dezenas_str = ""  # Inicializa a variável
        
        # Para Super Sete, 'dezenas' pode vir como string "1234567" ou lista de strings/ints. 
        if nome_loteria == 'supersete':
            if isinstance(dezenas_lista, list):
                dezenas_lista = [str(d) for d in dezenas_lista]
                dezenas_str = "".join(dezenas_lista)
            elif isinstance(dezenas_lista, str):
                dezenas_str = dezenas_lista
            else:
                logger.warning(f"Campo 'dezenas' inválido para Super Sete {concurso}. Pulando.")
                return None
        elif not dezenas_lista:
            logger.warning(f"Campo 'dezenas' ausente para o concurso {concurso}. Pulando registro.")
            return None
        else:
            # CORREÇÃO: Manter a ordem original para Dupla Sena e Mais Milionária, ordenar para outras loterias
            if nome_loteria == 'duplasena' or nome_loteria == 'maismilionaria':
                # Para Dupla Sena e Mais Milionária: manter a ordem original do sorteio
                if isinstance(dezenas_lista, list):
                    dezenas_str = " ".join(map(lambda x: f"{int(x):02d}", dezenas_lista))
                else:
                    dezenas_str = dezenas_lista
                logger.info(f"📋 {nome_loteria} - Mantendo ordem original: {dezenas_str}")
            else:
                # Para outras loterias: ordenar numericamente
                if isinstance(dezenas_lista, list):
                    dezenas_str = " ".join(sorted(map(lambda x: f"{int(x):02d}", dezenas_lista), key=int))
                else:
                    dezenas_str = dezenas_lista
                logger.info(f"📋 {nome_loteria} - Dezenas ordenadas: {dezenas_str}")
        
        data_sorteio = processar_data(data_str)
        
        if not data_sorteio:
            logger.warning(f"Data inválida para o concurso {concurso}. Pulando registro.")
            return None
        
        acumulou = dados_api.get('acumulou', False)
        
        # ✅ CORREÇÃO: Separar valor acumulado REAL do valor estimado próximo concurso
        valor_acumulado_api = dados_api.get('valorAcumulado')
        valor_acumulado = processar_valor_acumulado(valor_acumulado_api, acumulou)
        
        # Valor do próximo concurso (NÃO usar fallback - manter separado)
        valor_proximo_concurso_api = dados_api.get('valorEstimadoProximoConcurso')
        valor_proximo_concurso = processar_valor_acumulado(valor_proximo_concurso_api, False)
        
        # DEBUG: Log dos valores
        logger.info(f"💰 {nome_loteria} Concurso {concurso}: valorAcumulado={valor_acumulado_api}, valorEstimadoProximoConcurso={valor_proximo_concurso_api}")
        
        # Extrai ganhadores da primeira faixa de premiação
        ganhadores = 0
        premiacoes = dados_api.get('premiacoes', [])
        if premiacoes and len(premiacoes) > 0:
            ganhadores = premiacoes[0].get('ganhadores', 0)

        # Mês da Sorte (apenas para Dia de Sorte)
        mes_sorte = dados_api.get('mesSorte') if nome_loteria == 'diadesorte' else None

        # Trevos (apenas para Mais Milionária)
        trevos_lista = dados_api.get('trevos')
        trevos_str = " ".join(map(str, trevos_lista)) if nome_loteria == 'maismilionaria' and trevos_lista else None

        # Time do Coração (apenas para Timemania)
        time_coracao = dados_api.get('timeCoracao') if nome_loteria == 'timemania' else None

        return {
            'concurso': concurso,
            'data_sorteio': data_sorteio,
            'dezenas': dezenas_str,
            'ganhadores': ganhadores,
            'acumulou': acumulou,
            'mes_sorte': mes_sorte,
            'valor_acumulado': valor_acumulado,           # Valor acumulado REAL
            'trevos': trevos_str,
            'time_coracao': time_coracao,
            'valor_proximo_concurso': valor_proximo_concurso  # Valor estimado próximo concurso
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao extrair dados do concurso {dados_api.get('concurso', 'N/A')}: {e}. Dados brutos: {dados_api}")
        return None
    
def inserir_ou_atualizar_resultado(conn, nome_loteria: str, dados_processados: Dict[str, Any]) -> bool:
    """Insere ou atualiza um resultado de concurso no banco de dados."""
    try:
        with conn.cursor() as cur:
            # Primeiro, verifica quais colunas existem na tabela
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'resultados_sorteados'
                ORDER BY ordinal_position;
            """)
            colunas_existentes = [row[0] for row in cur.fetchall()]
            
            # Define as colunas base
            colunas_base = [
                'tipo_loteria', 'concurso', 'data_sorteio', 'dezenas', 
                'ganhadores', 'acumulou', 'mes_sorte', 'valor_acumulado'
            ]
            
            # Adiciona colunas extras apenas se existirem na tabela
            colunas_extras = ['trevos', 'time_coracao', 'valor_proximo_concurso']
            colunas_para_inserir = colunas_base.copy()
            placeholders = ['%s'] * len(colunas_base)
            
            for coluna_extra in colunas_extras:
                if coluna_extra in colunas_existentes:
                    colunas_para_inserir.append(coluna_extra)
                    placeholders.append('%s')
            
            # Constrói a query dinamicamente
            colunas_str = ", ".join(colunas_para_inserir)
            placeholders_str = ", ".join(placeholders)
            
            # Prepara os valores na mesma ordem das colunas
            valores = [
                nome_loteria,
                dados_processados['concurso'],
                dados_processados['data_sorteio'],
                dados_processados['dezenas'],
                dados_processados['ganhadores'],
                dados_processados['acumulou'],
                dados_processados['mes_sorte'],
                dados_processados['valor_acumulado']
            ]
            
            # Adiciona valores extras apenas se as colunas existirem
            for coluna_extra in colunas_extras:
                if coluna_extra in colunas_existentes:
                    valores.append(dados_processados.get(coluna_extra))
            
            # Constrói a parte SET do ON CONFLICT dinamicamente
            set_clause = ", ".join([
                f"{col} = EXCLUDED.{col}" 
                for col in colunas_para_inserir 
                if col not in ['tipo_loteria', 'concurso']
            ])
            
            query = f"""
                INSERT INTO resultados_sorteados ({colunas_str})
                VALUES ({placeholders_str})
                ON CONFLICT (tipo_loteria, concurso) DO UPDATE SET 
                    {set_clause},
                    data_importacao = CURRENT_TIMESTAMP;
            """
            
            cur.execute(query, valores)
            return True
            
    except psycopg2.Error as e:
        logger.error(f"❌ Erro do PostgreSQL ao inserir/atualizar resultado do concurso {dados_processados.get('concurso')} ({nome_loteria}): {e}")
        conn.rollback()
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao inserir/atualizar resultado do concurso {dados_processados.get('concurso')} ({nome_loteria}): {e}")
        conn.rollback()
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
    """Verifica e exibe o último registro importado para uma loteria específica, incluindo novos campos."""
    with conn.cursor() as cur:
        # Primeiro, obtenha a lista de todas as colunas existentes na tabela
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'resultados_sorteados'
            ORDER BY ordinal_position;
        """)
        todas_colunas_db = [row[0] for row in cur.fetchall()]

        # Define as colunas que queremos tentar exibir, em ordem de preferência
        colunas_desejadas = [
            'concurso', 'data_sorteio', 'dezenas', 'ganhadores',
            'acumulou', 'mes_sorte', 'valor_acumulado',
            'trevos', 'time_coracao', 'valor_proximo_concurso', 'data_importacao'
        ]

        # Filtra as colunas desejadas para incluir apenas as que realmente existem no DB
        colunas_para_selecionar = [col for col in colunas_desejadas if col in todas_colunas_db]

        if not colunas_para_selecionar:
            logger.warning("Nenhuma coluna relevante encontrada na tabela 'resultados_sorteados'. Não é possível exibir o último registro.")
            return

        # Constrói a query SELECT dinamicamente
        select_clause = ", ".join(colunas_para_selecionar)

        cur.execute(f"""
            SELECT {select_clause}
            FROM resultados_sorteados
            WHERE tipo_loteria = %s
            ORDER BY concurso DESC
            LIMIT 1;
        """, (nome_loteria,))

        ultimo_registro = cur.fetchone()

        if ultimo_registro:
            log_msg = f"🔎 Último registro de {nome_loteria.upper()} no DB: "
            # Mapeia os valores para os nomes das colunas correspondentes
            detalhes_registro = {
                col: ultimo_registro[colunas_para_selecionar.index(col)]
                for col in colunas_para_selecionar
            }

            # Formata os detalhes para exibição
            formatted_details = []
            for k, v in detalhes_registro.items():
                if v is None:
                    formatted_details.append(f"{k}=NULL")
                elif k == 'data_sorteio':
                    formatted_details.append(f"{k}={v.strftime('%Y-%m-%d') if isinstance(v, date) else v}")
                elif k == 'data_importacao':
                    formatted_details.append(f"{k}={v.strftime('%Y-%m-%d %H:%M:%S') if isinstance(v, datetime) else v}")
                elif k in ['valor_acumulado', 'valor_proximo_concurso']:
                    formatted_details.append(f"{k}=R${v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')) # Formato BR
                else:
                    formatted_details.append(f"{k}={v}")

            log_msg += ", ".join(formatted_details)
            logger.info(log_msg)
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