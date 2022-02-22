from .config import Database


def config_to_url(db: Database) -> str:
    return f"{db.driver}://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}"
