"""
Servicio NER (Named Entity Recognition) usando Claude API
"""
import json
import asyncio
import time
from typing import Optional
import anthropic
from anthropic import AsyncAnthropic

from app.config import settings, CLAUDE_NER_SYSTEM_PROMPT, INVOICE_JSON_SCHEMA
from app.models import NERResponse, VendorExtracted, StoreExtracted, ItemExtracted
from app.utils.logger import get_logger
from app.utils.errors import NERError

logger = get_logger(__name__)


class NERService:
    """
    Servicio para estructuración de datos de facturas mediante Claude
    """
    
    def __init__(self):
        """Inicializar cliente Anthropic"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL_TEXT
        self.max_retries = settings.CLAUDE_RETRY_MAX_ATTEMPTS
        self.retry_delay = settings.CLAUDE_RETRY_DELAY_SECONDS
    
    async def extract_entities(
        self,
        ocr_text: str,
        timeout: Optional[int] = None
    ) -> NERResponse:
        """
        Extraer entidades estructuradas del texto OCR
        
        Args:
            ocr_text: Texto extraído por OCR
            timeout: Timeout en segundos (default: desde config)
            
        Returns:
            NERResponse con datos estructurados
            
        Raises:
            NERError: Si falla la extracción
        """
        start_time = time.time()
        timeout = timeout or settings.NER_TIMEOUT_SECONDS
        
        logger.info(f"Iniciando NER para texto de {len(ocr_text)} caracteres")
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            raise NERError("Texto OCR vacío o demasiado corto")
        
        try:
            # Llamar a Claude con structured outputs
            structured_data = await self._call_claude_ner(
                ocr_text=ocr_text,
                timeout=timeout
            )
            
            # Validar y parsear respuesta
            ner_response = self._parse_structured_data(structured_data)
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"NER completado: {len(ner_response.items)} items, "
                f"confidence={ner_response.confidence:.4f}, "
                f"tiempo={processing_time:.2f}s"
            )
            
            return ner_response
            
        except asyncio.TimeoutError:
            raise NERError(f"NER timeout después de {timeout}s")
        
        except anthropic.APIError as e:
            logger.error(f"Error en Claude API: {e}")
            raise NERError(f"Error en Claude API: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error inesperado en NER: {e}", exc_info=True)
            raise NERError(f"Error procesando NER: {str(e)}")
    
    async def _call_claude_ner(
        self,
        ocr_text: str,
        timeout: int
    ) -> dict:
        """
        Llamar a Claude API con structured outputs
        
        Returns:
            Dict con datos estructurados
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Claude NER API - Intento {attempt}/{self.max_retries}")
                
                # Construir prompt con instrucciones específicas
                user_prompt = self._build_user_prompt(ocr_text)
                
                # Llamar a Claude con tool use (structured outputs)
                message = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=settings.CLAUDE_MAX_TOKENS,
                        temperature=settings.CLAUDE_TEMPERATURE,
                        system=CLAUDE_NER_SYSTEM_PROMPT,
                        messages=[
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ],
                        tools=[
                            {
                                "name": "extract_invoice_data",
                                "description": "Extrae y estructura los datos de una factura",
                                "input_schema": INVOICE_JSON_SCHEMA
                            }
                        ],
                        tool_choice={"type": "tool", "name": "extract_invoice_data"}
                    ),
                    timeout=timeout
                )
                
                # Extraer datos estructurados del tool use
                structured_data = self._extract_tool_use_data(message)
                
                if not structured_data:
                    raise NERError("No se pudo extraer datos estructurados")
                
                return structured_data
                
            except asyncio.TimeoutError:
                last_error = f"Timeout en intento {attempt}"
                logger.warning(last_error)
                
            except anthropic.RateLimitError:
                last_error = f"Rate limit en intento {attempt}"
                logger.warning(last_error)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                    
            except anthropic.APIError as e:
                last_error = f"API error en intento {attempt}: {str(e)}"
                logger.warning(last_error)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                    
            except Exception as e:
                last_error = f"Error inesperado en intento {attempt}: {str(e)}"
                logger.error(last_error, exc_info=True)
                break
        
        raise NERError(f"NER falló después de {self.max_retries} intentos. Último error: {last_error}")
    
    def _build_user_prompt(self, ocr_text: str) -> str:
        """
        Construir prompt para Claude con el texto OCR
        """
        return f"""Analiza la siguiente factura y extrae la información estructurada.

TEXTO DE LA FACTURA:
---
{ocr_text}
---

Usa la herramienta extract_invoice_data para devolver los datos estructurados.
Sé preciso y conservador - si no estás seguro de un campo, usa null.
"""
    
    def _extract_tool_use_data(self, message) -> dict:
        """
        Extraer datos del tool use en la respuesta de Claude
        """
        for content in message.content:
            if content.type == "tool_use" and content.name == "extract_invoice_data":
                return content.input
        
        raise NERError("No se encontró tool_use en la respuesta de Claude")
    
    def _parse_structured_data(self, data: dict) -> NERResponse:
        """
        Parsear y validar datos estructurados a NERResponse
        """
        try:
            # Extraer vendor
            vendor_data = data.get('vendor', {})
            vendor = VendorExtracted(
                name=vendor_data.get('name', ''),
                nit=vendor_data.get('nit', ''),
                address=vendor_data.get('address'),
                phone=vendor_data.get('phone')
            )
            
            # Extraer store
            store_data = data.get('store', {})
            store = StoreExtracted(
                name=store_data.get('name'),
                address=store_data.get('address')
            )
            
            # Extraer items
            items_data = data.get('items', [])
            items = []
            for item_dict in items_data:
                try:
                    item = ItemExtracted(
                        product_name=item_dict.get('product_name', ''),
                        sku=item_dict.get('sku'),
                        quantity=float(item_dict.get('quantity', 0)),
                        unit_price=float(item_dict.get('unit_price', 0)),
                        line_total=float(item_dict.get('line_total', 0))
                    )
                    items.append(item)
                except Exception as e:
                    logger.warning(f"Error parseando item: {e}. Item: {item_dict}")
                    continue
            
            if not items:
                raise NERError("No se pudieron extraer items de la factura")
            
            # Extraer fechas
            from datetime import datetime
            
            invoice_date_str = data.get('invoice_date')
            invoice_date = datetime.fromisoformat(invoice_date_str).date() if invoice_date_str else None
            
            due_date_str = data.get('due_date')
            due_date = datetime.fromisoformat(due_date_str).date() if due_date_str else None
            
            # Extraer montos
            subtotal = data.get('subtotal')
            tax = data.get('tax')
            total = float(data.get('total', 0))
            
            if total <= 0:
                raise NERError("Total de factura inválido")
            
            # Confidence
            confidence = float(data.get('confidence', 0.8))
            
            # Validaciones adicionales
            if not vendor.name or not vendor.nit:
                logger.warning("Vendor incompleto en NER")
                confidence *= 0.9
            
            if not invoice_date:
                logger.warning("Fecha de factura no extraída")
                confidence *= 0.85
            
            # Validar suma de items vs total
            items_sum = sum(item.line_total for item in items)
            if abs(items_sum - total) / total > settings.VALIDATE_TOTAL_THRESHOLD_PERCENT:
                logger.warning(
                    f"Discrepancia en total: items_sum={items_sum:.2f}, "
                    f"total={total:.2f}, diff={abs(items_sum - total):.2f}"
                )
                confidence *= 0.9
            
            return NERResponse(
                vendor=vendor,
                store=store,
                invoice_number=data.get('invoice_number', ''),
                invoice_date=invoice_date,
                due_date=due_date,
                items=items,
                subtotal=subtotal,
                tax=tax,
                total=total,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error parseando datos estructurados: {e}", exc_info=True)
            raise NERError(f"Error validando datos extraídos: {str(e)}")
    
    async def batch_extract(
        self,
        ocr_texts: list[str],
        max_concurrent: Optional[int] = None
    ) -> list[NERResponse]:
        """
        Procesar múltiples textos OCR en paralelo
        
        Args:
            ocr_texts: Lista de textos OCR
            max_concurrent: Máximo de tareas concurrentes (default: desde config)
            
        Returns:
            Lista de NERResponse en el mismo orden
        """
        max_concurrent = max_concurrent or settings.MAX_CONCURRENT_WORKERS
        
        logger.info(f"NER batch: {len(ocr_texts)} textos, max_concurrent={max_concurrent}")
        
        # Crear semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(text: str) -> NERResponse:
            async with semaphore:
                return await self.extract_entities(text)
        
        # Ejecutar todas las tareas
        tasks = [extract_with_semaphore(text) for text in ocr_texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados y errores
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error en texto {i}: {result}")
                # Devolver None en lugar de fallar todo
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r is not None)
        logger.info(f"NER batch completado: {success_count}/{len(ocr_texts)} exitosos")
        
        return processed_results
    
    def validate_ner_response(self, ner_response: NERResponse) -> tuple[bool, list[str]]:
        """
        Validar respuesta NER contra reglas de negocio
        
        Returns:
            Tuple[is_valid, list_of_errors]
        """
        errors = []
        
        # Validar NIT
        if settings.VALIDATE_NIT_FORMAT:
            if not self._validate_nit(ner_response.vendor.nit):
                errors.append(f"NIT inválido: {ner_response.vendor.nit}")
        
        # Validar rango de fechas
        from datetime import datetime, timedelta
        today = datetime.now().date()
        max_date_range = timedelta(days=settings.VALIDATE_DATE_RANGE_DAYS)
        
        if ner_response.invoice_date:
            date_diff = abs((today - ner_response.invoice_date).days)
            if date_diff > settings.VALIDATE_DATE_RANGE_DAYS:
                errors.append(
                    f"Fecha de factura fuera de rango: {ner_response.invoice_date} "
                    f"(>{settings.VALIDATE_DATE_RANGE_DAYS} días)"
                )
        
        # Validar total vs suma items
        items_sum = sum(item.line_total for item in ner_response.items)
        diff_percent = abs(items_sum - ner_response.total) / ner_response.total
        
        if diff_percent > settings.VALIDATE_TOTAL_THRESHOLD_PERCENT:
            errors.append(
                f"Discrepancia en total: suma_items={items_sum:.2f}, "
                f"total={ner_response.total:.2f}, diff={diff_percent*100:.2f}%"
            )
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Validación NER falló: {errors}")
        
        return is_valid, errors
    
    def _validate_nit(self, nit: str) -> bool:
        """
        Validar formato de NIT colombiano
        
        Formato: XXXXXXXXX-X (9 dígitos + guion + dígito verificación)
        """
        import re
        
        # Patrón básico: 9-10 dígitos + guion + 1 dígito
        pattern = r'^\d{9,10}-\d$'
        
        if not re.match(pattern, nit):
            return False
        
        # TODO: Implementar validación de dígito verificador si se requiere
        # (algoritmo específico de DIAN)
        
        return True


# Singleton instance
_ner_service: Optional[NERService] = None


def get_ner_service() -> NERService:
    """
    Obtener instancia singleton del servicio NER
    """
    global _ner_service
    if _ner_service is None:
        _ner_service = NERService()
    return _ner_service