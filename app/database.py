from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, DeclarativeBase

import psycopg2
from dotenv import load_dotenv
import os



load_dotenv()

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 5432))
)

engine = create_engine(url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        print("Conexión abierta")
        yield db
    finally:
        db.close()
        print("Conexión cerrada")

def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Conexión exitosa:", result.fetchone())
    except Exception as e:
        print("Error al conectar:", e)

test_connection()