#!/usr/bin/env python3
"""
Migrate Manufacturers Script
Re-procesa todos los invoice_items existentes para extraer manufacturers
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.manufacturer_extraction_service import get_manufacturer_service
from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_all_invoice_items():
    """
    Migra todos los invoice_items existentes
    """
    logger.info("=" * 70)
    logger.info("🔄 MIGRANDO MANUFACTURERS DE INVOICE_ITEMS")
    logger.info("=" * 70)
    print()
    
    service = get_manufacturer_service()
    db = DatabaseService()
    
    # Obtener todos los invoice_items
    result = db.client.table('invoice_items').select(
        'id, vendor_product_name'
    ).execute()
    
    if not result.data:
        logger.info("❌ No hay invoice_items en la base de datos")
        return
    
    total = len(result.data)
    logger.info(f"📊 Total invoice_items: {total}")
    print()
    
    # Estadísticas
    processed = 0
    with_manufacturer = 0
    without_manufacturer = 0
    errors = 0
    
    # Procesar cada item
    for idx, item in enumerate(result.data, 1):
        try:
            extraction = service.extract_manufacturer(item['vendor_product_name'])
            
            # Obtener o crear manufacturer
            manufacturer_id = None
            if extraction['manufacturer_name']:
                manufacturer_id = service.get_or_create_manufacturer(
                    extraction['manufacturer_name']
                )
                if manufacturer_id:
                    with_manufacturer += 1
                else:
                    without_manufacturer += 1
            else:
                without_manufacturer += 1
            
            # Actualizar item
            db.client.table('invoice_items').update({
                'manufacturer_id': manufacturer_id,
                'manufacturer_prefix': extraction['manufacturer_prefix'],
                'product_name_clean': extraction['product_name_clean']
            }).eq('id', item['id']).execute()
            
            processed += 1
            
            # Log progreso cada 50 items
            if processed % 50 == 0:
                logger.info(f"   ... procesados {processed}/{total}")
                
        except Exception as e:
            logger.error(f"   ❌ Error procesando item {item['id']}: {e}")
            errors += 1
    
    print()
    logger.info("=" * 70)
    logger.info("✅ MIGRACIÓN COMPLETADA:")
    logger.info(f"   Total procesados: {processed}")
    logger.info(f"   Con manufacturer: {with_manufacturer}")
    logger.info(f"   Sin manufacturer: {without_manufacturer}")
    logger.info(f"   Errores: {errors}")
    logger.info("=" * 70)
    print()
    
    # Mostrar manufacturers creados
    manufacturers = db.client.table('manufacturers').select(
        'name'
    ).order('name').execute()
    
    logger.info(f"📦 Manufacturers en DB: {len(manufacturers.data)}")
    for mfr in manufacturers.data:
        logger.info(f"   - {mfr['name']}")


if __name__ == '__main__':
    migrate_all_invoice_items()