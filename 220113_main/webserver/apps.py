from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webserver'
    #label = 'user.conf'

    # add this
    def ready(self):
        import webserver.signals  # noqa
