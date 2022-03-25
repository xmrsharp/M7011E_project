from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'polls'
    #label = 'user.conf'

    # add this
    def ready(self):
        import polls.signals  # noqa

"""class PollsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'polls'
    #label = 'polls.conf'
"""

