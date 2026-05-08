"""
Servicio OCR usando Claude Vision API
"""
import base64
import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple
import anthropic
from anthropic import AsyncAnthropic

from app.config import settings, CLAUDE_OCR_SYSTEM_PROMPT
from app.models import OCRResponse
from app.utils.logger import get_logger
from app.utils.errors import OCRError, FileError

logger = get_logger(__name__)


class OCRService:
    """
    Servicio para extracción de texto de facturas mediante Claude Vision
    """
    
    def __init__(self):
        """Inicializar cliente Anthropic"""
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL_VISION
        self.max_retries = settings.CLAUDE_RETRY_MAX_ATTEMPTS
        self.retry_delay = settings.CLAUDE_RETRY_DELAY_SECONDS
    
    def _convert_pdf_to_image(self, pdf_path: str) -> str:
        """
        Convertir PDF a imagen PNG (primera página)
        """
        import fitz  # PyMuPDF
        
        logger.info(f"Convirtiendo PDF a imagen: {pdf_path}")
        
        # Abrir PDF
        doc = fitz.open(pdf_path)
        
        # Tomar primera página
        page = doc[0]
        
        # Convertir a imagen (300 DPI para buena calidad)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        
        # Guardar como PNG temporal
        temp_path = pdf_path.replace('.pdf', '_temp.png')
        pix.save(temp_path)
        
        doc.close()
        
        logger.info(f"PDF convertido a: {temp_path}")
        return temp_path
    
    async def process_invoice(
        self, 
        file_path: str,
        timeout: Optional[int] = None
    ) -> OCRResponse:
        """
        Procesar factura y extraer texto
        
        Args:
            file_path: Ruta al archivo PDF/imagen
            timeout: Timeout en segundos (default: desde config)
            
        Returns:
            OCRResponse con texto extraído y metadata
            
        Raises:
            OCRError: Si falla la extracción
            FileError: Si hay problemas con el archivo
        """
        start_time = time.time()
        timeout = timeout or settings.OCR_TIMEOUT_SECONDS
        
        logger.info(f"Iniciando OCR para: {file_path}")
        
        try:
            # Validar archivo
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileError(f"Archivo no encontrado: {file_path}")
            
            if not file_path_obj.is_file():
                raise FileError(f"No es un archivo válido: {file_path}")
            
            # Si es PDF, convertir a imagen
            if file_path_obj.suffix.lower() == '.pdf':
                file_path = self._convert_pdf_to_image(file_path)
                file_path_obj = Path(file_path)
            
            # Validar tamaño
            file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.MAX_FILE_SIZE_MB:
                raise FileError(
                    f"Archivo demasiado grande: {file_size_mb:.2f}MB "
                    f"(máximo: {settings.MAX_FILE_SIZE_MB}MB)"
                )
            
            # Leer y encodear archivo
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            base64_data = base64.standard_b64encode(file_data).decode('utf-8')
            
            # Detectar tipo de archivo
            media_type = self._detect_media_type(file_path_obj)
            
            logger.debug(f"Archivo: {file_path_obj.name}, Tamaño: {file_size_mb:.2f}MB, Tipo: {media_type}")
            
            # Llamar a Claude Vision con retry logic
            text, confidence = await self._call_claude_vision(
                base64_data=base64_data,
                media_type=media_type,
                timeout=timeout
            )
            
            processing_time = time.time() - start_time
            
            logger.info(
                f"OCR completado: {len(text)} caracteres, "
                f"confidence={confidence:.4f}, "
                f"tiempo={processing_time:.2f}s"
            )
            
            return OCRResponse(
                text=text,
                confidence=confidence,
                processing_time_seconds=processing_time
            )
            
        except asyncio.TimeoutError:
            raise OCRError(f"OCR timeout después de {timeout}s")
        
        except anthropic.APIError as e:
            logger.error(f"Error en Claude API: {e}")
            raise OCRError(f"Error en Claude Vision API: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error inesperado en OCR: {e}", exc_info=True)
            raise OCRError(f"Error procesando OCR: {str(e)}")
    
    async def _call_claude_vision(
        self,
        base64_data: str,
        media_type: str,
        timeout: int
    ) -> Tuple[str, float]:
        """
        Llamar a Claude Vision API con retry logic
        
        Returns:
            Tuple[texto_extraido, confidence_score]
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Claude Vision API - Intento {attempt}/{self.max_retries}")
                
                # Construir mensaje
                message = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=settings.CLAUDE_MAX_TOKENS,
                        temperature=settings.CLAUDE_TEMPERATURE,
                        system=CLAUDE_OCR_SYSTEM_PROMPT,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": base64_data,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": "Extrae TODO el texto de esta factura."
                                    }
                                ],
                            }
                        ],
                    ),
                    timeout=timeout
                )
                
                # Extraer texto
                text = self._extract_text_from_response(message)
                
                if not text or len(text.strip()) < 10:
                    raise OCRError("Texto extraído es demasiado corto o vacío")
                
                # Calcular confidence basado en stop_reason y uso de tokens
                confidence = self._calculate_confidence(message)
                
                return text, confidence
                
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
        
        # Si llegamos aquí, todos los intentos fallaron
        raise OCRError(f"OCR falló después de {self.max_retries} intentos. Último error: {last_error}")
    
    def _extract_text_from_response(self, message) -> str:
        """
        Extraer texto de la respuesta de Claude
        """
        # Claude puede devolver múltiples bloques de contenido
        text_parts = []
        
        for content in message.content:
            if content.type == "text":
                text_parts.append(content.text)
        
        return "\n".join(text_parts)
    
    def _calculate_confidence(self, message) -> float:
        """
        Calcular score de confianza basado en metadata de la respuesta
        """
        # Factores que afectan confidence:
        # 1. stop_reason = "end_turn" es bueno
        # 2. Uso de tokens vs max_tokens
        
        confidence = 0.9  # Base confidence
        
        # Si terminó normalmente (no truncado)
        if message.stop_reason == "end_turn":
            confidence += 0.05
        elif message.stop_reason == "max_tokens":
            confidence -= 0.1  # Posiblemente truncado
        
        # Si usó muy pocos tokens, puede ser que no extrajo todo
        if hasattr(message, 'usage'):
            tokens_used = message.usage.output_tokens
            tokens_max = settings.CLAUDE_MAX_TOKENS
            
            if tokens_used < 50:
                confidence -= 0.15  # Muy poco texto
            elif tokens_used > tokens_max * 0.9:
                confidence -= 0.05  # Posible truncamiento
        
        # Clamp entre 0 y 1
        return max(0.0, min(1.0, confidence))
    
    def _detect_media_type(self, file_path: Path) -> str:
        """
        Detectar tipo MIME del archivo
        """
        extension = file_path.suffix.lower()
        
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        
        media_type = media_types.get(extension)
        
        if not media_type:
            raise FileError(
                f"Tipo de archivo no soportado: {extension}. "
                f"Soportados: {', '.join(media_types.keys())}"
            )
        
        return media_type
    
    async def batch_process(
        self,
        file_paths: list[str],
        max_concurrent: Optional[int] = None
    ) -> list[OCRResponse]:
        """
        Procesar múltiples facturas en paralelo
        
        Args:
            file_paths: Lista de rutas a procesar
            max_concurrent: Máximo de tareas concurrentes (default: desde config)
            
        Returns:
            Lista de OCRResponse en el mismo orden que file_paths
        """
        max_concurrent = max_concurrent or settings.MAX_CONCURRENT_WORKERS
        
        logger.info(f"Procesamiento batch: {len(file_paths)} archivos, max_concurrent={max_concurrent}")
        
        # Crear semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(file_path: str) -> OCRResponse:
            async with semaphore:
                return await self.process_invoice(file_path)
        
        # Ejecutar todas las tareas
        tasks = [process_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados y errores
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error en {file_paths[i]}: {result}")
                # Devolver un resultado de error en lugar de fallar todo
                processed_results.append(
                    OCRResponse(
                        text="",
                        confidence=0.0,
                        processing_time_seconds=0.0
                    )
                )
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.confidence > 0)
        logger.info(f"Batch completado: {success_count}/{len(file_paths)} exitosos")
        
        return processed_results


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """
    Obtener instancia singleton del servicio OCR
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service