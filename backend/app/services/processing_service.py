"""
Processing Service - Orquestador principal del pipeline
"""
import asyncio
import time
from typing import Optional, Dict, Any
from pathlib import Path
from uuid import UUID

from app.services.ocr_service import get_ocr_service
from app.services.ner_service import get_ner_service
from app.services.database_service import DatabaseService
from app.models import ProcessingStatus
from app.utils.logger import get_logger
from app.utils.errors import OCRError, NERError, DatabaseError, FileError

logger = get_logger(__name__)


class ProcessingService:
    """
    Orquestador principal: OCR → NER → Validación → Database
    """
    
    def __init__(self):
        """Inicializar servicios"""
        self.ocr_service = get_ocr_service()
        self.ner_service = get_ner_service()
        self.db_service = DatabaseService()

    async def process_file(
        self,
        file_path: str,
        file_id: Optional[str] = None,
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        Procesar archivo completo: OCR → NER → Database
        
        Args:
            file_path: Ruta al archivo PDF/imagen
            file_id: ID del archivo (ej: Google Drive ID)
            source: Origen del archivo (manual, gdrive, email)
            
        Returns:
            Dict con resultado del procesamiento
        """
        start_time = time.time()
        result = {
            'success': False,
            'file_path': file_path,
            'file_id': file_id,
            'invoice_id': None,
            'errors': [],
            'processing_time': 0,
            'steps': {}
        }
        
        try:
            logger.info(f"{'='*60}")
            logger.info(f"Procesando archivo: {file_path}")
            logger.info(f"{'='*60}")
            
            # Validar que el archivo existe
            if not Path(file_path).exists():
                raise FileError(f"Archivo no encontrado: {file_path}")
            
            # PASO 1: OCR
            logger.info("PASO 1/4: OCR - Extrayendo texto...")
            ocr_start = time.time()
            try:
                ocr_response = await self.ocr_service.process_invoice(file_path)
                result['steps']['ocr'] = {
                    'success': True,
                    'confidence': ocr_response.confidence,
                    'text_length': len(ocr_response.text),
                    'time': time.time() - ocr_start
                }
                logger.info(f"✅ OCR completado: {len(ocr_response.text)} caracteres, confidence={ocr_response.confidence:.2%}")
            except OCRError as e:
                result['errors'].append(f"OCR falló: {str(e)}")
                result['steps']['ocr'] = {'success': False, 'error': str(e)}
                raise
            
            # PASO 2: NER
            logger.info("PASO 2/4: NER - Estructurando datos...")
            ner_start = time.time()
            try:
                ner_response = await self.ner_service.extract_entities(ocr_response.text)
                result['steps']['ner'] = {
                    'success': True,
                    'confidence': ner_response.confidence,
                    'items_count': len(ner_response.items),
                    'time': time.time() - ner_start
                }
                logger.info(f"✅ NER completado: {ner_response.vendor.name}, ${ner_response.total:,.2f}, {len(ner_response.items)} items")
            except NERError as e:
                result['errors'].append(f"NER falló: {str(e)}")
                result['steps']['ner'] = {'success': False, 'error': str(e)}
                raise
            
            # PASO 3: Validación
            logger.info("PASO 3/4: Validación...")
            validation_start = time.time()
            validation_errors = self._validate_ner_response(ner_response)
            
            if validation_errors:
                logger.warning(f"⚠️  Validación con {len(validation_errors)} advertencias:")
                for err in validation_errors:
                    logger.warning(f"   - {err}")
                result['steps']['validation'] = {
                    'success': True,
                    'warnings': validation_errors,
                    'time': time.time() - validation_start
                }
            else:
                logger.info("✅ Validación OK")
                result['steps']['validation'] = {
                    'success': True,
                    'warnings': [],
                    'time': time.time() - validation_start
                }
            
            # PASO 4: Database
            logger.info("PASO 4/4: Guardando en base de datos...")
            db_start = time.time()
            try:
                invoice_id = self.db_service.create_invoice_from_ner(
                    ner_response=ner_response,
                    source_file_path=file_path,
                    source_file_id=file_id,
                    raw_ocr_text=ocr_response.text
                )
                result['invoice_id'] = str(invoice_id)
                result['steps']['database'] = {
                    'success': True,
                    'invoice_id': str(invoice_id),
                    'time': time.time() - db_start
                }
                logger.info(f"✅ Invoice guardada: {invoice_id}")
            except DatabaseError as e:
                result['errors'].append(f"Database falló: {str(e)}")
                result['steps']['database'] = {'success': False, 'error': str(e)}
                raise
            
            # SUCCESS
            result['success'] = True
            result['processing_time'] = time.time() - start_time
            
            logger.info(f"{'='*60}")
            logger.info(f"✅ Procesamiento exitoso en {result['processing_time']:.2f}s")
            logger.info(f"   Invoice ID: {invoice_id}")
            logger.info(f"{'='*60}")
            
            return result
            
        except Exception as e:
            result['success'] = False
            result['processing_time'] = time.time() - start_time
            result['errors'].append(str(e))
            
            logger.error(f"{'='*60}")
            logger.error(f"❌ Procesamiento falló: {str(e)}")
            logger.error(f"{'='*60}")
            
            return result
        
    def _validate_ner_response(self, ner_response) -> list:
        """
        Validar respuesta NER contra reglas de negocio
        
        Returns:
            Lista de errores/advertencias
        """
        errors = []
        
        # Validar campos obligatorios
        if not ner_response.vendor.name:
            errors.append("Vendor sin nombre")
        
        if not ner_response.vendor.nit:
            errors.append("Vendor sin NIT")
        
        if not ner_response.invoice_number:
            errors.append("Sin número de factura")
        
        if not ner_response.items or len(ner_response.items) == 0:
            errors.append("Factura sin items")
        
        if ner_response.total <= 0:
            errors.append("Total inválido")
        
        # Validar suma de items
        items_sum = sum(item.line_total for item in ner_response.items)
        diff_percent = abs(items_sum - ner_response.total) / ner_response.total
        
        if diff_percent > 0.01:  # 1% diferencia
            errors.append(f"Suma items ({items_sum}) != Total ({ner_response.total})")
        
        return errors