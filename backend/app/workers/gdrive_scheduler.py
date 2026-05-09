"""
Google Drive Scheduler - Monitoreo automático de carpetas
"""
import asyncio
import tempfile
import os
from typing import List, Dict
from pathlib import Path

from app.services.gdrive_service import get_gdrive_service
from app.services.processing_service import ProcessingService
from app.services.database_service import DatabaseService
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GDriveScheduler:
    """
    Scheduler para monitorear carpetas de Google Drive
    y procesar archivos nuevos automáticamente
    """
    
    def __init__(self):
        """Inicializar scheduler"""
        self.gdrive = get_gdrive_service()
        self.processor = ProcessingService()
        self.db = DatabaseService()
        logger.info("GDriveScheduler inicializado")
    
    def get_processed_file_ids(self) -> List[str]:
        """
        Obtener IDs de archivos ya procesados
        """
        try:
            result = self.db.client.table('invoices')\
                .select('source_file_id')\
                .not_.is_('source_file_id', 'null')\
                .execute()
            
            file_ids = [row['source_file_id'] for row in result.data if row['source_file_id']]
            logger.info(f"📊 {len(file_ids)} archivos ya procesados")
            return file_ids
            
        except Exception as e:
            logger.error(f"Error obteniendo archivos procesados: {e}")
            return []
    
    async def scan_and_process(self):
        """
        Escanear carpetas y procesar archivos nuevos
        """
        logger.info("="*60)
        logger.info("🔍 Iniciando escaneo de Google Drive...")
        logger.info("="*60)
        
        try:
            # Obtener archivos ya procesados
            processed_ids = self.get_processed_file_ids()
            
            # Obtener archivos nuevos
            folder_ids = settings.GOOGLE_DRIVE_FOLDER_IDS
            new_files = self.gdrive.get_new_files(
                folder_ids=folder_ids,
                processed_file_ids=processed_ids
            )
            
            if not new_files:
                logger.info("✅ No hay archivos nuevos")
                return
            
            logger.info(f"📥 {len(new_files)} archivos nuevos encontrados")
            
            # Procesar cada archivo
            for file in new_files:
                await self._process_file(file)
            
            logger.info("="*60)
            logger.info("✅ Escaneo completado")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error en scan_and_process: {e}", exc_info=True)
    
    async def _process_file(self, file: Dict):
        """
        Descargar y procesar archivo individual
        """
        file_id = file['id']
        file_name = file['name']
        
        logger.info(f"\n📄 Procesando: {file_name}")
        logger.info(f"   ID: {file_id}")
        
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file_name)
        
        try:
            # 1. Descargar archivo
            logger.info("   1/2 Descargando...")
            self.gdrive.download_file(file_id, temp_path)
            
            # 2. Procesar
            logger.info("   2/2 Procesando...")
            result = await self.processor.process_file(
                file_path=temp_path,
                file_id=file_id,
                source="google_drive"
            )
            
            # Resultado
            if result['success']:
                logger.info(f"   ✅ Éxito: Invoice {result['invoice_id']}")
            else:
                logger.error(f"   ❌ Error: {result['errors']}")
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"   ❌ Error procesando {file_name}: {e}")
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass


async def run_scheduler_once():
    """
    Ejecutar scheduler una vez (para testing)
    """
    scheduler = GDriveScheduler()
    await scheduler.scan_and_process()


if __name__ == "__main__":
    # Para testing: ejecutar una vez
    asyncio.run(run_scheduler_once())