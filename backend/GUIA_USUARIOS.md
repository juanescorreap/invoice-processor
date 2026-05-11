# 📖 Guía de Uso - Invoice Processor

## 🚀 Acceso al Sistema

**Dashboard:** https://invoice-proceappr-r3jihrpwd6abxuarcahyh2.streamlit.app

## 📤 Cómo Subir Facturas

1. Abre la carpeta de Google Drive compartida
2. **Arrastra y suelta** los PDFs de facturas a la carpeta
3. **Espera 1-2 minutos** - el sistema procesa automáticamente
4. **Refresca el dashboard** para ver los resultados

## 💰 Configurar Alertas de Precios

1. En el dashboard, busca la sección **"💰 Precios Acordados"**
2. Click en **"Browse files"**
3. Selecciona tu archivo CSV o Excel con los precios
4. El archivo debe tener estas columnas:
   - **Razón Social** (nombre exacto del vendor)
   - **Código Item** (SKU del producto)
   - **Precio Acordado por Case**

### Ejemplo de archivo CSV:

```csv
Razón Social,Código Item,Precio Acordado por Case
Primizie Foods CA,1223,60.00
Primizie Foods CA,1222,50.00
Distribuidora ABC,ABC-001,2400.00
```

5. Las filas con **fondo rojo** = precio mayor al acordado ⚠️

## 🔍 Filtros Disponibles

- **Proveedor:** Filtrar por vendor específico
- **Tienda:** Filtrar por tienda
- **Estado:** Filtrar por estado de procesamiento
- **Fecha:** Seleccionar rango de fechas

## 📥 Exportar Datos

1. Aplica los filtros que necesites
2. Scroll hasta el final de la página
3. Click en **"📥 Descargar como Excel"**
4. El archivo se descarga automáticamente

## ⚠️ Solución de Problemas

### "No veo mis facturas"
- Espera 2 minutos después de subirlas
- Refresca la página del dashboard
- Verifica que los PDFs estén en la carpeta correcta

### "Las alertas no funcionan"
- Verifica que los nombres de vendors coincidan exactamente
- Verifica que los códigos de item sean correctos
- Usa el formato CSV del ejemplo

### "La factura no se procesó correctamente"
- El PDF debe ser legible (no escaneos de muy baja calidad)
- El PDF debe ser una factura real con estructura clara
- Contacta al administrador si persiste el problema

## 📊 Información Mostrada

Para cada factura verás:
- **Estado** de procesamiento
- **Tienda** y código de tienda
- **Fecha**, semana, mes, quarter, año
- **Número de factura**
- **Proveedor** (Razón Social y NIT)
- **Código del item** y nombre
- **Cantidades** (cases, unidades por case, total unidades)
- **Precios** (por case, por unidad, total)
- **Confidence score** (qué tan seguro está el sistema)

## 🎯 Mejores Prácticas

1. **Sube facturas regularmente** - el sistema procesa automáticamente
2. **Mantén actualizado el archivo de precios** - súbelo cada vez que cambien
3. **Revisa las alertas** - facturas rojas requieren atención
4. **Exporta reportes** - descarga Excel para análisis externo
5. **Reporta problemas** - si algo no se procesa bien, avisa al admin

## 📞 Soporte

Para problemas técnicos o dudas, contacta al administrador del sistema.