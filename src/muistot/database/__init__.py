from .store import Databases, register_databases, DatabaseDependency

try:
    # This will not fail if databases is in use
    from .store import Database
except ImportError:
    # Fallback
    from .connection import Database

__all__ = [
    "register_databases",
    "Database",
    "Databases",
    "DatabaseDependency"
]
