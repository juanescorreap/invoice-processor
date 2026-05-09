"""
Continuous Scheduler - Ejecutar escaneo periódicamente
"""
import asyncio
import time
from datetime import datetime

from app.workers.gdrive_scheduler import GDriveScheduler
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def run_continuous():
    """
    Ejecutar scheduler continuamente cada N minutos
    """
    scheduler = GDriveScheduler()
    interval_seconds = settings.SCHEDULER_INTERVAL_MINUTES * 60
    
    logger.info("="*60)
    logger.info("🤖 Scheduler Continuo Iniciado")
    logger.info(f"   Intervalo: {settings.SCHEDULER_INTERVAL_MINUTES} minutos")
    logger.info("   Presiona Ctrl+C para detener")
    logger.info("="*60)
    
    while True:
        try:
            # Ejecutar escaneo
            await scheduler.scan_and_process()
            
            # Esperar hasta próxima ejecución
            logger.info(f"\n⏰ Próximo escaneo en {settings.SCHEDULER_INTERVAL_MINUTES} minutos...")
            logger.info(f"   Esperando hasta {datetime.now().strftime('%H:%M:%S')}\n")
            
            await asyncio.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler detenido por usuario")
            break
        except Exception as e:
            logger.error(f"Error en scheduler continuo: {e}", exc_info=True)
            # Esperar un poco antes de reintentar
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_continuous())