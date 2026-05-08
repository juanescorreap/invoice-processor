"""
Configuración del sistema de procesamiento de facturas
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configuración global de la aplicación
    """
    
    # ============================================================================
    # APP CONFIG
    # ============================================================================
    APP_NAME: str = "Invoice Processor"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # ============================================================================
    # API CONFIG
    # ============================================================================
    API_PREFIX: str = "/api"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # ============================================================================
    # CLAUDE API
    # ============================================================================
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL_VISION: str = "claude-sonnet-4-20250514"
    CLAUDE_MODEL_TEXT: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.0
    
    # Límites de rate
    CLAUDE_MAX_REQUESTS_PER_MINUTE: int = 50
    CLAUDE_RETRY_MAX_ATTEMPTS: int = 3
    CLAUDE_RETRY_DELAY_SECONDS: int = 2
    
    # ============================================================================
    # SUPABASE
    # ============================================================================
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon/public key
    SUPABASE_SERVICE_KEY: str  # service role key (admin)
    
    # ============================================================================
    # GOOGLE DRIVE API
    # ============================================================================
    GOOGLE_DRIVE_CREDENTIALS_PATH: str = "./credentials.json"
    GOOGLE_DRIVE_TOKEN_PATH: str = "./token.json"
    GOOGLE_DRIVE_FOLDER_IDS: List[str] = []  # Lista de carpetas a monitorear
    GOOGLE_DRIVE_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # ============================================================================
    # PROCESAMIENTO
    # ============================================================================
    
    # Workers
    MAX_CONCURRENT_WORKERS: int = 5
    WORKER_POLL_INTERVAL_SECONDS: int = 10
    
    # Queue
    QUEUE_MAX_RETRIES: int = 3
    QUEUE_RETRY_DELAY_SECONDS: int = 60
    QUEUE_PRIORITY_HIGH: int = 10
    QUEUE_PRIORITY_NORMAL: int = 5
    QUEUE_PRIORITY_LOW: int = 1
    
    # Scheduler (monitoreo Google Drive)
    SCHEDULER_INTERVAL_MINUTES: int = 5
    SCHEDULER_ENABLED: bool = True
    
    # Timeouts
    PROCESSING_TIMEOUT_SECONDS: int = 120
    OCR_TIMEOUT_SECONDS: int = 60
    NER_TIMEOUT_SECONDS: int = 60
    
    # ============================================================================
    # VALIDACIÓN
    # ============================================================================
    
    # Confidence thresholds
    MIN_CONFIDENCE_AUTO_APPROVE: float = 0.95  # Auto-aprobar si >= 95%
    MIN_CONFIDENCE_MANUAL_REVIEW: float = 0.75  # Marcar para revisión si < 75%
    
    # Validación de campos
    VALIDATE_NIT_FORMAT: bool = True
    VALIDATE_DATE_RANGE_DAYS: int = 365  # Facturas dentro de 1 año
    VALIDATE_TOTAL_THRESHOLD_PERCENT: float = 0.01  # 1% diferencia máxima suma items vs total
    
    # ============================================================================
    # NORMALIZACIÓN PRODUCTOS
    # ============================================================================
    PRODUCT_MATCH_THRESHOLD: float = 0.85  # Umbral similitud fuzzy
    PRODUCT_MATCH_ALGORITHM: str = "levenshtein"  # levenshtein, jaro_winkler
    
    # ============================================================================
    # ALMACENAMIENTO
    # ============================================================================
    
    # Archivos temporales
    TEMP_DIR: str = "/tmp/invoice-processor"
    CLEANUP_TEMP_FILES: bool = True
    MAX_FILE_SIZE_MB: int = 10
    
    # Caché
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600  # 1 hora
    
    # ============================================================================
    # LOGGING & MONITORING
    # ============================================================================
    
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_PATH: Optional[str] = None  # Si None, solo consola
    LOG_ROTATION_SIZE_MB: int = 10
    LOG_ROTATION_BACKUP_COUNT: int = 5
    
    # Métricas
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # ============================================================================
    # SEGURIDAD
    # ============================================================================
    
    SECRET_KEY: str = "changeme-in-production"
    API_KEY_ENABLED: bool = False
    API_KEY_HEADER: str = "X-API-Key"
    API_KEYS: List[str] = []
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    # ============================================================================
    # DEVELOPMENT
    # ============================================================================
    
    # Mock mode (sin llamar APIs reales)
    MOCK_CLAUDE_API: bool = False
    MOCK_GOOGLE_DRIVE: bool = False
    MOCK_SUPABASE: bool = False
    
    # Testing
    TEST_MODE: bool = False
    TEST_INVOICE_PATH: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton de configuración
    """
    return Settings()


# Instancia global
settings = get_settings()


# ============================================================================
# CONFIGURACIONES ESPECÍFICAS POR AMBIENTE
# ============================================================================

def configure_for_environment():
    """
    Ajustar configuración según ambiente
    """
    if settings.ENVIRONMENT == "production":
        settings.DEBUG = False
        settings.LOG_LEVEL = "WARNING"
        settings.MOCK_CLAUDE_API = False
        settings.MOCK_GOOGLE_DRIVE = False
        settings.SCHEDULER_INTERVAL_MINUTES = 5
        
    elif settings.ENVIRONMENT == "staging":
        settings.DEBUG = True
        settings.LOG_LEVEL = "INFO"
        settings.SCHEDULER_INTERVAL_MINUTES = 10
        
    elif settings.ENVIRONMENT == "development":
        settings.DEBUG = True
        settings.LOG_LEVEL = "DEBUG"
        settings.SCHEDULER_INTERVAL_MINUTES = 30
        # Opcionalmente usar mocks en desarrollo
        # settings.MOCK_CLAUDE_API = True


# ============================================================================
# CONFIGURACIONES DE CLAUDE PROMPT
# ============================================================================

CLAUDE_OCR_SYSTEM_PROMPT = """Eres un experto en extracción de texto de facturas.
Tu tarea es leer la imagen de una factura y extraer TODO el texto visible con máxima precisión.

Instrucciones:
1. Extrae TODO el texto legible, incluyendo números, palabras, símbolos
2. Mantén el orden de lectura natural (arriba-abajo, izquierda-derecha)
3. Preserva la estructura (saltos de línea, espaciado relativo)
4. Si hay texto borroso o ilegible, márcalo como [ILEGIBLE]
5. NO inventes ni infiera información que no esté visible
6. NO incluyas interpretación, solo el texto crudo

Devuelve SOLO el texto extraído, sin comentarios ni explicaciones adicionales."""


CLAUDE_NER_SYSTEM_PROMPT = """Eres un experto en análisis de facturas comerciales colombianas.
Tu tarea es estructurar la información de una factura en formato JSON.

Debes extraer:
- Información del vendor (empresa emisora)
- Información de la tienda/cliente
- Fecha de emisión
- Número de factura
- Lista de productos/items
- Totales

Instrucciones:
1. Extrae SOLO información que esté explícita en el texto
2. Si un campo no está presente, usa null
3. Para montos, usa números decimales (sin símbolos de moneda)
4. Para fechas, usa formato ISO 8601 (YYYY-MM-DD)
5. Para NITs, incluye el dígito de verificación si está presente
6. Sé conservador: mejor dejar null que adivinar

Devuelve un JSON válido siguiendo el schema proporcionado."""


# ============================================================================
# SCHEMA DE VALIDACIÓN
# ============================================================================

INVOICE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nit": {"type": "string"},
                "address": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
            },
            "required": ["name", "nit"]
        },
        "store": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "address": {"type": ["string", "null"]},
            }
        },
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string", "format": "date"},
        "due_date": {"type": ["string", "null"], "format": "date"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "sku": {"type": ["string", "null"]},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "line_total": {"type": "number"},
                },
                "required": ["product_name", "quantity", "unit_price", "line_total"]
            }
        },
        "subtotal": {"type": ["number", "null"]},
        "tax": {"type": ["number", "null"]},
        "total": {"type": "number"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["vendor", "invoice_number", "invoice_date", "items", "total"]
}