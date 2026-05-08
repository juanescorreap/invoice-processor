"""
Modelos Pydantic para validación de datos
"""
from pydantic import BaseModel, Field, validator, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ProcessingStatus(str, Enum):
    """Estados de procesamiento de facturas"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
    MANUAL_REVIEW = "manual_review"
    VALIDATED = "validated"


class QueueStatus(str, Enum):
    """Estados de cola de procesamiento"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    """Tipos de eventos en el log"""
    UPLOADED = "uploaded"
    OCR_STARTED = "ocr_started"
    OCR_COMPLETED = "ocr_completed"
    NER_STARTED = "ner_started"
    NER_COMPLETED = "ner_completed"
    NORMALIZED = "normalized"
    VALIDATED = "validated"
    ERROR = "error"


class LogStatus(str, Enum):
    """Estados de log"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ============================================================================
# MODELS: VENDORS
# ============================================================================

class VendorBase(BaseModel):
    """Base vendor model"""
    name: str = Field(..., min_length=1, max_length=255)
    nit: str = Field(..., min_length=9, max_length=20)
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class VendorCreate(VendorBase):
    """Vendor creation"""
    pass


class VendorUpdate(BaseModel):
    """Vendor update"""
    name: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class Vendor(VendorBase):
    """Vendor response"""
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: STORES
# ============================================================================

class StoreBase(BaseModel):
    """Base store model"""
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = None


class StoreCreate(StoreBase):
    """Store creation"""
    pass


class StoreUpdate(BaseModel):
    """Store update"""
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None


class Store(StoreBase):
    """Store response"""
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: PRODUCTS
# ============================================================================

class ProductBase(BaseModel):
    """Base product model"""
    master_name: str = Field(..., min_length=1, max_length=255)
    master_sku: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    unit: Optional[str] = None


class ProductCreate(ProductBase):
    """Product creation"""
    pass


class ProductUpdate(BaseModel):
    """Product update"""
    master_name: Optional[str] = None
    master_sku: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None


class Product(ProductBase):
    """Product response"""
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: PRODUCT MAPPINGS
# ============================================================================

class ProductMappingBase(BaseModel):
    """Base product mapping model"""
    product_id: UUID4
    vendor_id: UUID4
    vendor_name: str = Field(..., min_length=1, max_length=255)
    vendor_sku: Optional[str] = None


class ProductMappingCreate(ProductMappingBase):
    """Product mapping creation"""
    pass


class ProductMapping(ProductMappingBase):
    """Product mapping response"""
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: INVOICE ITEMS
# ============================================================================

class InvoiceItemBase(BaseModel):
    """Base invoice item model"""
    vendor_product_name: str = Field(..., min_length=1, max_length=255)
    vendor_sku: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    line_total: Decimal = Field(..., ge=0)
    line_number: Optional[int] = None

    @validator('line_total')
    def validate_line_total(cls, v, values):
        """Validar que line_total = quantity * unit_price"""
        if 'quantity' in values and 'unit_price' in values:
            expected = values['quantity'] * values['unit_price']
            # Permitir 1% de diferencia por redondeo
            if abs(float(v - expected)) > float(expected * Decimal('0.01')):
                raise ValueError(f"line_total {v} no coincide con quantity * unit_price ({expected})")
        return v


class InvoiceItemCreate(InvoiceItemBase):
    """Invoice item creation"""
    product_id: Optional[UUID4] = None


class InvoiceItem(InvoiceItemBase):
    """Invoice item response"""
    id: UUID4
    invoice_id: UUID4
    product_id: Optional[UUID4] = None
    matched: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: INVOICES
# ============================================================================

class InvoiceBase(BaseModel):
    """Base invoice model"""
    invoice_number: str = Field(..., min_length=1, max_length=100)
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = Field(None, ge=0)
    tax: Optional[Decimal] = Field(None, ge=0)
    total: Decimal = Field(..., gt=0)

    @validator('due_date')
    def validate_due_date(cls, v, values):
        """Validar que due_date >= invoice_date"""
        if v and 'invoice_date' in values:
            if v < values['invoice_date']:
                raise ValueError("due_date no puede ser anterior a invoice_date")
        return v


class InvoiceCreate(InvoiceBase):
    """Invoice creation"""
    vendor_id: Optional[UUID4] = None
    store_id: Optional[UUID4] = None
    source_file_path: Optional[str] = None
    source_file_id: Optional[str] = None
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    """Invoice update"""
    invoice_number: Optional[str] = None
    vendor_id: Optional[UUID4] = None
    store_id: Optional[UUID4] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    processing_status: Optional[ProcessingStatus] = None
    validated: Optional[bool] = None


class Invoice(InvoiceBase):
    """Invoice response"""
    id: UUID4
    vendor_id: Optional[UUID4] = None
    store_id: Optional[UUID4] = None
    source_file_path: Optional[str] = None
    source_file_id: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    validated: bool = False
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    raw_ocr_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    processed_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Relaciones
    items: List[InvoiceItem] = []

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: PROCESSING QUEUE
# ============================================================================

class QueueItemBase(BaseModel):
    """Base queue item model"""
    file_path: str
    file_id: str
    file_name: str
    priority: int = Field(default=5, ge=0, le=10)


class QueueItemCreate(QueueItemBase):
    """Queue item creation"""
    pass


class QueueItem(QueueItemBase):
    """Queue item response"""
    id: UUID4
    status: QueueStatus = QueueStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    last_error_at: Optional[datetime] = None
    scheduled_for: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: PROCESSING LOG
# ============================================================================

class ProcessingLogBase(BaseModel):
    """Base processing log model"""
    event_type: EventType
    status: LogStatus
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ProcessingLogCreate(ProcessingLogBase):
    """Processing log creation"""
    invoice_id: Optional[UUID4] = None


class ProcessingLog(ProcessingLogBase):
    """Processing log response"""
    id: UUID4
    invoice_id: Optional[UUID4] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELS: CLAUDE API RESPONSES
# ============================================================================

class OCRResponse(BaseModel):
    """Respuesta de OCR"""
    text: str
    confidence: float = Field(..., ge=0, le=1)
    processing_time_seconds: float


class VendorExtracted(BaseModel):
    """Vendor extraído por NER"""
    name: str
    nit: str
    address: Optional[str] = None
    phone: Optional[str] = None


class StoreExtracted(BaseModel):
    """Store extraído por NER"""
    name: Optional[str] = None
    address: Optional[str] = None


class ItemExtracted(BaseModel):
    """Item extraído por NER"""
    product_name: str
    sku: Optional[str] = None
    quantity: float
    unit_price: float
    line_total: float


class NERResponse(BaseModel):
    """Respuesta de NER"""
    vendor: VendorExtracted
    store: StoreExtracted
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    items: List[ItemExtracted]
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    confidence: float = Field(..., ge=0, le=1)


# ============================================================================
# MODELS: API REQUESTS
# ============================================================================

class ProcessFileRequest(BaseModel):
    """Request para procesar archivo"""
    file_path: Optional[str] = None
    file_id: Optional[str] = None
    priority: int = Field(default=5, ge=0, le=10)


class ValidateInvoiceRequest(BaseModel):
    """Request para validar factura"""
    validated: bool
    validated_by: str
    corrections: Optional[Dict[str, Any]] = None


class BulkProcessRequest(BaseModel):
    """Request para procesamiento bulk"""
    folder_id: str
    max_files: Optional[int] = Field(default=100, ge=1, le=1000)
    priority: int = Field(default=5, ge=0, le=10)


# ============================================================================
# MODELS: API RESPONSES
# ============================================================================

class ProcessingStats(BaseModel):
    """Estadísticas de procesamiento"""
    total_invoices: int
    processed: int
    pending: int
    errors: int
    manual_review: int
    avg_confidence: float
    processing_rate_per_hour: float


class DashboardMetrics(BaseModel):
    """Métricas para dashboard"""
    today_processed: int
    today_total_amount: Decimal
    week_processed: int
    week_total_amount: Decimal
    month_processed: int
    month_total_amount: Decimal
    avg_processing_time_seconds: float
    top_vendors: List[Dict[str, Any]]
    recent_errors: List[Dict[str, Any]]


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, bool]


# ============================================================================
# MODELS: FILTERS & PAGINATION
# ============================================================================

class InvoiceFilters(BaseModel):
    """Filtros para búsqueda de facturas"""
    vendor_id: Optional[UUID4] = None
    store_id: Optional[UUID4] = None
    status: Optional[ProcessingStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    validated: Optional[bool] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    search: Optional[str] = None  # Búsqueda en invoice_number o vendor name


class PaginationParams(BaseModel):
    """Parámetros de paginación"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @validator('pages', always=True)
    def calculate_pages(cls, v, values):
        """Calcular número total de páginas"""
        if 'total' in values and 'page_size' in values:
            return (values['total'] + values['page_size'] - 1) // values['page_size']
        return 0