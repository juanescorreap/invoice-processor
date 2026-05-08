"""Mock OCR Service para desarrollo"""
from app.models import OCRResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MockOCRService:
    async def process_invoice(self, file_path: str) -> OCRResponse:
        logger.info(f"[MOCK] Procesando: {file_path}")
        
        # Texto simulado de factura
        mock_text = """
DISTRIBUIDORA ABC S.A.S
NIT: 900111111-1
Calle 10 #5-20, Bogotá
Tel: 3001111111

FACTURA DE VENTA
No. FAC-001234
Fecha: 2026-05-08

CLIENTE: Tienda Centro
DIRECCIÓN: Calle 15 #10-30

CANT  DESCRIPCIÓN           P.UNIT    TOTAL
24    Coca Cola 1.5L        2,500    60,000
12    Pepsi 1.5L            2,300    27,600
50    Agua mineral          1,200    60,000

                        SUBTOTAL:   147,600
                        IVA (19%):   28,044
                        TOTAL:      175,644
"""
        
        return OCRResponse(
            text=mock_text,
            confidence=0.95,
            processing_time_seconds=0.5
        )

def get_ocr_service():
    return MockOCRService()