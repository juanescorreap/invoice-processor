# Plan de Implementación Detallado - 7 Días

## 📊 Estado Actual: DÍA 1 COMPLETADO ✅

### ✅ Completado Hoy (Día 1)

1. **Diseño de Arquitectura**
   - ✅ Stack tecnológico definido
   - ✅ Diagrama de arquitectura
   - ✅ Estimación de costos (~$1.30/mes)

2. **Base de Datos**
   - ✅ Schema SQL completo (`database/schema.sql`)
   - ✅ 9 tablas diseñadas
   - ✅ Índices optimizados
   - ✅ Triggers automáticos
   - ✅ Vistas para consultas comunes
   - ✅ Seeds de ejemplo

3. **Backend - Fundación**
   - ✅ Estructura de proyecto
   - ✅ Configuración (`app/config.py`)
   - ✅ Modelos Pydantic (`app/models.py`)
   - ✅ Sistema de logging (`app/utils/logger.py`)
   - ✅ Errores personalizados (`app/utils/errors.py`)
   - ✅ FastAPI app base (`app/main.py`)
   - ✅ Requirements.txt
   - ✅ .env.example

4. **Servicios Core**
   - ✅ OCR Service con Claude Vision (`app/services/ocr_service.py`)
   - ✅ NER Service con Claude Structured Outputs (`app/services/ner_service.py`)

5. **Documentación**
   - ✅ README completo
   - ✅ Prompts de Claude optimizados
   - ✅ JSON Schema para validación

---

## 🎯 DÍA 2: Infraestructura y Database Service

### Objetivos
- Conectar Supabase
- Crear servicio de base de datos
- Implementar CRUD básico
- Testing de servicios OCR/NER

### Tareas Detalladas

#### 1. Setup Supabase (2 horas)
```bash
# Acciones:
1. Crear proyecto en Supabase
2. Ejecutar schema.sql
3. Insertar datos de prueba (vendors, stores, products)
4. Configurar Row Level Security (opcional)
5. Obtener credenciales y actualizar .env
```

#### 2. Database Service (3 horas)
Crear: `app/services/database_service.py`
```python
class DatabaseService:
    - connect() / disconnect()
    - create_invoice()
    - get_invoice()
    - update_invoice()
    - list_invoices()
    - create_vendor() / get_vendor_by_nit()
    - create_store() / get_store_by_code()
    - create_product()
    - create_product_mapping()
    - get_product_mapping()
    - add_to_queue()
    - get_queue_items()
    - log_event()
```

#### 3. Testing (2 horas)
Crear: `backend/tests/`
```bash
tests/
├── test_ocr_service.py
├── test_ner_service.py
├── test_database_service.py
└── conftest.py  # fixtures
```

Casos de prueba:
- OCR con factura real
- NER con texto OCR real
- CRUD operations en Supabase
- Error handling

#### 4. Integration Test (1 hora)
Pipeline completo:
```
PDF → OCR → NER → Database
```

**Entregable Día 2:**
- ✅ Supabase configurado
- ✅ Database service funcional
- ✅ Tests pasando
- ✅ Pipeline básico funcionando

---

## 🎯 DÍA 3: Normalización y Google Drive

### Objetivos
- Servicio de normalización de productos
- Integración Google Drive
- Sistema de colas funcional

### Tareas Detalladas

#### 1. Normalization Service (3 horas)
Crear: `app/services/normalization_service.py`
```python
class NormalizationService:
    - normalize_vendor(ner_response) → vendor_id
    - normalize_store(ner_response) → store_id
    - normalize_products(items: List[ItemExtracted]) → List[product_id]
    - fuzzy_match_product(vendor_name, vendor_id) → product_id
    - create_mapping_if_not_exists()
```

Estrategias:
1. Búsqueda exacta por vendor_sku
2. Fuzzy matching por nombre
3. Manual review si no hay match

#### 2. Google Drive Service (3 horas)
Crear: `app/services/gdrive_service.py`
```python
class GoogleDriveService:
    - authenticate()
    - list_files_in_folder(folder_id) → List[file_metadata]
    - download_file(file_id, destination_path)
    - get_file_metadata(file_id)
    - watch_folders() → List[new_files]
```

Setup:
1. Crear proyecto en Google Cloud
2. Habilitar Drive API
3. Descargar credentials.json
4. Implementar OAuth flow

#### 3. Queue Service (2 horas)
Crear: `app/services/queue_service.py`
```python
class QueueService:
    - add_to_queue(file_path, priority)
    - get_next_items(limit) → List[QueueItem]
    - mark_processing(queue_id)
    - mark_completed(queue_id, invoice_id)
    - mark_failed(queue_id, error_message)
    - retry_failed(queue_id)
```

**Entregable Día 3:**
- ✅ Productos normalizados
- ✅ Google Drive conectado
- ✅ Cola de procesamiento funcionando

---

## 🎯 DÍA 4: Processing Pipeline y Worker

### Objetivos
- Orquestador de procesamiento completo
- Worker asíncrono
- Scheduler automático

### Tareas Detalladas

#### 1. Processing Service (4 horas)
Crear: `app/services/processing_service.py`
```python
class ProcessingService:
    async def process_invoice(file_path) → Invoice:
        1. Validar archivo
        2. OCR (Claude Vision)
        3. NER (Claude Structured)
        4. Normalización
        5. Validación
        6. Guardar en DB
        7. Logging
        8. Return Invoice
```

Features:
- Error handling robusto
- Retry logic
- Confidence scoring
- Manual review flagging

#### 2. Worker (2 horas)
Crear: `app/workers/invoice_worker.py`
```python
class InvoiceWorker:
    - async run() # loop infinito
    - process_queue_items()
    - handle_success()
    - handle_error()
    - respect_concurrency_limits()
```

#### 3. Scheduler (2 horas)
Crear: `app/workers/scheduler.py`
```python
class DriveScheduler:
    - scan_google_drive()
    - add_new_files_to_queue()
    - run every N minutes
```

Usar APScheduler para scheduling.

**Entregable Día 4:**
- ✅ Pipeline completo funcionando
- ✅ Worker procesando automáticamente
- ✅ Scheduler monitoreando Drive

---

## 🎯 DÍA 5: REST API

### Objetivos
- Endpoints CRUD completos
- Validación manual
- Filtros y búsqueda

### Tareas Detalladas

#### 1. Invoices Router (3 horas)
Crear: `app/routers/invoices.py`
```python
GET    /api/invoices         # List con filtros
GET    /api/invoices/{id}    # Detail
POST   /api/invoices/process # Manual upload
PATCH  /api/invoices/{id}    # Update
DELETE /api/invoices/{id}    # Delete
PATCH  /api/invoices/{id}/validate  # Marcar validado
GET    /api/invoices/{id}/logs      # Processing logs
```

#### 2. CRUD Routers (3 horas)
```python
app/routers/vendors.py    # CRUD vendors
app/routers/stores.py     # CRUD stores
app/routers/products.py   # CRUD products + mappings
```

#### 3. Queue & Dashboard Routers (2 horas)
```python
app/routers/queue.py      # Ver cola, retry, clear
app/routers/dashboard.py  # Métricas, stats
```

**Entregable Día 5:**
- ✅ API REST completa
- ✅ Documentación Swagger
- ✅ Testing de endpoints

---

## 🎯 DÍA 6: Frontend - Dashboard React

### Objetivos
- Setup React + Tailwind
- Tabla de facturas
- Vista de detalle
- Corrección manual

### Tareas Detalladas

#### 1. Setup (1 hora)
```bash
cd frontend
npx create-react-app . --template typescript
npm install axios @tanstack/react-query recharts
npm install -D tailwindcss postcss autoprefixer
```

#### 2. Services Layer (1 hora)
```typescript
frontend/src/services/
├── api.ts           # Axios client
├── invoices.ts      # Invoice endpoints
├── vendors.ts
└── products.ts
```

#### 3. Components (4 horas)
```typescript
src/components/
├── InvoiceTable.tsx        # Tabla con filtros
├── InvoiceDetail.tsx       # Vista detalle + edición
├── InvoiceStats.tsx        # Cards con métricas
├── ProductMapping.tsx      # Mapeo productos
└── ProcessingLogs.tsx      # Logs de procesamiento
```

#### 4. Pages (2 horas)
```typescript
src/pages/
├── Dashboard.tsx           # Home con stats
├── InvoicesList.tsx        # Lista facturas
└── InvoiceDetailPage.tsx   # Detalle completo
```

**Entregable Día 6:**
- ✅ Dashboard funcional
- ✅ Tabla con filtros
- ✅ Edición manual

---

## 🎯 DÍA 7: Testing, Refinamiento y Deploy

### Objetivos
- Testing end-to-end
- Refinamiento UX
- Deploy en producción
- Documentación final

### Tareas Detalladas

#### 1. Testing (3 horas)
- E2E tests con factura real
- Performance testing (200 facturas)
- Error scenarios
- Manual review workflow

#### 2. Refinamiento (2 horas)
- UI polish
- Error messages
- Loading states
- Validaciones frontend

#### 3. Deploy (2 horas)
```bash
Backend:  Railway / Render (gratis)
Frontend: Vercel / Netlify (gratis)
Database: Supabase (ya está cloud)
```

#### 4. Documentación (1 hora)
- Guía de setup
- Guía de uso
- API docs
- Troubleshooting

**Entregable Día 7:**
- ✅ Sistema completo en producción
- ✅ Documentación completa
- ✅ Ready para usar

---

## 📦 Estructura Final del Proyecto

```
invoice-processor/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── routers/
│   │   │   ├── invoices.py
│   │   │   ├── vendors.py
│   │   │   ├── stores.py
│   │   │   ├── products.py
│   │   │   ├── queue.py
│   │   │   └── dashboard.py
│   │   ├── services/
│   │   │   ├── ocr_service.py
│   │   │   ├── ner_service.py
│   │   │   ├── database_service.py
│   │   │   ├── normalization_service.py
│   │   │   ├── gdrive_service.py
│   │   │   ├── queue_service.py
│   │   │   └── processing_service.py
│   │   ├── workers/
│   │   │   ├── invoice_worker.py
│   │   │   └── scheduler.py
│   │   └── utils/
│   │       ├── logger.py
│   │       ├── errors.py
│   │       └── validators.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── .env.example
│
├── database/
│   ├── schema.sql
│   ├── migrations/
│   └── seeds/
│
├── docs/
│   ├── SETUP.md
│   ├── API.md
│   └── DEPLOYMENT.md
│
├── .gitignore
└── README.md
```

---

## 🚀 Cómo Continuar

### Día 2 (Mañana)
```bash
# 1. Crear proyecto Supabase
# 2. Ejecutar schema.sql
# 3. Implementar database_service.py
# 4. Testing OCR + NER con facturas reales
```

### Costos Reales
- Claude API: $1.30/mes (200 facturas)
- Supabase: Gratis
- Google Drive: Gratis
- Deploy: Gratis (Railway + Vercel)
**Total: ~$1.30/mes**

### Métricas de Éxito
- ✅ 95%+ accuracy en extracción
- ✅ <5 segundos por factura
- ✅ 200 facturas/mes sin intervención
- ✅ <5% requieren corrección manual