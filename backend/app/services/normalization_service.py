"""
Product Normalization Service - Fuzzy Matching
"""
from typing import List, Dict, Any, Optional, Tuple
from thefuzz import fuzz
from thefuzz import process
import re

from app.services.database_service import DatabaseService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProductNormalizationService:
    """
    Servicio para normalizar nombres de productos usando fuzzy matching
    """
    
    def __init__(self, db_service: Optional[DatabaseService] = None):
        """Inicializar servicio"""
        self.db = db_service or DatabaseService()
        self.similarity_threshold = 70  # Score mínimo para considerar match
        
    def normalize_product_name(self, raw_name: str) -> str:
        """
        Limpia y normaliza un nombre de producto
        
        Args:
            raw_name: Nombre crudo del producto
            
        Returns:
            Nombre normalizado
        """
        # Convertir a minúsculas
        normalized = raw_name.lower()
        
        # Remover caracteres especiales excepto espacios y números
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Remover espacios múltiples
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remover espacios al inicio/final
        normalized = normalized.strip()
        
        return normalized
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calcula similitud entre dos nombres usando múltiples métodos
        
        Returns:
            Score de similitud (0-100)
        """
        # Normalizar ambos nombres
        norm1 = self.normalize_product_name(name1)
        norm2 = self.normalize_product_name(name2)
        
        # Usar múltiples algoritmos y promediar
        ratio = fuzz.ratio(norm1, norm2)
        partial_ratio = fuzz.partial_ratio(norm1, norm2)
        token_sort = fuzz.token_sort_ratio(norm1, norm2)
        token_set = fuzz.token_set_ratio(norm1, norm2)
        
        # Weighted average (token_set es más robusto)
        score = (ratio * 0.2 + partial_ratio * 0.2 + 
                token_sort * 0.3 + token_set * 0.3)
        
        return round(score, 2)
    
    def find_similar_products(
        self,
        product_name: str,
        vendor_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Encuentra productos similares en la base de datos
        
        Args:
            product_name: Nombre del producto a buscar
            vendor_id: ID del vendor (opcional, para filtrar por vendor)
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos similares con scores
        """
        try:
            # Obtener todos los productos únicos de invoice_items
            query = self.db.client.table('invoice_items').select(
                'vendor_product_name, invoices!inner(vendor_id)'
            )
            
            if vendor_id:
                query = query.eq('invoices.vendor_id', vendor_id)
            
            result = query.execute()
            
            if not result.data:
                return []
            
            # Obtener nombres únicos
            unique_products = {}
            for item in result.data:
                name = item['vendor_product_name']
                v_id = item['invoices']['vendor_id']
                key = f"{name}_{v_id}"
                if key not in unique_products:
                    unique_products[key] = {
                        'name': name,
                        'vendor_id': v_id
                    }
            
            # Calcular similitud con cada producto
            matches = []
            for key, prod in unique_products.items():
                score = self.calculate_similarity(product_name, prod['name'])
                
                if score >= self.similarity_threshold:
                    matches.append({
                        'product_name': prod['name'],
                        'vendor_id': prod['vendor_id'],
                        'similarity_score': score
                    })
            
            # Ordenar por score descendente
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar products: {e}")
            return []
    
    def create_normalized_product(
        self,
        normalized_name: str,
        normalized_code: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[str]:
        """
        Crea un nuevo producto normalizado
        
        Returns:
            ID del producto normalizado creado
        """
        try:
            result = self.db.client.table('normalized_products').insert({
                'normalized_name': normalized_name,
                'normalized_code': normalized_code,
                'category': category,
                'description': description
            }).execute()
            
            if result.data:
                product_id = result.data[0]['id']
                logger.info(f"✅ Producto normalizado creado: {normalized_name} (ID: {product_id})")
                return product_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating normalized product: {e}")
            return None
    
    def create_product_mapping(
        self,
        variant_name: str,
        normalized_product_id: str,
        vendor_id: Optional[str] = None,
        similarity_score: Optional[float] = None,
        status: str = 'pending'
    ) -> bool:
        """
        Crea un mapeo de nombre variante a producto normalizado
        
        Returns:
            True si se creó exitosamente
        """
        try:
            self.db.client.table('product_name_mappings').insert({
                'variant_name': variant_name,
                'vendor_id': vendor_id,
                'normalized_product_id': normalized_product_id,
                'similarity_score': similarity_score,
                'status': status
            }).execute()
            
            logger.info(f"✅ Mapeo creado: '{variant_name}' → {normalized_product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating product mapping: {e}")
            return False
    
    def get_normalized_product(
        self,
        variant_name: str,
        vendor_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene el producto normalizado para una variante
        
        Returns:
            Producto normalizado o None si no existe mapeo
        """
        try:
            query = self.db.client.table('product_name_mappings').select(
                '*, normalized_products(*)'
            ).eq('variant_name', variant_name).eq('status', 'approved')
            
            if vendor_id:
                query = query.eq('vendor_id', vendor_id)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['normalized_products']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting normalized product: {e}")
            return None
    
    def suggest_normalizations(
        self,
        auto_approve_threshold: int = 95
    ) -> List[Dict[str, Any]]:
        """
        Genera sugerencias de normalización para productos sin mapear
        
        Args:
            auto_approve_threshold: Score para auto-aprobar (default 95)
            
        Returns:
            Lista de sugerencias
        """
        try:
            # Obtener todos los productos únicos sin mapeo
            result = self.db.client.table('invoice_items').select(
                'vendor_product_name, invoices!inner(vendor_id, vendors(name))'
            ).execute()
            
            if not result.data:
                return []
            
            # Agrupar por nombre de producto
            products = {}
            for item in result.data:
                name = item['vendor_product_name']
                v_id = item['invoices']['vendor_id']
                v_name = item['invoices']['vendors']['name']
                
                key = f"{name}_{v_id}"
                if key not in products:
                    products[key] = {
                        'variant_name': name,
                        'vendor_id': v_id,
                        'vendor_name': v_name,
                        'count': 0
                    }
                products[key]['count'] += 1
            
            # Para cada producto, buscar similares
            suggestions = []
            for key, prod in list(products.items())[:50]:  # Limitar a 50 para no saturar
                # Verificar si ya tiene mapeo
                existing = self.get_normalized_product(
                    prod['variant_name'],
                    prod['vendor_id']
                )
                
                if existing:
                    continue  # Ya tiene mapeo
                
                # Buscar productos similares
                similar = self.find_similar_products(
                    prod['variant_name'],
                    prod['vendor_id'],
                    limit=3
                )
                
                if similar:
                    suggestions.append({
                        'variant_name': prod['variant_name'],
                        'vendor_id': prod['vendor_id'],
                        'vendor_name': prod['vendor_name'],
                        'item_count': prod['count'],
                        'suggestions': similar,
                        'auto_approve': similar[0]['similarity_score'] >= auto_approve_threshold
                    })
            
            logger.info(f"✅ Generadas {len(suggestions)} sugerencias de normalización")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating normalization suggestions: {e}")
            return []


# Singleton
_normalization_service: Optional[ProductNormalizationService] = None

def get_normalization_service() -> ProductNormalizationService:
    """Obtener instancia singleton"""
    global _normalization_service
    if _normalization_service is None:
        _normalization_service = ProductNormalizationService()
    return _normalization_service