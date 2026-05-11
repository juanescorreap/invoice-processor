# Sistema de Procesamiento Automatizado de Facturas

Sistema robusto para procesamiento inteligente de facturas mediante Claude AI, con almacenamiento en Supabase y dashboard React.

## 📋 Características

- ✅ Extracción OCR con Claude Vision
- ✅ Clasificación NER con Claude Structured Outputs
- ✅ Normalización de productos multi-vendor
- ✅ Sistema de colas con retry logic
- ✅ Dashboard interactivo con métricas
- ✅ Validación y corrección manual
- ✅ Integración Google Drive
- ✅ Auditoría completa

## 🏗️ Arquitectura

```
invoice-processor/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings
│   │   ├── database.py        # Supabase client
│   │   ├── models/            # Pydantic models
│   │   ├── services/          # Business logic
│   │   │   ├── ocr_service.py
│   │   │   ├── ner_service.py
│   │   │   ├── normalization_service.py
│   │   │   └── gdrive_service.py
│   │   ├── routers/           # API endpoints
│   │   ├── workers/           # Background tasks
│   │   └── utils/             # Helpers
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # React dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── .env.example
│
├── database/
│   ├── schema.sql             # Base schema
│   ├── migrations/            # DB migrations
│   └── seeds/                 # Seed data
│
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   ├── API_DOCS.md
│   └── DEPLOYMENT.md
│
├── docker-compose.yml         # Local development
└── README.md
```

## 🚀 Stack Tecnológico

### Backend
- **FastAPI**: Framework web async
- **Anthropic Claude**: OCR + NER
- **Supabase**: PostgreSQL + Auth
- **Google Drive API**: Ingesta documentos
- **APScheduler**: Tareas programadas
- **Pydantic**: Validación de datos

### Frontend
- **React 18**: UI framework
- **Recharts**: Visualizaciones
- **TanStack Query**: Data fetching
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

## 📦 Instalación Rápida

### 1. Clonar y Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

**Variables requeridas:**
```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Google Drive API
GOOGLE_DRIVE_CREDENTIALS_PATH=./credentials.json
GOOGLE_DRIVE_FOLDER_IDS=["folder_id_1", "folder_id_2"]

# App Config
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3. Crear Base de Datos

```bash
# En Supabase Dashboard, ejecutar:
database/schema.sql
```

### 4. Iniciar Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📊 Costos Estimados

### Claude API (200 facturas/mes)
- **OCR (Vision)**: 200 × $0.0035 = **$0.70/mes**
- **NER (Structured)**: 200 × $0.003 = **$0.60/mes**
- **Total**: **~$1.30/mes**

### Infraestructura
- **Supabase**: Gratis (hasta 500MB DB)
- **Google Drive API**: Gratis
- **Hosting**: Gratis (Vercel/Netlify + Railway)

**Costo total mensual: ~$1.30** ✅

## 🗓️ Plan de Implementación (7 días)

### Día 1: Fundación
- [x] Schema base de datos
- [ ] Setup proyecto backend
- [ ] Configuración Supabase
- [ ] Setup Google Drive API

### Día 2: Servicios Core
- [ ] OCR service (Claude Vision)
- [ ] NER service (Claude Structured)
- [ ] Database service (Supabase)
- [ ] Tests unitarios

### Día 3: Procesamiento
- [ ] Sistema de colas
- [ ] Worker de procesamiento
- [ ] Normalización productos
- [ ] Retry logic

### Día 4: API REST
- [ ] Endpoints CRUD
- [ ] Ingesta manual
- [ ] Scheduler Google Drive
- [ ] Validación manual

### Día 5-6: Dashboard
- [ ] Setup React
- [ ] Tabla facturas
- [ ] Dashboard métricas
- [ ] Corrección manual

### Día 7: Testing & Deploy
- [ ] Tests integración
- [ ] Documentación
- [ ] Deploy Vercel + Railway
- [ ] Monitoreo

## 📝 Uso

### Procesamiento Automático

El sistema monitoreará automáticamente las carpetas de Google Drive configuradas cada 5 minutos:

```python
# Se ejecuta automáticamente
# No requiere intervención manual
```

### API Manual

```bash
# Procesar factura individual
curl -X POST "http://localhost:8000/api/invoices/process" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "path/to/invoice.pdf"}'

# Listar facturas
curl "http://localhost:8000/api/invoices?status=processed"

# Validar factura
curl -X PATCH "http://localhost:8000/api/invoices/{id}/validate" \
  -H "Content-Type: application/json" \
  -d '{"validated": true}'
```

### Dashboard

```
http://localhost:3000
```

Funciones:
- Ver facturas procesadas
- Filtrar por fecha, vendor, tienda
- Corregir errores manualmente
- Ver métricas de procesamiento
- Exportar datos

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

## 🔒 Seguridad

- ✅ API keys en variables de entorno
- ✅ Row Level Security en Supabase
- ✅ Validación de inputs con Pydantic
- ✅ Rate limiting en API
- ✅ Logs de auditoría completos

## 📈 Monitoreo

El sistema registra:
- Tasa de éxito/error
- Tiempo de procesamiento
- Confidence scores
- Productos sin mapear
- Errores de validación

## 🛠️ Troubleshooting

### Error: "Claude API rate limit"
```bash
# Reducir workers concurrentes en config.py
MAX_CONCURRENT_WORKERS = 2  # default: 5
```

### Error: "Google Drive authentication"
```bash
# Regenerar credentials.json desde Google Cloud Console
# Verificar scopes: drive.readonly
```

### Error: "Supabase connection timeout"
```bash
# Verificar firewall
# Revisar SUPABASE_URL en .env
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

MIT License - ver `LICENSE` para detalles

## 👥 Autores

- Juan Esteban Correa Pérez

## 🙏 Agradecimientos

- Anthropic Claude API
- Supabase
- FastAPI
- React

---

**Estado**: 🚧 En desarrollo activo (Día 1/7)



# Invoice Processor

Sistema automatizado de procesamiento de facturas con IA usando Claude API.

## 🌐 URLs de Producción

- **Dashboard:** https://invoice-proceappr-r3jihrpwd6abxuarcahyh2.streamlit.app
- **Backend API:** https://invoice-processor-production-7d77.up.railway.app
- **API Docs:** https://invoice-processor-production-7d77.up.railway.app/docs

## 📊 Estado del Sistema

✅ **Backend API:** Online en Railway  
✅ **Dashboard:** Online en Streamlit Cloud  
✅ **Database:** Supabase PostgreSQL  
✅ **AI Engine:** Claude API (claude-sonnet-4-6)  
✅ **Storage:** Google Drive (OAuth)

## 💰 Costos Mensuales

- Railway Backend: **$0** (free tier - 500 horas/mes)
- Streamlit Dashboard: **$0** (free tier)
- Supabase Database: **$0** (free tier)
- Claude API: **~$1.40** (200 facturas/mes)
- **Total: $1.40/mes**

## 🚀 Uso del Sistema

### Dashboard Web
Visita: https://invoice-proceappr-r3jihrpwd6abxuarcahyh2.streamlit.app

- Ver facturas procesadas en tiempo real
- Filtrar por proveedor, tienda, fecha, estado
- Cargar precios acordados (CSV/Excel)
- Alertas automáticas de precios altos
- Exportar a Excel

### API REST
Base URL: https://invoice-processor-production-7d77.up.railway.app

**Endpoints principales:**
- `POST /api/invoices/process` - Procesar factura PDF
- `GET /api/invoices/` - Listar facturas
- `GET /api/invoices/{id}` - Detalle de factura
- `GET /docs` - Documentación interactiva