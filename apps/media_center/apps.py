from django.apps import AppConfig


class MediaCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media_center"
    label = "media_center"
    verbose_name = "Press releases, media kit, news"
