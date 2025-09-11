# -*- coding: utf-8 -*-
# SCRIPT DE TESTE - Testa apenas um concurso específico
import os
import requests
import psycopg2
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')

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
        logger.info(f"Available fields in API response: {list(dados_api.keys())}")
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
        
        logger.info(f"✅ SUCCESS! Accumulated value processed: {resultado} (from field: {field_used})")
        return resultado
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Error processing accumulated value '{valor_acumulado}' from field '{field_used}': {e}")
        return None

def teste_concurso_especifico():
    """Test processing a specific contest"""
    try:
        # Test with contest 2912 (the one we know is accumulated)
        url = "https://loteriascaixa-api.herokuapp.com/api/megasena/2912"
        
        logger.info("🧪 TESTING SPECIFIC CONTEST...")
        logger.info(f"Fetching: {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        dados_api = response.json()
        
        logger.info(f"📊 API Response keys: {list(dados_api.keys())}")
        logger.info(f"📊 Contest: {dados_api.get('concurso')}")
        logger.info(f"📊 Accumulated: {dados_api.get('acumulou')}")
        
        # Test the value processing function
        acumulou = dados_api.get('acumulou', False)
        valor = processar_valor_acumulado(dados_api, acumulou)
        
        logger.info(f"📊 Processed accumulated value: {valor}")
        
        # Show relevant fields from API
        relevant_fields = [
            'valorEstimadoProximoConcurso',
            'valorAcumuladoProximoConcurso', 
            'valorAcumuladoConcurso_0_5',
            'valorAcumulado'
        ]
        
        logger.info("📊 Relevant fields in API response:")
        for field in relevant_fields:
            if field in dados_api:
                logger.info(f"   {field}: {dados_api[field]}")
        
        # Now try to update this specific contest in the database
        if valor is not None:
            logger.info("🔄 Updating database with correct value...")
            
            conn = psycopg2.connect(DATABASE_URL)
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE resultados_sorteados 
                    SET valor_acumulado = %s, data_importacao = CURRENT_TIMESTAMP
                    WHERE tipo_loteria = 'megasena' AND concurso = 2912
                """, (valor,))
                
                if cur.rowcount > 0:
                    conn.commit()
                    logger.info(f"✅ SUCCESS! Updated contest 2912 with value: {valor}")
                    
                    # Verify the update
                    cur.execute("""
                        SELECT concurso, acumulou, valor_acumulado, ganhadores 
                        FROM resultados_sorteados 
                        WHERE tipo_loteria = 'megasena' AND concurso = 2912
                    """)
                    result = cur.fetchone()
                    if result:
                        logger.info(f"📋 Verified record: contest={result[0]}, accumulated={result[1]}, value={result[2]}, winners={result[3]}")
                else:
                    logger.warning("⚠️  No rows updated - contest 2912 may not exist in database")
            
            conn.close()
        else:
            logger.error("❌ Failed to process accumulated value")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    teste_concurso_especifico()