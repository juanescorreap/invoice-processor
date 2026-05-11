"""
Normalization Router - Product name normalization endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.normalization_service import get_normalization_service
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/normalization", tags=["normalization"])


# Schemas
class NormalizedProductCreate(BaseModel):
    normalized_name: str = Field(..., description="Nombre normalizado del producto")
    normalized_code: Optional[str] = Field(None, description="Código normalizado")
    category: Optional[str] = Field(None, description="Categoría del producto")
    description: Optional[str] = Field(None, description="Descripción")


class ProductMappingCreate(BaseModel):
    variant_name: str = Field(..., description="Nombre variante del producto")
    normalized_product_id: str = Field(..., description="ID del producto normalizado")
    vendor_id: Optional[str] = Field(None, description="ID del vendor")
    similarity_score: Optional[float] = Field(None, ge=0, le=100)
    status: str = Field("pending", description="Estado: pending, approved, rejected")


class SimilarProductsRequest(BaseModel):
    product_name: str = Field(..., description="Nombre del producto a buscar")
    vendor_id: Optional[str] = Field(None, description="ID del vendor (opcional)")
    limit: int = Field(5, ge=1, le=20, description="Número máximo de resultados")


# Endpoints
@router.post("/products", summary="Crear producto normalizado")
async def create_normalized_product(product: NormalizedProductCreate):
    """
    Crea un nuevo producto normalizado
    """
    try:
        service = get_normalization_service()
        
        product_id = service.create_normalized_product(
            normalized_name=product.normalized_name,
            normalized_code=product.normalized_code,
            category=product.category,
            description=product.description
        )
        
        if not product_id:
            raise HTTPException(status_code=500, detail="Failed to create normalized product")
        
        return {
            "success": True,
            "product_id": product_id,
            "message": f"Producto normalizado creado: {product.normalized_name}"
        }
        
    except Exception as e:
        logger.error(f"Error creating normalized product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mappings", summary="Crear mapeo de producto")
async def create_product_mapping(mapping: ProductMappingCreate):
    """
    Crea un mapeo de nombre variante a producto normalizado
    """
    try:
        service = get_normalization_service()
        
        success = service.create_product_mapping(
            variant_name=mapping.variant_name,
            normalized_product_id=mapping.normalized_product_id,
            vendor_id=mapping.vendor_id,
            similarity_score=mapping.similarity_score,
            status=mapping.status
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create mapping")
        
        return {
            "success": True,
            "message": f"Mapeo creado: '{mapping.variant_name}' → {mapping.normalized_product_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating product mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similar", summary="Buscar productos similares")
async def find_similar_products(request: SimilarProductsRequest):
    """
    Encuentra productos similares usando fuzzy matching
    """
    try:
        service = get_normalization_service()
        
        results = service.find_similar_products(
            product_name=request.product_name,
            vendor_id=request.vendor_id,
            limit=request.limit
        )
        
        return {
            "success": True,
            "query": request.product_name,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error finding similar products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions", summary="Obtener sugerencias de normalización")
async def get_normalization_suggestions(
    auto_approve_threshold: int = Query(95, ge=80, le=100, description="Score para auto-aprobar")
):
    """
    Genera sugerencias de normalización para productos sin mapear
    """
    try:
        service = get_normalization_service()
        
        suggestions = service.suggest_normalizations(
            auto_approve_threshold=auto_approve_threshold
        )
        
        return {
            "success": True,
            "suggestions_count": len(suggestions),
            "auto_approve_threshold": auto_approve_threshold,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{variant_name}", summary="Obtener producto normalizado")
async def get_normalized_product(
    variant_name: str,
    vendor_id: Optional[str] = Query(None, description="ID del vendor")
):
    """
    Obtiene el producto normalizado para una variante específica
    """
    try:
        service = get_normalization_service()
        
        product = service.get_normalized_product(
            variant_name=variant_name,
            vendor_id=vendor_id
        )
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"No normalized product found for '{variant_name}'"
            )
        
        return {
            "success": True,
            "variant_name": variant_name,
            "normalized_product": product
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting normalized product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mappings/{mapping_id}/approve", summary="Aprobar mapeo")
async def approve_mapping(
    mapping_id: str,
    reviewed_by: str = Query(..., description="Usuario que aprueba")
):
    """
    Aprueba un mapeo de producto
    """
    try:
        service = get_normalization_service()
        
        result = service.db.supabase.table('product_name_mappings').update({
            'status': 'approved',
            'reviewed_by': reviewed_by,
            'reviewed_at': 'now()'
        }).eq('id', mapping_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        return {
            "success": True,
            "message": f"Mapeo aprobado por {reviewed_by}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mappings/{mapping_id}/reject", summary="Rechazar mapeo")
async def reject_mapping(
    mapping_id: str,
    reviewed_by: str = Query(..., description="Usuario que rechaza")
):
    """
    Rechaza un mapeo de producto
    """
    try:
        service = get_normalization_service()
        
        result = service.db.supabase.table('product_name_mappings').update({
            'status': 'rejected',
            'reviewed_by': reviewed_by,
            'reviewed_at': 'now()'
        }).eq('id', mapping_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        return {
            "success": True,
            "message": f"Mapeo rechazado por {reviewed_by}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))