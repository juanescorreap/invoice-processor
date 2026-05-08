-- ============================================================================
-- SCHEMA DE BASE DE DATOS: Sistema de Procesamiento de Facturas
-- ============================================================================
-- Supabase PostgreSQL
-- Versión: 1.0
-- Fecha: 2026-05-08

-- ============================================================================
-- TABLA: vendors (proveedores)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    nit VARCHAR(20) UNIQUE NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vendors_nit ON vendors(nit);
CREATE INDEX idx_vendors_name ON vendors(name);

-- ============================================================================
-- TABLA: stores (tiendas/clientes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL, -- Código interno tienda
    address TEXT,
    city VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stores_code ON stores(code);

-- ============================================================================
-- TABLA: products (productos maestros)
-- ============================================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    master_name VARCHAR(255) NOT NULL, -- Nombre normalizado
    master_sku VARCHAR(100) UNIQUE NOT NULL, -- SKU interno
    category VARCHAR(100),
    unit VARCHAR(50), -- unidad, caja, kg, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_products_sku ON products(master_sku);
CREATE INDEX idx_products_name ON products(master_name);

-- ============================================================================
-- TABLA: product_mappings (diccionario de nombres/SKUs por vendor)
-- ============================================================================
CREATE TABLE IF NOT EXISTS product_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    vendor_name VARCHAR(255) NOT NULL, -- Nombre que usa el vendor
    vendor_sku VARCHAR(100), -- SKU que usa el vendor
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vendor_id, vendor_sku)
);

CREATE INDEX idx_mappings_product ON product_mappings(product_id);
CREATE INDEX idx_mappings_vendor ON product_mappings(vendor_id);
CREATE INDEX idx_mappings_vendor_name ON product_mappings(vendor_name);

-- ============================================================================
-- TABLA: invoices (facturas)
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificación
    invoice_number VARCHAR(100) NOT NULL,
    vendor_id UUID REFERENCES vendors(id),
    store_id UUID REFERENCES stores(id),
    
    -- Fechas
    invoice_date DATE NOT NULL,
    due_date DATE,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Montos
    subtotal DECIMAL(15,2),
    tax DECIMAL(15,2),
    total DECIMAL(15,2) NOT NULL,
    
    -- Metadata procesamiento
    source_file_path TEXT, -- Path en Google Drive
    source_file_id VARCHAR(255), -- ID de Google Drive
    confidence_score DECIMAL(5,4), -- 0.0000 a 1.0000
    processing_status VARCHAR(50) DEFAULT 'pending', -- pending, processed, error, manual_review
    error_message TEXT,
    
    -- Validación
    validated BOOLEAN DEFAULT FALSE,
    validated_by VARCHAR(255),
    validated_at TIMESTAMPTZ,
    
    -- OCR/NER results (JSON)
    raw_ocr_text TEXT,
    structured_data JSONB, -- Datos extraídos por Claude
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(vendor_id, invoice_number)
);

CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_vendor ON invoices(vendor_id);
CREATE INDEX idx_invoices_store ON invoices(store_id);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_status ON invoices(processing_status);
CREATE INDEX idx_invoices_source_file ON invoices(source_file_id);

-- ============================================================================
-- TABLA: invoice_items (líneas de factura)
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id), -- NULL si no se pudo mapear
    
    -- Datos originales del vendor
    vendor_product_name VARCHAR(255) NOT NULL,
    vendor_sku VARCHAR(100),
    
    -- Cantidades y precios
    quantity DECIMAL(15,3) NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    line_total DECIMAL(15,2) NOT NULL,
    
    -- Metadata
    line_number INTEGER, -- Orden en la factura
    matched BOOLEAN DEFAULT FALSE, -- Si se logró mapear a producto maestro
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_items_invoice ON invoice_items(invoice_id);
CREATE INDEX idx_items_product ON invoice_items(product_id);
CREATE INDEX idx_items_vendor_name ON invoice_items(vendor_product_name);

-- ============================================================================
-- TABLA: processing_log (auditoría)
-- ============================================================================
CREATE TABLE IF NOT EXISTS processing_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    
    event_type VARCHAR(50) NOT NULL, -- uploaded, ocr_started, ocr_completed, ner_started, ner_completed, validated, error
    status VARCHAR(50) NOT NULL, -- success, error, warning
    message TEXT,
    details JSONB, -- Información adicional
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_log_invoice ON processing_log(invoice_id);
CREATE INDEX idx_log_type ON processing_log(event_type);
CREATE INDEX idx_log_created ON processing_log(created_at);

-- ============================================================================
-- TABLA: processing_queue (cola de procesamiento)
-- ============================================================================
CREATE TABLE IF NOT EXISTS processing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    file_path TEXT NOT NULL,
    file_id VARCHAR(255) NOT NULL UNIQUE,
    file_name VARCHAR(255) NOT NULL,
    
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    priority INTEGER DEFAULT 0, -- Mayor = más prioridad
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    error_message TEXT,
    last_error_at TIMESTAMPTZ,
    
    scheduled_for TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_queue_status ON processing_queue(status);
CREATE INDEX idx_queue_scheduled ON processing_queue(scheduled_for);
CREATE INDEX idx_queue_file_id ON processing_queue(file_id);

-- ============================================================================
-- FUNCIONES: Triggers para updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger a todas las tablas con updated_at
CREATE TRIGGER update_vendors_updated_at BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stores_updated_at BEFORE UPDATE ON stores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_product_mappings_updated_at BEFORE UPDATE ON product_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoice_items_updated_at BEFORE UPDATE ON invoice_items
    FOR EACH ROW EXECUTE FUNCTION update_invoice_items_updated_at_column();

CREATE TRIGGER update_processing_queue_updated_at BEFORE UPDATE ON processing_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VISTAS: Consultas comunes
-- ============================================================================

-- Vista: Facturas con información completa
CREATE OR REPLACE VIEW invoices_detailed AS
SELECT 
    i.id,
    i.invoice_number,
    i.invoice_date,
    i.total,
    i.processing_status,
    i.confidence_score,
    i.validated,
    v.name as vendor_name,
    v.nit as vendor_nit,
    s.name as store_name,
    s.code as store_code,
    COUNT(DISTINCT ii.id) as items_count,
    i.created_at,
    i.updated_at
FROM invoices i
LEFT JOIN vendors v ON i.vendor_id = v.id
LEFT JOIN stores s ON i.store_id = s.id
LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
GROUP BY i.id, v.name, v.nit, s.name, s.code;

-- Vista: Items con productos mapeados
CREATE OR REPLACE VIEW invoice_items_detailed AS
SELECT 
    ii.id,
    ii.invoice_id,
    i.invoice_number,
    ii.vendor_product_name,
    ii.vendor_sku,
    p.master_name as product_name,
    p.master_sku as product_sku,
    ii.quantity,
    ii.unit_price,
    ii.line_total,
    ii.matched,
    ii.line_number
FROM invoice_items ii
JOIN invoices i ON ii.invoice_id = i.id
LEFT JOIN products p ON ii.product_id = p.id
ORDER BY i.invoice_date DESC, ii.line_number;

-- Vista: Resumen de procesamiento
CREATE OR REPLACE VIEW processing_summary AS
SELECT 
    DATE(created_at) as date,
    processing_status,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence,
    SUM(total) as total_amount
FROM invoices
GROUP BY DATE(created_at), processing_status
ORDER BY date DESC;

-- ============================================================================
-- DATOS SEED: Ejemplos iniciales (opcional)
-- ============================================================================

-- Vendors de ejemplo
INSERT INTO vendors (name, nit, address, phone, email) VALUES
('Proveedor Demo 1', '900123456-7', 'Calle 100 #10-20', '3001234567', 'contacto@proveedor1.com'),
('Proveedor Demo 2', '900654321-3', 'Carrera 50 #25-30', '3007654321', 'ventas@proveedor2.com')
ON CONFLICT (nit) DO NOTHING;

-- Stores de ejemplo
INSERT INTO stores (name, code, address, city) VALUES
('Tienda Centro', 'TC001', 'Calle 10 #5-15', 'Bogotá'),
('Tienda Norte', 'TN001', 'Calle 127 #20-30', 'Bogotá')
ON CONFLICT (code) DO NOTHING;

-- Productos maestros de ejemplo
INSERT INTO products (master_name, master_sku, category, unit) VALUES
('Producto A', 'PROD-A-001', 'Categoría 1', 'unidad'),
('Producto B', 'PROD-B-001', 'Categoría 2', 'caja')
ON CONFLICT (master_sku) DO NOTHING;

-- ============================================================================
-- POLÍTICAS RLS (Row Level Security) - Opcional para Supabase Auth
-- ============================================================================
-- Descomentarlas si usas autenticación de Supabase

-- ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Public read access" ON invoices FOR SELECT USING (true);
-- CREATE POLICY "Authenticated users can insert" ON invoices FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- ============================================================================
-- FIN DEL SCHEMA
-- ============================================================================