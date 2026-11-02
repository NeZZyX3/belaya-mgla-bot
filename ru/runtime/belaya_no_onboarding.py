"""belaya-mgla-bot: never treat the account as being in the first-run tutorial.

Upstream gates the popup dismissers and the identity probe off while
``worker.onboarding_phase.onboarding_active`` is True (no resolved player, no
recorded Sawmill, furnace < 5). Right after a start with a login modal up
(«С возвращением!», paid-pack offers) none of those signals is known yet, so the
modal is never dismissed, ``who_i_am`` never runs and the worker idles forever —
the bootstrap deadlock described in upstream's own docstring. «Белая мгла»
players run established accounts and this fork disables the onboarding module,
so the phase is pinned to "not onboarding" (``BELAYA_ONBOARDING=1`` restores
upstream behaviour).

Applied right after ``worker.onboarding_phase`` is imported (meta-path hook
installed by ``belaya_no_onboarding.pth``).
"""

from __future__ import annotations

import importlib.abc
import os
import sys

_TARGET = "worker.onboarding_phase"
_ENABLED = os.environ.get("BELAYA_ONBOARDING", "").strip() not in ("1", "true", "yes")


async def _never_onboarding(redis, instance_id):  # noqa: ARG001 - same signature
    return False


class _Loader(importlib.abc.Loader):
    def __init__(self, inner):
        self._inner = inner

    def create_module(self, spec):
        return self._inner.create_module(spec)

    def exec_module(self, module):
        self._inner.exec_module(module)
        if hasattr(module, "onboarding_active"):
            module.onboarding_active = _never_onboarding


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname != _TARGET:
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None and spec.loader is not None:
                spec.loader = _Loader(spec.loader)
                return spec
        return None


if _ENABLED and not any(isinstance(f, _Finder) for f in sys.meta_path):
    sys.meta_path.insert(0, _Finder())
