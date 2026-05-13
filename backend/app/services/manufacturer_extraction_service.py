
"""
Manufacturer Extraction Service
Extrae información de manufacturer de nombres de productos
"""
import re
from typing import Optional, Tuple, Dict, Any
from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ManufacturerExtractionService:
    """
    Extrae manufacturer de nombres de productos y limpia el nombre
    """
    
    def __init__(self):
        self.db = DatabaseService()
        # Patrones comunes de separadores
        self.separators = [
            r'\s*\|\s*',  # pipe: " | "
            r'\s*-\s*(?=[A-Z][a-z]+\s*$)',  # dash antes de nombre capitalizado al final
            r'\s*\(\s*([A-Z][^)]+)\s*\)\s*$',  # paréntesis al final: "(Bindi)"
        ]
    
    def extract_manufacturer(self, product_name: str) -> Dict[str, Any]:
        """
        Extrae manufacturer del nombre del producto
        
        Args:
            product_name: Nombre completo del producto
            
        Returns:
            {
                'manufacturer_name': str or None,
                'product_name_clean': str,
                'manufacturer_prefix': str or None (el texto exacto extraído)
            }
        """
        if not product_name or product_name.strip() == '':
            return {
                'manufacturer_name': None,
                'product_name_clean': product_name,
                'manufacturer_prefix': None
            }
        
        manufacturer_name = None
        manufacturer_prefix = None
        clean_name = product_name.strip()
        
        # Patrón 1: Pipe separator " | Manufacturer"
        # El manufacturer está en el segmento después del último pipe
        if '|' in product_name:
            parts = product_name.split('|')
            
            # El manufacturer candidato es el último segmento no vacío
            for i in range(len(parts) - 1, -1, -1):
                candidate = parts[i].strip()
                if candidate:
                    # Limpiar información adicional (números, medidas)
                    # Extraer solo el nombre (primeras 1-3 palabras capitalizadas)
                    match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', candidate)
                    if match:
                        manufacturer_name = match.group(1).strip()
                        manufacturer_prefix = candidate
                        # Clean name = todo antes del pipe donde encontramos el manufacturer
                        clean_name = '|'.join(parts[:i]).strip()
                        break
        
        # Patrón 2: Paréntesis al final "(Manufacturer)"
        if not manufacturer_name:
            paren_match = re.search(r'\(([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\)\s*$', product_name)
            if paren_match:
                manufacturer_prefix = paren_match.group(1).strip()
                manufacturer_name = manufacturer_prefix
                clean_name = re.sub(r'\s*\([^)]+\)\s*$', '', product_name).strip()
        
        # Patrón 3: Dash al final " - Manufacturer"
        if not manufacturer_name:
            dash_match = re.search(r'\s+-\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s*$', product_name)
            if dash_match:
                potential_mfr = dash_match.group(1).strip()
                # Validar que no sea parte de la descripción
                common_words = ['frozen', 'fresh', 'organic', 'whole', 'sliced', 'usa', 'italy']
                if potential_mfr.lower() not in common_words:
                    manufacturer_prefix = potential_mfr
                    manufacturer_name = potential_mfr
                    clean_name = product_name[:dash_match.start()].strip()
        
        return {
            'manufacturer_name': manufacturer_name,
            'product_name_clean': clean_name,
            'manufacturer_prefix': manufacturer_prefix
        }
    
    def get_or_create_manufacturer(self, manufacturer_name: str) -> Optional[str]:
        """
        Busca o crea un manufacturer
        
        Returns:
            UUID del manufacturer o None
        """
        if not manufacturer_name:
            return None
        
        try:
            # Buscar existente
            result = self.db.client.table('manufacturers').select('id').eq(
                'name', manufacturer_name
            ).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            
            # Crear nuevo
            logger.info(f"Creating new manufacturer: {manufacturer_name}")
            insert_result = self.db.client.table('manufacturers').insert({
                'name': manufacturer_name
            }).execute()
            
            if insert_result.data:
                return insert_result.data[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating manufacturer: {e}")
            return None
    
    def process_invoice_item(self, item_id: str, product_name: str) -> bool:
        """
        Procesa un invoice_item existente para extraer manufacturer
        
        Args:
            item_id: UUID del invoice_item
            product_name: Nombre del producto
            
        Returns:
            True si se actualizó exitosamente
        """
        try:
            # Extraer manufacturer
            extraction = self.extract_manufacturer(product_name)
            
            # Obtener o crear manufacturer
            manufacturer_id = None
            if extraction['manufacturer_name']:
                manufacturer_id = self.get_or_create_manufacturer(
                    extraction['manufacturer_name']
                )
            
            # Actualizar invoice_item
            self.db.client.table('invoice_items').update({
                'manufacturer_id': manufacturer_id,
                'manufacturer_prefix': extraction['manufacturer_prefix'],
                'product_name_clean': extraction['product_name_clean']
            }).eq('id', item_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing invoice item {item_id}: {e}")
            return False


# Singleton
_manufacturer_service: Optional[ManufacturerExtractionService] = None

def get_manufacturer_service() -> ManufacturerExtractionService:
    """Obtener instancia singleton"""
    global _manufacturer_service
    if _manufacturer_service is None:
        _manufacturer_service = ManufacturerExtractionService()
    return _manufacturer_service