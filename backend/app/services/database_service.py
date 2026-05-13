"""
Database Service - Interacción con Supabase
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from supabase import create_client, Client
from datetime import datetime

from app.config import settings
from app.models import (
    NERResponse, Vendor, Store, Product, Invoice, InvoiceItem,
    VendorCreate, StoreCreate, ProductCreate, InvoiceCreate, InvoiceItemCreate
)
from app.utils.logger import get_logger
from app.utils.errors import DatabaseError

logger = get_logger(__name__)


class DatabaseService:
    """
    Servicio para operaciones de base de datos en Supabase
    """
    
    def __init__(self):
        """Inicializar cliente Supabase"""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY  # Usamos service key para admin access
        )
        logger.info("DatabaseService inicializado")

    def get_or_create_vendor(self, ner_vendor) -> UUID:
            """
            Buscar vendor por NIT o crearlo si no existe
            
            Args:
                ner_vendor: VendorExtracted del NER
                
            Returns:
                UUID del vendor
            """
            try:
                # Buscar por NIT
                result = self.client.table('vendors')\
                    .select('id')\
                    .eq('nit', ner_vendor.nit)\
                    .execute()
                
                if result.data and len(result.data) > 0:
                    vendor_id = result.data[0]['id']
                    logger.info(f"Vendor encontrado: {ner_vendor.nit} -> {vendor_id}")
                    return vendor_id
                
                # Si no existe, crear
                logger.info(f"Creando nuevo vendor: {ner_vendor.name}")
                insert_result = self.client.table('vendors').insert({
                    'name': ner_vendor.name,
                    'nit': ner_vendor.nit,
                    'address': ner_vendor.address,
                    'phone': ner_vendor.phone,
                }).execute()
                
                vendor_id = insert_result.data[0]['id']
                logger.info(f"Vendor creado: {vendor_id}")
                return vendor_id
                
            except Exception as e:
                logger.error(f"Error en get_or_create_vendor: {e}")
                raise DatabaseError(f"Error buscando/creando vendor: {str(e)}")
            
    def get_or_create_store(self, ner_store, default_code: str = None) -> Optional[UUID]:
        """
        Buscar store por nombre o crear con código default
        
        Args:
            ner_store: StoreExtracted del NER
            default_code: Código a usar si se crea nuevo store
            
        Returns:
            UUID del store o None si no se puede determinar
        """
        if not ner_store.name:
            logger.warning("No hay nombre de tienda en NER")
            return None
        
        try:
            # Buscar por nombre (coincidencia aproximada)
            result = self.client.table('stores')\
                .select('id, code')\
                .ilike('name', f'%{ner_store.name}%')\
                .execute()
            
            if result.data and len(result.data) > 0:
                store_id = result.data[0]['id']
                logger.info(f"Store encontrado: {ner_store.name} -> {store_id}")
                return store_id
            
            # Si no existe y no hay código, no crear
            if not default_code:
                logger.warning(f"Store no encontrado y sin código: {ner_store.name}")
                return None
            
            # Crear nuevo store
            logger.info(f"Creando nuevo store: {ner_store.name}")
            insert_result = self.client.table('stores').insert({
                'name': ner_store.name,
                'code': default_code,
                'address': ner_store.address,
            }).execute()
            
            store_id = insert_result.data[0]['id']
            logger.info(f"Store creado: {store_id}")
            return store_id
            
        except Exception as e:
            logger.error(f"Error en get_or_create_store: {e}")
            return None
        
    def create_invoice_from_ner(
        self,
        ner_response: NERResponse,
        source_file_path: str,
        source_file_id: str = None,
        raw_ocr_text: str = None
    ) -> UUID:
        """
        Crear invoice completa con items a partir de NER
        
        Args:
            ner_response: Respuesta del NER
            source_file_path: Ruta del archivo original
            source_file_id: ID del archivo (ej: Google Drive ID)
            raw_ocr_text: Texto OCR original
            
        Returns:
            UUID de la invoice creada
        """
        try:
            logger.info(f"Creando invoice: {ner_response.invoice_number}")
            
            # 1. Obtener vendor_id
            vendor_id = self.get_or_create_vendor(ner_response.vendor)
            
            # 2. Obtener store_id
            store_id = self.get_or_create_store(ner_response.store)
            
            # 3. Crear invoice
            invoice_data = {
                'invoice_number': ner_response.invoice_number,
                'vendor_id': str(vendor_id),
                'store_id': str(store_id) if store_id else None,
                'invoice_date': ner_response.invoice_date.isoformat(),
                'due_date': ner_response.due_date.isoformat() if ner_response.due_date else None,
                'subtotal': float(ner_response.subtotal) if ner_response.subtotal else None,
                'tax': float(ner_response.tax) if ner_response.tax else None,
                'total': float(ner_response.total),
                'source_file_path': source_file_path,
                'source_file_id': source_file_id,
                'confidence_score': float(ner_response.confidence),
                'processing_status': 'processed',
                'raw_ocr_text': raw_ocr_text,
                'structured_data': {
                    'vendor': ner_response.vendor.dict(),
                    'store': ner_response.store.dict() if ner_response.store else None,
                    'items': [item.dict() for item in ner_response.items]
                }
            }
            
            try:
                invoice_result = self.client.table('invoices').insert(invoice_data).execute()
                invoice_id = invoice_result.data[0]['id']
                logger.info(f"Invoice creada: {invoice_id}")
            except Exception as e:
                # Si es duplicado, buscar la existente
                if 'duplicate key' in str(e) or '23505' in str(e):
                    logger.warning(f"Invoice duplicada: {ner_response.invoice_number}")
                    
                    # Buscar invoice existente
                    existing = self.client.table('invoices')\
                        .select('id')\
                        .eq('vendor_id', str(vendor_id))\
                        .eq('invoice_number', ner_response.invoice_number)\
                        .execute()
                    
                    if existing.data and len(existing.data) > 0:
                        invoice_id = existing.data[0]['id']
                        logger.info(f"Retornando invoice existente: {invoice_id}")
                        return invoice_id
                    else:
                        raise
                else:
                    raise
            
            # 4. Crear items
            for idx, item in enumerate(ner_response.items, 1):
                item_data = {
                    'invoice_id': invoice_id,
                    'vendor_product_name': item.product_name,
                    'vendor_sku': item.sku,
                    'quantity': float(item.quantity),
                    'unit_price': float(item.unit_price),
                    'line_total': float(item.line_total),
                    'line_number': idx,
                    'matched': False
                }
                
                result = self.client.table('invoice_items').insert(item_data).execute()
                item_id = result.data[0]['id']
                
                # AGREGAR ESTO: Extraer manufacturer
                try:
                    from app.services.manufacturer_extraction_service import get_manufacturer_service
                    mfr_service = get_manufacturer_service()
                    mfr_service.process_invoice_item(item_id, item.product_name)
                except Exception as e:
                    logger.warning(f"No se pudo extraer manufacturer: {e}")
            
            logger.info(f"✅ Invoice {invoice_id} creada con {len(ner_response.items)} items")
            return invoice_id
            
        except Exception as e:
            logger.error(f"Error creando invoice: {e}", exc_info=True)
            raise DatabaseError(f"Error creando invoice: {str(e)}")