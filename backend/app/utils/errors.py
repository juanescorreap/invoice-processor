"""
Clases de errores personalizadas
"""


class InvoiceProcessorError(Exception):
    """Base exception para el sistema"""
    pass


class FileError(InvoiceProcessorError):
    """Errores relacionados con archivos"""
    pass


class OCRError(InvoiceProcessorError):
    """Errores en proceso OCR"""
    pass


class NERError(InvoiceProcessorError):
    """Errores en proceso NER"""
    pass


class DatabaseError(InvoiceProcessorError):
    """Errores de base de datos"""
    pass


class ValidationError(InvoiceProcessorError):
    """Errores de validación"""
    pass


class GoogleDriveError(InvoiceProcessorError):
    """Errores de Google Drive API"""
    pass


class ConfigurationError(InvoiceProcessorError):
    """Errores de configuración"""
    pass


class QueueError(InvoiceProcessorError):
    """Errores en sistema de colas"""
    pass