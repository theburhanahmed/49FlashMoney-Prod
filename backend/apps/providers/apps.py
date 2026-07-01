from django.apps import AppConfig


class ProvidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.providers'
    verbose_name = 'Casino Providers'

    def ready(self) -> None:
        # Importing the adapters package triggers registration of all
        # bundled adapters (DemoProviderAdapter, etc.) with the global registry.
        import apps.providers.adapters  # noqa: F401
