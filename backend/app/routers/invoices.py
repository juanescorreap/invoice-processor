"""
Router de Invoices - API REST endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Optional, List
import asyncio
import tempfile
import os
from pathlib import Path

from app.services.processing_service import ProcessingService
from app.services.database_service import DatabaseService
from app.models import Invoice, PaginationParams, InvoiceFilters, ProcessingStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/process", status_code=201)
async def process_invoice(
    file: UploadFile = File(..., description="PDF o imagen de factura")
):
    """
    Subir y procesar factura
    
    - Sube un archivo PDF o imagen
    - Lo procesa automáticamente (OCR → NER → Database)
    - Retorna el resultado
    """
    logger.info(f"📥 Recibiendo archivo: {file.filename}")
    
    # Validar tipo de archivo
    if not file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no soportado. Use PDF, JPG o PNG"
        )
    
    # Guardar archivo temporal
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Guardar archivo
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"📁 Archivo guardado: {temp_path}")
        
        # Procesar
        processor = ProcessingService()
        result = await processor.process_file(
            file_path=temp_path,
            file_id=None,
            source="api_upload"
        )
        
        # Limpiar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass
        
        if result['success']:
            return {
                "success": True,
                "message": "Factura procesada exitosamente",
                "invoice_id": result['invoice_id'],
                "processing_time": result['processing_time'],
                "steps": result['steps']
            }
        else:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Error procesando factura",
                    "errors": result['errors'],
                    "steps": result['steps']
                }
            )
    
    except Exception as e:
        # Limpiar archivo temporal
        try:
            os.remove(temp_path)
        except:
            pass
        
        logger.error(f"Error procesando archivo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ProcessingStatus] = None,
    vendor_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Listar facturas con paginación y filtros
    """
    try:
        db = DatabaseService()
        
        # Query base
        query = db.client.table('invoices')\
            .select('*, vendors(name, nit)', count='exact')
        
        # Aplicar filtros
        if status:
            query = query.eq('processing_status', status)
        
        if vendor_id:
            query = query.eq('vendor_id', vendor_id)
        
        if date_from:
            query = query.gte('invoice_date', date_from)
        
        if date_to:
            query = query.lte('invoice_date', date_to)
        
        # Paginación
        offset = (page - 1) * page_size
        query = query.order('created_at', desc=True)\
            .range(offset, offset + page_size - 1)
        
        result = query.execute()
        
        return {
            "items": result.data,
            "total": result.count,
            "page": page,
            "page_size": page_size,
            "pages": (result.count + page_size - 1) // page_size
        }
    
    except Exception as e:
        logger.error(f"Error listando facturas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str):
    """
    Obtener detalle de factura con items
    """
    try:
        db = DatabaseService()
        
        # Obtener invoice
        invoice_result = db.client.table('invoices')\
            .select('*, vendors(name, nit), stores(name, code)')\
            .eq('id', invoice_id)\
            .execute()
        
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Obtener items
        items_result = db.client.table('invoice_items')\
            .select('*, products(master_name, master_sku)')\
            .eq('invoice_id', invoice_id)\
            .order('line_number')\
            .execute()
        
        invoice['items'] = items_result.data
        
        return invoice
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo factura: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    