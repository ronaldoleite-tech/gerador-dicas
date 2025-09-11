# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

LOTERIAS_API = {
    'megasena': 'https://loteriascaixa-api.herokuapp.com/api/megasena',
    'lotofacil': 'https://loteriascaixa-api.herokuapp.com/api/lotofacil',
    'quina': 'https://loteriascaixa-api.herokuapp.com/api/quina',
    'diadesorte': 'https://loteriascaixa-api.herokuapp.com/api/diadesorte'
}

# Configuration constants
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")

def criar_tabela_se_nao_existir(conn):
    """Create the results table if it doesn't exist"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resultados_sorteados (
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
        
        # Create indexes for better performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tipo_concurso 
            ON resultados_sorteados (tipo_loteria, concurso);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_sorteio 
            ON resultados_sorteados (data_sorteio);
        """)
        
        conn.commit()
    logger.info("Table 'resultados_sorteados' verified/created successfully.")

def get_ultimo_concurso(conn, loteria: str) -> int:
    """Get the last contest number for a specific lottery"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(concurso) FROM resultados_sorteados WHERE tipo_loteria = %s;", 
            (loteria,)
        )
        resultado = cur.fetchone()[0]
        return resultado if resultado else 0

def processar_valor_acumulado(dados_api: Dict[Any, Any], acumulou: bool) -> Optional[float]:
    """Process accumulated value from API response with correct field mapping"""
    if not acumulou:
        return 0.0
    
    # Try different possible field names from the API
    possible_fields = [
        'valorEstimadoProximoConcurso',  # Primary field for next contest estimate
        'valorAcumuladoProximoConcurso', # Alternative accumulated value
        'valorAcumuladoConcurso_0_5',    # Another possible field
        'valorAcumulado',                # Original field name (fallback)
    ]
    
    valor_acumulado = None
    field_used = None
    
    for field in possible_fields:
        valor_acumulado = dados_api.get(field)
        if valor_acumulado is not None:
            field_used = field
            break
    
    if valor_acumulado is None:
        logger.warning("No accumulated value field found in API response")
        return None
    
    try:
        if isinstance(valor_acumulado, str):
            # Clean currency formatting
            valor_limpo = (valor_acumulado
                          .replace('R$', '')
                          .replace('.', '')
                          .replace(',', '.')
                          .strip())
            resultado = float(valor_limpo) if valor_limpo else 0.0
        else:
            # Handle scientific notation (like 5.5E7)
            resultado = float(valor_acumulado)
        
        logger.debug(f"Accumulated value processed: {resultado} (from field: {field_used})")
        return resultado
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Error processing accumulated value '{valor_acumulado}' from field '{field_used}': {e}")
        return None

def fazer_requisicao_api(url: str, max_tentativas: int = MAX_RETRIES) -> Optional[Dict[Any, Any]]:
    """Make API request with retry logic"""
    for tentativa in range(max_tentativas):
        try:
            logger.debug(f"API request to: {url} (attempt {tentativa + 1})")
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"API request failed (attempt {tentativa + 1}): {e}")
            if tentativa == max_tentativas - 1:
                logger.error(f"All API request attempts failed for: {url}")
                return None
    return None

def extrair_dados_concurso(dados: Dict[Any, Any], nome_loteria: str) -> Optional[Dict[str, Any]]:
    """Extract and validate contest data"""
    try:
        # Validate required fields
        dezenas_lista = dados.get('dezenas')
        if not dezenas_lista:
            logger.warning("Missing 'dezenas' in contest data")
            return None
        
        data_str = dados.get('data')
        if not data_str:
            logger.warning("Missing 'data' in contest data")
            return None
        
        concurso = dados.get('concurso')
        if not concurso:
            logger.warning("Missing 'concurso' in contest data")
            return None
        
        # Process data
        dezenas_str = " ".join(sorted(map(str, dezenas_lista)))
        data_formatada = processar_data(data_str)
        
        if not data_formatada:
            return None
        
        acumulou = dados.get('acumulou', False)
        
        # FIXED: Pass the entire API response to get the correct field
        valor_acumulado = processar_valor_acumulado(dados, acumulou)
        
        # Extract winners from first prize tier
        ganhadores_faixa1 = 0
        premiacoes = dados.get('premiacoes', [])
        if premiacoes and len(premiacoes) > 0:
            ganhadores_faixa1 = premiacoes[0].get('ganhadores', 0)
        
        # Month of luck (only for Dia de Sorte)
        mes_sorte = dados.get('mesSorte') if nome_loteria == 'diadesorte' else None
        
        resultado = {
            'concurso': concurso,
            'data_sorteio': data_formatada,
            'dezenas': dezenas_str,
            'ganhadores': ganhadores_faixa1,
            'acumulou': acumulou,
            'mes_sorte': mes_sorte,
            'valor_acumulado': valor_acumulado
        }
        
        # Debug log for accumulated values
        if valor_acumulado is not None:
            logger.debug(f"Contest {concurso}: accumulated={acumulou}, value={valor_acumulado}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error extracting contest data: {e}")
        return None

def inserir_resultado(conn, nome_loteria: str, dados_processados: Dict[str, Any]) -> bool:
    """Insert contest result into database"""
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
    except Exception as e:
        logger.error(f"Error inserting result: {e}")
        return False

def processar_loteria(conn, nome_loteria: str, url_base: str):
    """Process a specific lottery"""
    logger.info(f"--- Processing Lottery: {nome_loteria.upper()} ---")
    
    ultimo_concurso_db = get_ultimo_concurso(conn, nome_loteria)
    logger.info(f"Last contest in database: {ultimo_concurso_db}")
    
    # Get latest contest from API
    url_latest = f"{url_base}/latest"
    dados_api = fazer_requisicao_api(url_latest)
    
    if not dados_api:
        logger.error(f"Failed to get latest contest for {nome_loteria}")
        return
    
    ultimo_concurso_api = dados_api.get('concurso')
    if not ultimo_concurso_api:
        logger.error("Could not get latest contest number from API")
        return
    
    logger.info(f"Latest contest in API: {ultimo_concurso_api}")
    
    if ultimo_concurso_api <= ultimo_concurso_db:
        logger.info("No new results to import. Database is up to date.")
        return
    
    # Import new results
    logger.info(f"New results found! Importing from {ultimo_concurso_db + 1} to {ultimo_concurso_api}...")
    
    novos_registros = 0
    erros = 0
    
    for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
        url_concurso = f"{url_base}/{concurso_num}"
        dados_concurso = fazer_requisicao_api(url_concurso)
        
        if not dados_concurso:
            logger.warning(f"Failed to get data for contest {concurso_num}")
            erros += 1
            continue
        
        dados_processados = extrair_dados_concurso(dados_concurso, nome_loteria)
        
        if not dados_processados:
            logger.warning(f"Failed to process data for contest {concurso_num}")
            erros += 1
            continue
        
        # Debug log for the latest contest
        if concurso_num == ultimo_concurso_api:
            logger.info(f"LATEST CONTEST - Processed data: {dados_processados}")
        
        if inserir_resultado(conn, nome_loteria, dados_processados):
            novos_registros += 1
        else:
            erros += 1
    
    # Commit all changes
    try:
        conn.commit()
        logger.info(f"Success! {novos_registros} new results for {nome_loteria} imported.")
        if erros > 0:
            logger.warning(f"Errors occurred in {erros} contests.")
        
        # Verify last record was inserted correctly
        verificar_ultimo_registro(conn, nome_loteria)
        
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        conn.rollback()

def verificar_ultimo_registro(conn, nome_loteria: str):
    """Verify the last record was inserted correctly"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT concurso, acumulou, valor_acumulado, ganhadores 
            FROM resultados_sorteados 
            WHERE tipo_loteria = %s 
            ORDER BY concurso DESC 
            LIMIT 1
        """, (nome_loteria,))
        
        ultimo_registro = cur.fetchone()
        if ultimo_registro:
            logger.info(f"Last record in DB: contest={ultimo_registro[0]}, "
                       f"accumulated={ultimo_registro[1]}, "
                       f"value={ultimo_registro[2]}, "
                       f"winners={ultimo_registro[3]}")

def importar_resultados():
    """Main function to import lottery results"""
    try:
        with get_db_connection() as conn:
            criar_tabela_se_nao_existir(conn)
            
            for nome_loteria, url_base in LOTERIAS_API.items():
                try:
                    processar_loteria(conn, nome_loteria, url_base)
                except Exception as e:
                    logger.error(f"Error processing {nome_loteria}: {e}")
                    # Continue with other lotteries
                    continue
                    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting lottery results import...")
    importar_resultados()
    logger.info("Import process completed.")