from sqlalchemy import create_engine

DB_URL = "postgresql+psycopg://postgres@localhost:5432/pump_db"


def get_engine():
    """Return a SQLAlchemy engine connected to pump_db."""
    engine=create_engine(DB_URL)
    print("SQLAlchemy engine for pump_db has been created.")
    return engine

