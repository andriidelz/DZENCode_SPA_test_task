from django.apps import AppConfig
from backend.files.signals import *
# import backend.files.signals

class FilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'files'
    verbose_name = 'Files'
    
    def ready(self):
        """
        Import signals when the app is ready
        """
        try:
            import files.signals
        except ImportError:
            pass
