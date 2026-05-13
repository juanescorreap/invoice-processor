"""
Invoice Processor Dashboard - Streamlit App
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

# Configuración de página
st.set_page_config(
    page_title="Invoice Processor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar Supabase
@st.cache_resource
def init_supabase():
    """Inicializar cliente Supabase"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    return create_client(url, key)

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Título principal
st.title("📊 Invoice Processor Dashboard")
st.markdown("---")
# ============================================================================
# FUNCIONES DE CARGA DE DATOS
# ============================================================================

@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_invoices():
    """
    Cargar facturas con items desde Supabase
    """
    client = init_supabase()
    
    # Query complejo: invoices + items + vendors + stores
    result = client.table('invoice_items').select(
        '''
        *,
        invoices!inner(
            id,
            invoice_number,
            invoice_date,
            total,
            processing_status,
            confidence_score,
            vendors!inner(name, nit),
            stores(name, code)
        )
        '''
    ).execute()
    
    return result.data

def process_invoice_data(raw_data):
    """
    Procesar datos y agregar campos calculados
    """
    if not raw_data:
        return pd.DataFrame()
    
    # Convertir a DataFrame
    rows = []
    for item in raw_data:
        invoice = item['invoices']
        vendor = invoice['vendors']
        store = invoice.get('stores')
        
        # Calcular campos
        invoice_date = pd.to_datetime(invoice['invoice_date'])
        
        row = {
            # Info de Invoice
            'Estado': invoice['processing_status'],
            'Tienda': store['name'] if store else 'N/A',
            'Código Tienda': store['code'] if store else 'N/A',
            'Fecha': invoice_date.strftime('%Y-%m-%d'),
            'Semana': invoice_date.isocalendar()[1],
            'Mes': invoice_date.strftime('%B'),
            'Mes #': invoice_date.month,
            'Quarter': f"Q{(invoice_date.month - 1) // 3 + 1}",
            'Año': invoice_date.year,
            
            # Info de Vendor
            'Razón Social': vendor['name'],
            'NIT': vendor['nit'],
            
            # Info de Invoice
            'Invoice #': invoice['invoice_number'],
            'Confidence': f"{invoice['confidence_score']:.0%}",
            
            # Info de Item
            'Código Item': item.get('vendor_sku', 'N/A'),
            'Nombre Item': item['vendor_product_name'],
            'Cases Ordered': item['quantity'],
            'Unidades por Case': 1,  # TODO: agregar a modelo
            'Unidades Totales': item['quantity'] * 1,
            'Precio por Case': item['unit_price'],
            'Precio por Unidad': item['unit_price'] / 1,
            'Precio Total': item['line_total'],
            
            # IDs para joins
            '_invoice_id': invoice['id'],
            '_item_id': item['id']
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    return df

# ============================================================================
# SIDEBAR - FILTROS
# ============================================================================

st.sidebar.header("🔍 Filtros")

# Cargar datos
with st.spinner("Cargando datos..."):
    raw_data = load_invoices()
    df = process_invoice_data(raw_data)

if df.empty:
    st.warning("No hay facturas procesadas aún.")
    st.stop()

st.sidebar.success(f"✅ {len(df)} items cargados")
# Filtros
st.sidebar.markdown("---")

# Filtro por Vendor
vendors = ['Todos'] + sorted(df['Razón Social'].unique().tolist())
selected_vendor = st.sidebar.selectbox("Proveedor", vendors)

# Filtro por Tienda
stores = ['Todos'] + sorted(df['Tienda'].dropna().unique().tolist())
selected_store = st.sidebar.selectbox("Tienda", stores)

# Filtro por Estado
estados = ['Todos'] + sorted(df['Estado'].unique().tolist())
selected_estado = st.sidebar.selectbox("Estado", estados)

# Filtro por Fecha
st.sidebar.markdown("**Rango de Fechas**")
df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
min_date = df['Fecha_dt'].min().date()
max_date = df['Fecha_dt'].max().date()

date_from = st.sidebar.date_input("Desde", min_date, min_value=min_date, max_value=max_date)
date_to = st.sidebar.date_input("Hasta", max_date, min_value=min_date, max_value=max_date)

# Aplicar filtros
df_filtered = df.copy()

if selected_vendor != 'Todos':
    df_filtered = df_filtered[df_filtered['Razón Social'] == selected_vendor]

if selected_store != 'Todos':
    df_filtered = df_filtered[df_filtered['Tienda'] == selected_store]

if selected_estado != 'Todos':
    df_filtered = df_filtered[df_filtered['Estado'] == selected_estado]

df_filtered = df_filtered[
    (df_filtered['Fecha_dt'].dt.date >= date_from) &
    (df_filtered['Fecha_dt'].dt.date <= date_to)
]

st.sidebar.markdown("---")
st.sidebar.metric("Items Filtrados", len(df_filtered))

# ============================================================================
# MAIN CONTENT - UPLOAD DE PRECIOS ACORDADOS
# ============================================================================

st.header("💰 Precios Acordados")

uploaded_file = st.file_uploader(
    "Cargar archivo de precios acordados (CSV o Excel)",
    type=['csv', 'xlsx'],
    help="El archivo debe tener las columnas: Razón Social, Código Item, Precio Acordado por Case"
)

df_precios = None

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_precios = pd.read_csv(uploaded_file)
        else:
            df_precios = pd.read_excel(uploaded_file)
        
        st.success(f"✅ Archivo cargado: {len(df_precios)} precios acordados")
        
        with st.expander("Ver precios cargados"):
            st.dataframe(df_precios, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error cargando archivo: {e}")

st.markdown("---")
# ============================================================================
# TABLA PRINCIPAL CON ALERTAS
# ============================================================================

st.header("📋 Facturas Procesadas")

# Métricas resumen
col1, col2, col3, col4, col5 = st.columns(5)

# Métricas resumen
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Items", len(df_filtered))

with col2:
    total_amount = df_filtered['Precio Total'].sum()
    st.metric("Monto Total", f"${total_amount:,.2f}")

with col3:
    avg_price = df_filtered['Precio por Case'].mean()
    st.metric("Precio Promedio/Case", f"${avg_price:,.2f}")

with col4:
    unique_invoices = df_filtered['Invoice #'].nunique()
    st.metric("Facturas Únicas", unique_invoices)

st.markdown("---")

# Búsqueda
search = st.text_input("🔍 Buscar en tabla", placeholder="Buscar por nombre de item, invoice #, etc.")

df_display = df_filtered.copy()

if search:
    mask = df_display.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
    df_display = df_display[mask]

# Comparar con precios acordados y marcar alertas
df_display['⚠️ Alerta'] = ''

if df_precios is not None:
    # Hacer merge con precios acordados
    df_precios_clean = df_precios.rename(columns={
        df_precios.columns[0]: 'Razón Social',
        df_precios.columns[1]: 'Código Item', 
        df_precios.columns[2]: 'Precio Acordado'
    })
    
    # Convertir columnas a string para el merge
    df_display['Código Item'] = df_display['Código Item'].astype(str)
    df_precios_clean['Código Item'] = df_precios_clean['Código Item'].astype(str)
    
    df_display = df_display.merge(
        df_precios_clean[['Razón Social', 'Código Item', 'Precio Acordado']],
        on=['Razón Social', 'Código Item'],
        how='left'
    )  
    
    # Marcar alertas
    df_display['⚠️ Alerta'] = df_display.apply(
        lambda row: '🔴 PRECIO ALTO' if pd.notna(row.get('Precio Acordado')) and row['Precio por Case'] > row['Precio Acordado'] else '',
        axis=1
    )
    
# Mostrar métrica de alertas
    alertas = (df_display['⚠️ Alerta'] == '🔴 PRECIO ALTO').sum()
    if alertas > 0:
        st.warning(f"🚨 **{alertas} items con precio por encima del acordado**")

# Ordenar columnas para display
columns_order = [
    '⚠️ Alerta',
    'Estado',
    'Tienda',
    'Código Tienda',
    'Fecha',
    'Semana',
    'Mes',
    'Quarter',
    'Año',
    'Invoice #',
    'Razón Social',
    'NIT',
    'Código Item',
    'Nombre Item',
    'Cases Ordered',
    'Unidades por Case',
    'Unidades Totales',
    'Precio por Case',
    'Precio por Unidad',
    'Precio Total',
    'Confidence'
]

# Agregar Precio Acordado si existe
if 'Precio Acordado' in df_display.columns:
    columns_order.insert(columns_order.index('Precio por Case'), 'Precio Acordado')

# Filtrar solo columnas que existen
columns_order = [col for col in columns_order if col in df_display.columns]

df_display = df_display[columns_order]

# Función para aplicar estilos
def highlight_alerts(row):
    if row['⚠️ Alerta'] == '🔴 PRECIO ALTO':
        return ['background-color: #ffcccc'] * len(row)
    return [''] * len(row)

# Mostrar tabla con estilos
st.dataframe(
    df_display.style.apply(highlight_alerts, axis=1),
    use_container_width=True,
    height=600
)

# Exportar a Excel
st.markdown("---")
st.subheader("📥 Exportar Datos")

# Convertir a Excel en memoria
from io import BytesIO

output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_display.to_excel(writer, index=False, sheet_name='Facturas')

excel_data = output.getvalue()

st.download_button(
    label="📥 Descargar como Excel",
    data=excel_data,
    file_name=f"facturas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)