from typing import Any

# Module-level stubs for `gi` so calls like `gi.require_version(...)` are recognized.
def require_version(name: str, version: str) -> None: ...
def require_foreign(name: str) -> None: ...

# Expose `repository` as a package submodule (types are in repository.pyi)
repository: Any
