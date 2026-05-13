#!/usr/bin/env python3
"""
Load Product Catalog from Excel
"""
import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database_service import DatabaseService

def load_catalog_from_excel(excel_path: str):
    """Carga catálogo desde Excel a tabla products"""
    db = DatabaseService()
    
    # Leer Excel
    df = pd.read_excel(excel_path)
    
    print(f"📊 Cargando {len(df)} productos...")
    
    for idx, row in df.iterrows():
        # Ajustar nombres de columnas según tu Excel
        db.client.table('products').upsert({
            'master_sku': row['SKU'],  # Ajustar nombre columna
            'master_name': row['Product Name'],  # Ajustar
            'category': row.get('Category'),
            'unit': row.get('Unit')
        }, on_conflict='master_sku').execute()
    
    print(f"✅ {len(df)} productos cargados")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: python load_product_catalog.py <ruta_excel>")
        sys.exit(1)
    
    load_catalog_from_excel(sys.argv[1])