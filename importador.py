# -*- coding: utf-8 -*-
# SCRIPT PARA ATUALIZAR VALORES ACUMULADOS EXISTENTES
import os
import requests
import psycopg2
import logging
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any
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

def processar_valor_acumulado(dados_api: Dict[Any, Any], acumulou: bool) -> Optional[float]:
    """Process accumulated value from API response"""
    if not acumulou:
        return 0.0
    
    possible_fields = [
        'valorEstimadoProximoConcurso',
        'valorAcumuladoProximoConcurso',
        'valorAcumuladoConcurso_0_5',
        'valorAcumulado',
    ]
    
    for field in possible_fields:
        valor_acumulado = dados_api.get(field)
        if valor_acumulado is not None:
            try:
                if isinstance(valor_acumulado, str):
                    valor_limpo = (valor_acumulado
                                  .replace('R$', '')
                                  .replace('.', '')
                                  .replace(',', '.')
                                  .strip())
                    return float(valor_limpo) if valor_limpo else 0.0
                else:
                    return float(valor_acumulado)
            except (ValueError, TypeError):
                continue
    
    return None

def buscar_concursos_acumulados(conn):
    """Get all contests marked as accumulated but with NULL accumulated value"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tipo_loteria, concurso 
            FROM resultados_sorteados 
            WHERE acumulou = true 
            AND (valor_acumulado IS NULL OR valor_acumulado = 0)
            ORDER BY tipo_loteria, concurso
        """)
        return cur.fetchall()

def atualizar_valores_acumulados():
    """Update accumulated values for all contests marked as accumulated"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        
        # Get contests that need updating
        concursos_pendentes = buscar_concursos_acumulados(conn)
        
        if not concursos_pendentes:
            logger.info("✅ No contests need updating!")
            return
        
        logger.info(f"📋 Found {len(concursos_pendentes)} contests to update")
        
        atualizados = 0
        erros = 0
        
        for tipo_loteria, concurso in concursos_pendentes:
            try:
                logger.info(f"🔄 Processing {tipo_loteria} contest {concurso}...")
                
                # Get contest data from API
                url = f"{LOTERIAS_API[tipo_loteria]}/{concurso}"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                dados_api = response.json()
                
                # Process accumulated value
                acumulou = dados_api.get('acumulou', False)
                if acumulou:
                    valor = processar_valor_acumulado(dados_api, acumulou)
                    
                    if valor is not None:
                        # Update database
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE resultados_sorteados 
                                SET valor_acumulado = %s, data_importacao = CURRENT_TIMESTAMP
                                WHERE tipo_loteria = %s AND concurso = %s
                            """, (valor, tipo_loteria, concurso))
                        
                        logger.info(f"✅ Updated {tipo_loteria} {concurso}: {valor}")
                        atualizados += 1
                    else:
                        logger.warning(f"⚠️  Could not process value for {tipo_loteria} {concurso}")
                        erros += 1
                else:
                    logger.info(f"ℹ️  Contest {tipo_loteria} {concurso} is no longer accumulated")
                    # Update to mark as not accumulated
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE resultados_sorteados 
                            SET acumulou = false, valor_acumulado = 0, data_importacao = CURRENT_TIMESTAMP
                            WHERE tipo_loteria = %s AND concurso = %s
                        """, (tipo_loteria, concurso))
                    atualizados += 1
                
                # Small delay to avoid hitting API limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing {tipo_loteria} {concurso}: {e}")
                erros += 1
                continue
        
        # Commit all changes
        conn.commit()
        logger.info(f"🎉 COMPLETED! Updated: {atualizados}, Errors: {erros}")
        
        # Show some updated records
        logger.info("📊 Sample of updated records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tipo_loteria, concurso, valor_acumulado 
                FROM resultados_sorteados 
                WHERE acumulou = true AND valor_acumulado > 0
                ORDER BY data_importacao DESC 
                LIMIT 10
            """)
            for record in cur.fetchall():
                logger.info(f"   {record[0]} #{record[1]}: R$ {record[2]:,.2f}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    logger.info("🚀 Starting accumulated values update...")
    atualizar_valores_acumulados()
    logger.info("✅ Update process completed!")