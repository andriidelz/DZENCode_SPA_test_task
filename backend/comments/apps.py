from django.apps import AppConfig


class CommentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comments'
    verbose_name = 'Comments'
    
    def ready(self):
        """
        Import signals when the app is ready
        """
        try:
            import comments.signals
        except ImportError:
            pass
