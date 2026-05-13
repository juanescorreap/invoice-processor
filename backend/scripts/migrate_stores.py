#!/usr/bin/env python3
"""
Migrate Stores from structured_data to stores table
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalization_service import ProductNormalizationService
from app.services.database_service import DatabaseService

def migrate_stores():
    """
    Extrae stores de structured_data y los mapea a la tabla stores
    """
    print("=" * 70)
    print("🏪 MIGRANDO STORES DE STRUCTURED_DATA")
    print("=" * 70)
    print()
    
    service = ProductNormalizationService()
    db = DatabaseService()
    
    # Obtener invoices sin store_id pero con structured_data
    invoices = db.client.table('invoices').select(
        'id, invoice_number, structured_data'
    ).is_('store_id', 'null').execute()
    
    if not invoices.data:
        print("✅ Todos los invoices ya tienen store_id")
        return
    
    print(f"📊 Invoices sin store_id: {len(invoices.data)}")
    print()
    
    # Estadísticas
    migrated = 0
    no_store_data = 0
    
    for inv in invoices.data:
        structured = inv.get('structured_data')
        
        if not structured or 'store' not in structured:
            no_store_data += 1
            continue
        
        store_data = structured['store']
        store_name = store_data.get('name')
        
        if not store_name:
            no_store_data += 1
            continue
        
        # Buscar store existente con fuzzy matching
        existing_stores = db.client.table('stores').select('id, name, code').execute()
        
        best_match = None
        best_score = 0
        
        for store in existing_stores.data:
            score = service.calculate_similarity(store_name, store['name'])
            if score > best_score:
                best_score = score
                best_match = store
        
        store_id = None
        
        # Si hay match >= 80%, usar ese store
        if best_match and best_score >= 80:
            store_id = best_match['id']
            print(f"   ✅ Match: '{store_name}' → '{best_match['name']}' ({best_score:.0f}%)")
        else:
            # Crear nuevo store con código único
            code_base = store_name[:10].upper().replace(' ', '_').replace('-', '_')
            
            # Verificar si código existe y agregar sufijo si es necesario
            code = code_base
            counter = 1
            while True:
                existing_code = db.client.table('stores').select('id').eq('code', code).execute()
                if not existing_code.data:
                    break
                code = f"{code_base}_{counter}"
                counter += 1
            
            result = db.client.table('stores').insert({
                'name': store_name,
                'address': store_data.get('address'),
                'code': code
            }).execute()
            
            if result.data:
                store_id = result.data[0]['id']
                print(f"   ➕ Creado: '{store_name}' (code: {code})")
        
        # Actualizar invoice
        if store_id:
            db.client.table('invoices').update({
                'store_id': store_id
            }).eq('id', inv['id']).execute()
            
            migrated += 1
    
    print()
    print("=" * 70)
    print(f"✅ MIGRACIÓN COMPLETADA:")
    print(f"   Invoices migrados: {migrated}")
    print(f"   Sin datos de store: {no_store_data}")
    print("=" * 70)

if __name__ == '__main__':
    migrate_stores()