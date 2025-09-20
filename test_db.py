import sys
sys.path.append('app')

from config.database import test_connection, verify_tables

if __name__ == "__main__":
    print("🔍 PROBANDO CONEXIÓN A POSTGRESQL...")
    print("=" * 50)
    
    if test_connection():
        print("\n🔍 VERIFICANDO TABLAS...")
        if verify_tables():
            print("\n🎉 BASE DE DATOS LISTA!")
        else:
            print("\n⚠️  Algunas tablas faltan")
    else:
        print("\n❌ CONEXIÓN FALLIDA")