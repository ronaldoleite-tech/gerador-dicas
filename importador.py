# -*- coding: utf-8 -*-
import os
import requests
import psycopg2
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time

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
    """Process accumulated value from API response - SIMPLIFIED VERSION"""
    if not acumulou:
        return 0.0
    
    # Try the most common field names in order of preference
    possible_fields = [
        'valorEstimadoProximoConcurso',
        'valorAcumuladoProximoConcurso', 
        'valorAcumulado'
    ]
    
    for field in possible_fields:
        valor = dados_api.get(field)
        if valor is not None:
            try:
                # Handle string values with currency formatting
                if isinstance(valor, str):
                    # Remove R$, dots (thousands separator) and replace comma with dot
                    valor_limpo = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                    if valor_limpo:
                        return float(valor_limpo)
                # Handle numeric values (including scientific notation)
                else:
                    return float(valor)
            except (ValueError, TypeError):
                continue
    
    # If no valid value found, return None to indicate missing data
    return None

def processar_data(data_str: str) -> Optional[str]:
    """Process date string to PostgreSQL format - SIMPLIFIED VERSION"""
    if not data_str:
        return None
        
    try:
        # Handle the most common format: dd/mm/yyyy
        if len(data_str) == 10 and data_str.count('/') == 2:
            day, month, year = data_str.split('/')
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        logger.warning(f"Unexpected date format: {data_str}")
        return None
        
    except Exception as e:
        logger.error(f"Error processing date '{data_str}': {e}")
        return None

def fazer_requisicao_api(url: str, max_tentativas: int = MAX_RETRIES) -> Optional[Dict[Any, Any]]:
    """Make API request with retry logic"""
    for tentativa in range(max_tentativas):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"API request failed (attempt {tentativa + 1}): {e}")
            if tentativa == max_tentativas - 1:
                logger.error(f"All API request attempts failed for: {url}")
                return None
            time.sleep(1)  # Wait before retry
    return None

def extrair_dados_concurso(dados: Dict[Any, Any], nome_loteria: str) -> Optional[Dict[str, Any]]:
    """Extract and validate contest data - SIMPLIFIED VERSION"""
    try:
        # Get required fields
        dezenas_lista = dados.get('dezenas')
        data_str = dados.get('data')
        concurso = dados.get('concurso')
        
        # Skip if any required field is missing
        if not dezenas_lista or not data_str or not concurso:
            logger.warning(f"Missing required fields for contest {concurso}")
            return None
        
        # Process data - keep it simple like the old version
        dezenas_str = " ".join(sorted(map(str, dezenas_lista)))
        data_formatada = processar_data(data_str)
        
        if not data_formatada:
            return None
        
        # Get optional fields with defaults
        acumulou = dados.get('acumulou', False)
        
        # Get winners from first prize tier
        ganhadores_faixa1 = 0
        premiacoes = dados.get('premiacoes', [])
        if premiacoes and len(premiacoes) > 0:
            ganhadores_faixa1 = premiacoes[0].get('ganhadores', 0)
        
        # Get accumulated value
        valor_acumulado = processar_valor_acumulado(dados, acumulou)
        
        # Month of luck (only for Dia de Sorte)
        mes_sorte = dados.get('mesSorte') if nome_loteria == 'diadesorte' else None
        
        return {
            'concurso': concurso,
            'data_sorteio': data_formatada,
            'dezenas': dezenas_str,
            'ganhadores': ganhadores_faixa1,
            'acumulou': acumulou,
            'mes_sorte': mes_sorte,
            'valor_acumulado': valor_acumulado
        }
        
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
    """Process a specific lottery - SIMPLIFIED VERSION"""
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
    
    # Import new results if any
    if ultimo_concurso_api > ultimo_concurso_db:
        logger.info(f"New results found! Importing from {ultimo_concurso_db + 1} to {ultimo_concurso_api}...")
        
        novos_registros = 0
        erros = 0
        
        for concurso_num in range(ultimo_concurso_db + 1, ultimo_concurso_api + 1):
            try:
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
                
                if inserir_resultado(conn, nome_loteria, dados_processados):
                    novos_registros += 1
                    # Debug log for important contests
                    if dados_processados['acumulou']:
                        logger.debug(f"Contest {concurso_num}: accumulated={dados_processados['acumulou']}, value={dados_processados['valor_acumulado']}")
                else:
                    erros += 1
                    
            except Exception as e:
                logger.error(f"Error processing contest {concurso_num}: {e}")
                erros += 1
                continue
        
        # Commit after processing all contests
        try:
            conn.commit()
            logger.info(f"✅ Successfully imported {novos_registros} new results for {nome_loteria}")
            if erros > 0:
                logger.warning(f"⚠️  {erros} errors occurred during import")
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            conn.rollback()
    else:
        logger.info("No new results to import.")

def importar_resultados():
    """Main function to import lottery results"""
    try:
        logger.info("🚀 Starting lottery results import...")
        
        with get_db_connection() as conn:
            criar_tabela_se_nao_existir(conn)
            
            for nome_loteria, url_base in LOTERIAS_API.items():
                try:
                    processar_loteria(conn, nome_loteria, url_base)
                    logger.info(f"Completed processing {nome_loteria}")
                except Exception as e:
                    logger.error(f"Error processing {nome_loteria}: {e}")
                    # Continue with other lotteries
                    continue
            
            logger.info("🎉 IMPORT COMPLETED!")
            
            # Show final summary
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tipo_loteria, COUNT(*) as total_contests,
                           MAX(concurso) as latest_contest,
                           COUNT(CASE WHEN acumulou = true THEN 1 END) as accumulated_contests
                    FROM resultados_sorteados 
                    GROUP BY tipo_loteria
                    ORDER BY tipo_loteria
                """)
                
                logger.info("📊 Database summary:")
                for row in cur.fetchall():
                    loteria, total, latest, accumulated = row
                    logger.info(f"   {loteria}: {total} contests (latest: {latest}, accumulated: {accumulated})")
                    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    importar_resultados()