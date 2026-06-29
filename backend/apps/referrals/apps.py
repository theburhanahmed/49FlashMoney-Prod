from django.apps import AppConfig


class ReferralsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.referrals'
    verbose_name = 'Referral Bonus System'

    def ready(self):
        """Initialize app-ready signals."""
        import apps.referrals.signals  # noqa
