"""Mock NER Service - Temporal hasta resolver API Anthropic"""
import time
from datetime import date
from app.models import NERResponse, VendorExtracted, StoreExtracted, ItemExtracted
from app.utils.logger import get_logger
import random


logger = get_logger(__name__)

class MockNERService:
    async def extract_entities(self, ocr_text: str) -> NERResponse:
        logger.info(f"[MOCK] Extrayendo entidades de {len(ocr_text)} caracteres")
        
        time.sleep(0.5)  # Simular procesamiento
        
        # Parsear datos simulados del texto
        vendor = VendorExtracted(
            name="DISTRIBUIDORA ABC S.A.S",
            nit="900111111-1",
            address="Calle 10 #5-20, Bogotá",
            phone="3001111111"
        )
        
        store = StoreExtracted(
            name="Tienda Centro",
            address="Calle 15 #10-30"
        )
        
        items = [
            ItemExtracted(
                product_name="Coca Cola 1.5L",
                sku=None,
                quantity=24,
                unit_price=2500,
                line_total=60000
            ),
            ItemExtracted(
                product_name="Pepsi 1.5L",
                sku=None,
                quantity=12,
                unit_price=2300,
                line_total=27600
            ),
        ]
        
        return NERResponse(
            vendor=vendor,
            store=store,
            invoice_number=f"FAC-{random.randint(100000, 999999)}",
            invoice_date=date(2026, 5, 8),
            due_date=None,
            items=items,
            subtotal=87600,
            tax=16644,
            total=104244,
            confidence=0.92
        )

def get_ner_service():
    return MockNERService()