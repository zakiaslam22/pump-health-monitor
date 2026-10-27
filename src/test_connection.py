from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg://postgres@localhost:5432/pump_db")

with engine.connect() as conn:
    print(conn.execute(text("SELECT version();")).scalar())