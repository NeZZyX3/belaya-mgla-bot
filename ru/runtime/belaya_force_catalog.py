"""belaya-mgla-bot: always run the «Белая мгла» (wos_ru) module catalog.

Upstream binds the RU catalog (Russian OCR + games/wos/ru overlays) only after
the controller notices the running package is ``com.gof.globalru``. When that
detection is missed (game already open, emulator restarted) the worker stays on
the global ``wos`` catalog: Tesseract reads Russian screens with the English
model and no RU screen is recognised. This fork serves only the RU build, so the
catalog for game ``wos`` is pinned to ``BELAYA_FORCE_CATALOG`` (default
``wos_ru``; set it to an empty string to restore upstream behaviour).

Applied lazily right after the ``services`` module is imported (meta-path hook
installed by ``belaya_force_catalog.pth``).
"""

from __future__ import annotations

import importlib.abc
import os
import sys

_TARGET = "services"
_FORCED = os.environ.get("BELAYA_FORCE_CATALOG", "wos_ru").strip()


def _patch(mod) -> None:
    if not _FORCED or getattr(mod, "_belaya_catalog_patch", False):
        return
    orig_bind_catalog = getattr(mod, "bind_active_module_catalog", None)
    orig_bind_game = getattr(mod, "bind_active_game", None)
    if orig_bind_catalog is None:
        return

    def bind_active_module_catalog(catalog: str) -> None:
        c = (catalog or "").strip()
        orig_bind_catalog(_FORCED if c in ("", "wos") else c)

    mod.bind_active_module_catalog = bind_active_module_catalog
    if orig_bind_game is not None:

        def bind_active_game(game: str) -> None:
            orig_bind_game(game)
            if (game or "").strip() in ("", "wos"):
                orig_bind_catalog(_FORCED)

        mod.bind_active_game = bind_active_game
    # Unbound processes (API, scheduler) fall back to the forced catalog too.
    try:
        orig_bind_catalog(_FORCED)
    except Exception:
        pass
    mod._belaya_catalog_patch = True


class _Loader(importlib.abc.Loader):
    def __init__(self, inner):
        self._inner = inner

    def create_module(self, spec):
        return self._inner.create_module(spec)

    def exec_module(self, module):
        self._inner.exec_module(module)
        _patch(module)


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname != _TARGET:
            return None
        for finder in sys.meta_path:
            if finder is self:
                continue
            spec = finder.find_spec(fullname, path, target) if hasattr(finder, "find_spec") else None
            if spec is not None and spec.loader is not None:
                spec.loader = _Loader(spec.loader)
                return spec
        return None


if _FORCED and not any(isinstance(f, _Finder) for f in sys.meta_path):
    sys.meta_path.insert(0, _Finder())
