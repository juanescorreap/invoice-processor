# Invoice Processor Dashboard

Dashboard interactivo con Streamlit para visualizar y analizar facturas procesadas.

## Características

### 📊 Tabla Interactiva
- Estado, Tienda, Fecha, Semana, Mes, Quarter
- Invoice #, Razón Social, NIT
- Código Item, Nombre Item
- Cases Ordered, Unidades por Case, Unidades Totales
- Precio por Case, Precio por Unidad, Precio Total
- Confidence score

### 🔍 Filtros
- Proveedor
- Tienda
- Estado de procesamiento
- Rango de fechas

### 💰 Alertas de Precios
- Carga archivo CSV/Excel con precios acordados
- Filas rojas automáticas cuando precio > acordado
- Columnas requeridas: `Razón Social`, `Código Item`, `Precio Acordado por Case`

### 📈 Métricas
- Total items
- Monto total
- Precio promedio por case
- Facturas únicas
- Alertas de precio

### 🔎 Búsqueda
- Búsqueda global en toda la tabla

### 📥 Exportar
- Descarga datos filtrados a Excel

## Uso

### Ejecutar localmente

```bash
cd ~/invoice-processor/backend
source venv/bin/activate
streamlit run dashboard/app.py
```

Abre en navegador: http://localhost:8501

### Cargar Precios Acordados

1. Crea archivo CSV o Excel con columnas:
   - `Razón Social` (debe coincidir exactamente con BD)
   - `Código Item` (SKU del vendor)
   - `Precio Acordado por Case`

2. En dashboard, sección "💰 Precios Acordados", click "Browse files"

3. Selecciona tu archivo

4. Items con precio mayor aparecerán con fondo rojo

### Ejemplo de archivo de precios:

```csv
Razón Social,Código Item,Precio Acordado por Case
Primizie Foods CA,1223,60.00
Primizie Foods CA,1222,50.00
Distribuidora ABC,N/A,2400
```

## Deploy (Opcional)

### Streamlit Cloud (Gratis)

1. Push código a GitHub
2. Ve a https://streamlit.io/cloud
3. Conecta repositorio
4. Configura secrets en Settings:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
5. Deploy automático

## Requisitos

- Python 3.11+
- streamlit
- pandas
- openpyxl
- supabase
- python-dotenv