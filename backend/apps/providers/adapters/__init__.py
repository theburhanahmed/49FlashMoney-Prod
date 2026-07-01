"""
Provider adapter package.

Importing this module registers all bundled adapters with the global registry.
This import happens in ProvidersConfig.ready() so all adapters are available
as soon as Django starts.
"""
from apps.providers.registry import registry
from .demo import DemoProviderAdapter

# Register the demo adapter
_demo = DemoProviderAdapter()
if not registry.is_registered(_demo.provider_slug):
    registry.register(_demo)

__all__ = ['DemoProviderAdapter']
