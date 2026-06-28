"""A tiny, generic plugin registry.

Every extensible catalogue in stickforge (asset types, renderers, exporters,
easing curves, ...) is a ``Registry``. Plugins call ``register`` — or use it as
a decorator — to add capabilities without touching core code, which is the
mechanism that keeps the platform open/extensible.
"""
from __future__ import annotations

from typing import Callable, Generic, Iterator, TypeVar

T = TypeVar("T")


class RegistryError(KeyError):
    """Raised for unknown keys or duplicate registrations."""


class Registry(Generic[T]):
    """A name -> object map with decorator support and friendly errors."""

    def __init__(self, kind: str = "item") -> None:
        self.kind = kind
        self._items: dict[str, T] = {}

    def register(self, name: str, obj: T | None = None,
                 *, overwrite: bool = False) -> T | Callable[[T], T]:
        """Register ``obj`` under ``name``.

        Usable directly (``reg.register("x", obj)``) or as a decorator
        (``@reg.register("x")``).
        """
        def _do(value: T) -> T:
            if not overwrite and name in self._items:
                raise RegistryError(
                    f"{self.kind} {name!r} already registered; "
                    f"pass overwrite=True to replace it")
            self._items[name] = value
            return value

        if obj is None:
            return _do                       # decorator form
        return _do(obj)                      # direct form

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError:
            raise RegistryError(
                f"unknown {self.kind} {name!r}; "
                f"known: {sorted(self._items)}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._items

    def __getitem__(self, name: str) -> T:
        return self.get(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def names(self) -> list[str]:
        return sorted(self._items)

    def items(self):
        return self._items.items()

    def __len__(self) -> int:
        return len(self._items)
