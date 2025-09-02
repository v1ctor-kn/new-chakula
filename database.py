# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def _build_mysql_url():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    name = os.getenv("DB_NAME", "recipes_db")
    # Using pymysql dialect; user must install it if connecting to MySQL (not required for SQLite)
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

if not DATABASE_URL:
    # default to sqlite for easiest local dev
    # If DB_HOST/DB_USER provided and you prefer MySQL, set DATABASE_URL or adjust here
    sqlite_path = os.path.join(os.path.dirname(__file__), "data.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"

# engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# helper generator for dependency style
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
