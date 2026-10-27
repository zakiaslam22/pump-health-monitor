from sqlalchemy import text
from db import get_engine

engine=get_engine()

with engine.connect() as conn:
    print(conn.execute(text("SELECT version();")).scalar())
