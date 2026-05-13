#!/usr/bin/env python3
"""
Map Invoice Items to Product Catalog
Usa fuzzy matching para conectar nombres de facturas → productos maestros
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalization_service import ProductNormalizationService
from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def map_invoice_items_to_catalog():
    """
    Mapea invoice_items a products usando fuzzy matching
    """
    print("=" * 70)
    print("🔗 MAPEANDO INVOICE ITEMS → PRODUCT CATALOG")
    print("=" * 70)
    print()
    
    service = ProductNormalizationService()
    db = DatabaseService()
    
    # Obtener todos los productos maestros
    products = db.client.table('products').select(
        'id, master_name, master_sku'
    ).execute()
    
    if not products.data:
        print("❌ No hay productos en el catálogo maestro")
        return
    
    print(f"📦 Productos en catálogo: {len(products.data)}")
    
    # Obtener invoice_items sin mapear
    items = db.client.table('invoice_items').select(
        'id, product_name_clean, vendor_product_name'
    ).is_('product_id', 'null').execute()
    
    if not items.data:
        print("✅ Todos los items ya están mapeados")
        return
    
    print(f"📋 Items sin mapear: {len(items.data)}")
    print()
    
    # Estadísticas
    mapped = 0
    not_mapped = 0
    
    # Procesar cada item
    for idx, item in enumerate(items.data, 1):
        # Usar nombre limpio si existe, sino el original
        product_name = item.get('product_name_clean') or item['vendor_product_name']
        
        if not product_name or product_name == 'NULL':
            not_mapped += 1
            continue
        
        # Buscar mejor match en catálogo
        best_match = None
        best_score = 0
        
        for product in products.data:
            score = service.calculate_similarity(
                product_name,
                product['master_name']
            )
            
            if score > best_score:
                best_score = score
                best_match = product
        
        # Mapear si score >= 80%
        if best_match and best_score >= 80:
            db.client.table('invoice_items').update({
                'product_id': best_match['id']
            }).eq('id', item['id']).execute()
            
            mapped += 1
            
            if mapped % 10 == 0:
                print(f"   ... mapeados {mapped}/{len(items.data)}")
        else:
            not_mapped += 1
            
            # Log productos sin match para revisión
            if best_score < 80 and best_score > 0:
                print(f"   ⚠️  Score bajo ({best_score:.0f}%): '{product_name[:50]}' → '{best_match['master_name'][:50] if best_match else 'N/A'}'")
    
    print()
    print("=" * 70)
    print("✅ MAPEO COMPLETADO:")
    print(f"   Items mapeados: {mapped}")
    print(f"   Items sin mapeo: {not_mapped}")
    print(f"   Threshold usado: 80%")
    print("=" * 70)


if __name__ == '__main__':
    map_invoice_items_to_catalog()