from django.apps import AppConfig


class NewsStationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news_station"

    def ready(self):
        from . import signals  # noqa: F401
