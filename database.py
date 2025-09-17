import os
import psycopg2
from psycopg2 import pool
import logging

db_pool = None

def inicializar_pool():
    global db_pool
    if not db_pool:
        try:
            db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=os.getenv('DATABASE_URL'))
            logging.info("✅ Pool de conexiones a la base de datos inicializado.")
        except Exception as e:
            logging.error(f"❌ ERROR CRÍTICO: No se pudo conectar a la base de datos. {e}")
            db_pool = None

def ejecutar_sql(query, params=None, fetch=None):
    if not db_pool:
        raise Exception("El pool de la base de datos no está inicializado.")
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch == 'uno': return cur.fetchone()
            if fetch == 'todos': return cur.fetchall()
            conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        raise e # Relanzamos la excepción para que el llamador la maneje
    finally:
        if conn: db_pool.putconn(conn)

def inicializar_db():
    ejecutar_sql("""
        CREATE TABLE IF NOT EXISTS usuarios (
            telefono VARCHAR(50) PRIMARY KEY,
            nombre VARCHAR(150) DEFAULT 'Agricultor',
            cultivo VARCHAR(100),
            fecha_siembra TIMESTAMPTZ,
            lat DECIMAL(10, 8),
            lon DECIMAL(11, 8),
            zona_agroecologica VARCHAR(100),
            estado VARCHAR(50) DEFAULT 'incompleto'
        );
    """)
    logging.info("Tabla 'usuarios' verificada/inicializada.")

def obtener_usuario(telefono):
    return ejecutar_sql("SELECT * FROM usuarios WHERE telefono = %s", (telefono,), fetch='uno')

def guardar_usuario(usuario):
    query = """
        INSERT INTO usuarios (telefono, nombre, cultivo, fecha_siembra, lat, lon, zona_agroecologica, estado)
        VALUES (%(telefono)s, %(nombre)s, %(cultivo)s, %(fecha_siembra)s, %(lat)s, %(lon)s, %(zona_agroecologica)s, %(estado)s)
        ON CONFLICT (telefono) DO UPDATE SET
          nombre = EXCLUDED.nombre, cultivo = EXCLUDED.cultivo, fecha_siembra = EXCLUDED.fecha_siembra,
          lat = EXCLUDED.lat, lon = EXCLUDED.lon, zona_agroecologica = EXCLUDED.zona_agroecologica,
          estado = EXCLUDED.estado;
    """
    ejecutar_sql(query, usuario)
