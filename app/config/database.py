import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL no encontrada en variables de entorno")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()[0]
        db.close()
        
        if test_value == 1:
            print("Conexión a PostgreSQL exitosa")
            return True
        else:
            print("Error en test de PostgreSQL")
            return False
            
    except Exception as e:
        print(f"Error conectando a PostgreSQL: {e}")
        return False

def verify_tables():
    try:
        db = SessionLocal()
        expected_tables = ['cultivos', 'usuarios', 'siembras']
        
        for table in expected_tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                print(f"Tabla '{table}': {count} registros")
            except Exception as e:
                print(f"Error en tabla '{table}': {e}")
                db.close()
                return False
        
        db.close()
        return True
        
    except Exception as e:
        print(f"Error verificando tablas: {e}")
        return False