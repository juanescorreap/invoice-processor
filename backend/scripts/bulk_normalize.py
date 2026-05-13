#!/usr/bin/env python3
"""
Bulk Normalization Script
Procesa archivos CSV y crea normalizaciones automáticas
"""
import sys
import os
import csv
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalization_service import ProductNormalizationService
from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BulkNormalizer:
    """Normalización masiva de productos, vendors y stores"""
    
    def __init__(self):
        self.service = ProductNormalizationService()
        self.db = DatabaseService()
        
    def process_product_catalog(
        self,
        csv_path: str,
        vendor_name: str,
        auto_approve_threshold: float = 90.0
    ):
        """
        Procesa un catálogo de productos CSV
        
        Args:
            csv_path: Ruta al archivo CSV
            vendor_name: Nombre del vendor
            auto_approve_threshold: Score para auto-aprobar
        """
        logger.info(f"📂 Procesando: {csv_path}")
        logger.info(f"   Vendor: {vendor_name}")
        
        # Leer CSV
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"   ✅ {len(df)} filas leídas")
            logger.info(f"   📋 Columnas: {list(df.columns)}")  #

        except Exception as e:
            logger.error(f"   ❌ Error leyendo CSV: {e}")
            return
        
        # Validar columnas
        # Validar columnas
        # Validar columnas - soportar múltiples formatos
        logger.info(f"   📋 Columnas detectadas: {list(df.columns[:5])}")
        
        code_col = None
        item_col = None
        
        # Formato 1: Code + Item (Products Database)
        for col in df.columns:
            col_clean = col.strip().lower()
            if col_clean == 'code':
                code_col = col
            elif col_clean == 'item':
                item_col = col
        
        # Formato 2: Items + Description (Product Sheet)
        if not code_col or not item_col:
            for col in df.columns:
                col_clean = col.strip().lower()
                if col_clean == 'items':
                    code_col = col
                elif col_clean == 'description':
                    item_col = col
        
        if not code_col or not item_col:
            logger.error(f"   ❌ No se encontraron columnas de producto")
            logger.error(f"      Columnas: {list(df.columns)}")
            return
        
        logger.info(f"   ✅ Formato detectado: Code='{code_col}', Item='{item_col}'")
        
        # Obtener productos únicos
        products = df[[code_col, item_col]].drop_duplicates()
        
        # Obtener productos únicos
        products = df[[code_col, item_col]].drop_duplicates()
        logger.info(f"   📦 {len(products)} productos únicos")
        
        # Estadísticas
        created = 0
        mapped = 0
        skipped = 0
        
        # Procesar cada producto
        # Procesar cada producto
        for idx, row in products.iterrows():
            code = str(row[code_col]).strip()
            name = str(row[item_col]).strip()
            
            if not name or name == 'nan':
                skipped += 1
                continue
            
            # Buscar similares en DB
            similar = self.service.find_similar_products(
                product_name=name,
                limit=3
            )
            
            if similar and similar[0]['similarity_score'] >= auto_approve_threshold:
                # Ya existe similar - solo loguear
                logger.info(f"      ⚠️  '{name}' similar a '{similar[0]['product_name']}' ({similar[0]['similarity_score']}%)")
                skipped += 1
            else:
                # Crear producto normalizado
                normalized_id = self.service.create_normalized_product(
                    normalized_name=name,
                    normalized_code=code,
                    category=vendor_name,
                    description=f"From {vendor_name} catalog"
                )
                
                if normalized_id:
                    # Crear mapeo auto-aprobado
                    self.service.create_product_mapping(
                        variant_name=name,
                        normalized_product_id=normalized_id,
                        similarity_score=100.0,
                        status='approved'
                    )
                    created += 1
                    
                    if (created + skipped) % 50 == 0:
                        logger.info(f"      ... procesados {created + skipped}/{len(products)}")
        
        logger.info(f"   ✅ Completado:")
        logger.info(f"      - Creados: {created}")
        logger.info(f"      - Mapeados: {mapped}")
        logger.info(f"      - Omitidos: {skipped}")
        print()
    
    def process_all_catalogs(self, catalog_dir: str):
        """Procesa todos los catálogos en un directorio"""
        catalog_path = Path(catalog_dir)
        
        if not catalog_path.exists():
            logger.error(f"❌ Directorio no existe: {catalog_dir}")
            return
        
        # Mapeo de archivos a vendors
        vendor_mapping = {
            'Bindi': 'Bindi',
            'Bridor': 'Bridor',
        }
        
        csv_files = list(catalog_path.glob('*.csv'))
        logger.info(f"📁 Encontrados {len(csv_files)} archivos CSV")
        print()
        
        for csv_file in csv_files:
            # Detectar vendor del nombre del archivo
            vendor = None
            for key, value in vendor_mapping.items():
                if key.lower() in csv_file.name.lower():
                    vendor = value
                    break
            
            if not vendor:
                logger.warning(f"⚠️  No se pudo detectar vendor: {csv_file.name}")
                vendor = "Unknown"
            
            self.process_product_catalog(
                csv_path=str(csv_file),
                vendor_name=vendor,
                auto_approve_threshold=90.0
            )
    
    def normalize_existing_vendors(self):
        """Normaliza vendors existentes en la DB"""
        logger.info("=" * 70)
        logger.info("🏢 NORMALIZANDO VENDORS DUPLICADOS")
        logger.info("=" * 70)
        print()
        
        # Obtener todos los vendors
        result = self.db.client.table('vendors').select('id, name, nit').execute()
        
        if not result.data:
            logger.info("   ❌ No hay vendors en la DB")
            return
        
        logger.info(f"   📊 Total vendors en DB: {len(result.data)}")
        print()
        
        # Agrupar por nombre similar
        vendor_groups = {}
        for vendor in result.data:
            name = vendor['name']
            nit = vendor.get('nit', 'UNKNOWN')
            
            # Buscar grupo existente
            matched_group = None
            for group_name in vendor_groups.keys():
                score = self.service.calculate_similarity(name, group_name)
                if score >= 85:
                    matched_group = group_name
                    break
            
            if matched_group:
                vendor_groups[matched_group].append({
                    'id': vendor['id'],
                    'name': name,
                    'nit': nit
                })
            else:
                vendor_groups[name] = [{
                    'id': vendor['id'],
                    'name': name,
                    'nit': nit
                }]
        
        logger.info(f"   🔗 Grupos detectados: {len(vendor_groups)}")
        print()
        
        # Procesar grupos con duplicados
        duplicates_found = 0
        
        for group_name, vendors in vendor_groups.items():
            if len(vendors) > 1:
                duplicates_found += 1
                
                logger.info(f"   🔴 DUPLICADOS ENCONTRADOS:")
                logger.info(f"      Nombre base: '{group_name}'")
                logger.info(f"      Cantidad: {len(vendors)} vendors")
                
                for v in vendors:
                    logger.info(f"         - {v['name']} (NIT: {v['nit']}) [ID: {v['id'][:8]}...]")
                
                # Verificar si ya existe vendor normalizado
                existing = self.db.client.table('normalized_vendors').select('id').eq(
                    'normalized_name', group_name
                ).execute()
                
                if existing.data and len(existing.data) > 0:
                    normalized_id = existing.data[0]['id']
                    logger.info(f"      ♻️  Vendor normalizado ya existe: {normalized_id[:8]}...")
                else:
                    # Crear nuevo vendor normalizado
                    logger.info(f"      ➕ Creando vendor normalizado...")
                    normalized_id = self.service.create_normalized_vendor(
                        normalized_name=group_name,
                        category="Auto-detected duplicate"
                    )
                    
                    if normalized_id:
                        logger.info(f"      ✅ Vendor normalizado creado: {normalized_id[:8]}...")
                    else:
                        logger.error(f"      ❌ Error creando vendor normalizado")
                        continue
                
                # Crear mapeos
                for v in vendors:
                    # Verificar si ya existe mapeo
                    existing_mapping = self.db.client.table('vendor_name_mappings').select('id').eq(
                        'variant_name', v['name']
                    ).eq('variant_nit', v['nit']).execute()
                    
                    if existing_mapping.data and len(existing_mapping.data) > 0:
                        logger.info(f"         ⚠️  Mapeo ya existe: {v['name']} (NIT: {v['nit']})")
                    else:
                        success = self.service.create_vendor_mapping(
                            variant_name=v['name'],
                            variant_nit=v['nit'],
                            normalized_vendor_id=normalized_id,
                            similarity_score=100.0,
                            status='pending'
                        )
                        
                        if success:
                            logger.info(f"         ✅ Mapeo creado: {v['name']} → normalizado")
                        else:
                            logger.error(f"         ❌ Error: {v['name']}")
                
                print()
        
        logger.info("=" * 70)
        logger.info(f"   ✅ RESUMEN:")
        logger.info(f"      Total vendors: {len(result.data)}")
        logger.info(f"      Grupos únicos: {len(vendor_groups)}")
        logger.info(f"      Duplicados: {duplicates_found}")
        logger.info("=" * 70)

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bulk normalization script')
    parser.add_argument('--products', type=str, help='Directory with product CSVs')
    parser.add_argument('--vendors', action='store_true', help='Normalize existing vendors')
    parser.add_argument('--all', action='store_true', help='Run all normalizations')
    
    args = parser.parse_args()
    
    normalizer = BulkNormalizer()
    
    if args.all or args.vendors:
        normalizer.normalize_existing_vendors()
    
    if args.all or args.products:
        catalog_dir = args.products or '/mnt/user-data/uploads'
        normalizer.process_all_catalogs(catalog_dir)
    
    if not any([args.products, args.vendors, args.all]):
        parser.print_help()


if __name__ == '__main__':
    main()