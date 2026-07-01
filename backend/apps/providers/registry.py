"""
Provider adapter registry for 49FlashMoney.

Adapters register themselves here so ProviderService can look them up
by slug without hard-coded imports scattered across the codebase.

Usage::

    from apps.providers.registry import registry

    # Register (done at app ready-time in adapters/__init__.py)
    registry.register(DemoProviderAdapter())

    # Lookup
    adapter = registry.get('demo')
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProviderAdapter

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Thread-safe (read-heavy) registry mapping provider slugs to adapter instances.

    Adapters are singletons — one instance per provider per process.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseProviderAdapter] = {}

    # ---------------------------------------------------------------------- #

    def register(self, adapter: 'BaseProviderAdapter') -> None:
        """
        Register an adapter instance.

        Raises:
            ValueError if another adapter with the same slug is already
            registered (prevents accidental double-registration at startup).
        """
        slug = adapter.provider_slug
        if slug in self._adapters:
            raise ValueError(
                f"Provider '{slug}' is already registered. "
                "Each provider may only be registered once."
            )
        self._adapters[slug] = adapter
        logger.info("Registered provider adapter: %s (%s)", slug, adapter.display_name)

    def unregister(self, slug: str) -> None:
        """Remove a provider (useful in tests)."""
        self._adapters.pop(slug, None)

    # ---------------------------------------------------------------------- #

    def get(self, slug: str) -> 'BaseProviderAdapter':
        """
        Retrieve an adapter by slug.

        Raises:
            KeyError if the slug is not registered.
        """
        if slug not in self._adapters:
            raise KeyError(
                f"No provider adapter registered for slug '{slug}'. "
                f"Available: {list(self._adapters)}"
            )
        return self._adapters[slug]

    def all(self) -> list['BaseProviderAdapter']:
        """Return all registered adapters in registration order."""
        return list(self._adapters.values())

    def slugs(self) -> list[str]:
        """Return all registered slugs."""
        return list(self._adapters)

    def is_registered(self, slug: str) -> bool:
        return slug in self._adapters

    def __len__(self) -> int:
        return len(self._adapters)

    def __repr__(self) -> str:
        return f"<ProviderRegistry slugs={self.slugs()}>"


# Module-level singleton — import and use directly.
registry = ProviderRegistry()
