"""
Google Drive Service - Integración con Google Drive API
"""
import json
import os
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import settings
from app.utils.logger import get_logger
from app.utils.errors import GoogleDriveError

logger = get_logger(__name__)

# Scopes de solo lectura
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveService:
    """
    Servicio para interactuar con Google Drive
    """
    
    def __init__(self):
        """Inicializar servicio de Google Drive"""
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Autenticar con Google Drive usando Service Account (producción) u OAuth (desarrollo)
        """
        service_account_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
        logger.info(f"🔍 DEBUG: GOOGLE_SERVICE_ACCOUNT_JSON exists: {service_account_json is not None}")
        try:
            # OPCIÓN 1: Service Account (Producción - Railway)
            service_account_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON
            if service_account_json:
                logger.info("🔐 Using Service Account credentials (Production)")
                import json
                from google.oauth2 import service_account
                
                # Parse JSON from environment variable
                sa_info = json.loads(service_account_json)
                
                self.creds = service_account.Credentials.from_service_account_info(
                    sa_info,
                    scopes=SCOPES
                )
                
                # Crear servicio
                self.service = build('drive', 'v3', credentials=self.creds)
                logger.info("✅ Google Drive Service inicializado (Service Account)")
                return
            
            # OPCIÓN 2: OAuth Flow (Desarrollo Local)
            logger.info("🔐 Using OAuth flow (Development)")
            token_path = settings.GOOGLE_DRIVE_TOKEN_PATH
            creds_path = settings.GOOGLE_DRIVE_CREDENTIALS_PATH
            
            # Verificar si ya existe token
            if os.path.exists(token_path):
                logger.info("Token existente encontrado")
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # Si no hay credenciales válidas, obtenerlas
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refrescando token expirado")
                    self.creds.refresh(Request())
                else:
                    logger.info("Iniciando flujo OAuth...")
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    logger.info("✅ Autenticación exitosa")
                
                # Guardar credenciales para siguiente uso
                with open(token_path, 'w') as token:
                    token.write(self.creds.to_json())
                logger.info(f"Token guardado en: {token_path}")
            
            # Crear servicio
            self.service = build('drive', 'v3', credentials=self.creds)
            logger.info("✅ Google Drive Service inicializado (OAuth)")
            
        except Exception as e:
            logger.error(f"❌ Error authenticating with Google Drive: {e}")
            raise GoogleDriveError(f"Authentication failed: {str(e)}")
    
    def list_files_in_folder(
        self,
        folder_id: str,
        file_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Listar archivos en una carpeta de Google Drive
        
        Args:
            folder_id: ID de la carpeta
            file_types: Lista de extensiones (ej: ['pdf', 'jpg'])
            
        Returns:
            Lista de archivos con metadata
        """
        try:
            logger.info(f"Listando archivos en carpeta: {folder_id}")
            
            # Query base
            query = f"'{folder_id}' in parents and trashed=false"
            
            # Filtrar por tipo si se especifica
            if file_types:
                mime_queries = []
                for ext in file_types:
                    if ext.lower() == 'pdf':
                        mime_queries.append("mimeType='application/pdf'")
                    elif ext.lower() in ['jpg', 'jpeg']:
                        mime_queries.append("mimeType='image/jpeg'")
                    elif ext.lower() == 'png':
                        mime_queries.append("mimeType='image/png'")
                
                if mime_queries:
                    query += f" and ({' or '.join(mime_queries)})"
            
            # Ejecutar query
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime)",
                orderBy="createdTime desc"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"✅ Encontrados {len(files)} archivos")
            
            return files
            
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            raise GoogleDriveError(f"Error listando archivos: {str(e)}")
    
    def download_file(
        self,
        file_id: str,
        destination_path: str
    ) -> str:
        """
        Descargar archivo de Google Drive
        
        Args:
            file_id: ID del archivo en Drive
            destination_path: Ruta local donde guardar
            
        Returns:
            Ruta del archivo descargado
        """
        try:
            logger.info(f"Descargando archivo: {file_id}")
            
            # Crear directorio si no existe
            Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Obtener archivo
            request = self.service.files().get_media(fileId=file_id)
            
            # Descargar
            fh = io.FileIO(destination_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Descarga {progress}%")
            
            fh.close()
            logger.info(f"✅ Archivo descargado: {destination_path}")
            
            return destination_path
            
        except Exception as e:
            logger.error(f"Error descargando archivo: {e}")
            raise GoogleDriveError(f"Error descargando archivo: {str(e)}")
    
    def get_new_files(
        self,
        folder_ids: List[str],
        processed_file_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener archivos nuevos (no procesados) de carpetas
        
        Args:
            folder_ids: Lista de IDs de carpetas a monitorear
            processed_file_ids: IDs de archivos ya procesados
            
        Returns:
            Lista de archivos nuevos
        """
        processed_file_ids = processed_file_ids or []
        new_files = []
        
        for folder_id in folder_ids:
            files = self.list_files_in_folder(
                folder_id=folder_id,
                file_types=['pdf', 'jpg', 'jpeg', 'png']
            )
            
            for file in files:
                if file['id'] not in processed_file_ids:
                    new_files.append({
                        **file,
                        'folder_id': folder_id
                    })
        
        logger.info(f"✅ {len(new_files)} archivos nuevos encontrados")
        return new_files


# Singleton
_gdrive_service: Optional[GoogleDriveService] = None

def get_gdrive_service() -> GoogleDriveService:
    """Obtener instancia singleton"""
    global _gdrive_service
    if _gdrive_service is None:
        _gdrive_service = GoogleDriveService()
    return _gdrive_service