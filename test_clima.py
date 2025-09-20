# Importamos 'sys' para poder añadir nuestra carpeta 'app' a las rutas de Python
import sys
sys.path.append('app')

# Ahora sí podemos importar nuestro servicio
from services.clima_service import clima_service

# --- INICIO DEL SCRIPT DE PRUEBA ---

print("--- 🔬 Probando el Servicio del Clima ---")

# Coordenadas para la prueba (ej. Santo Domingo)
LATITUD_PRUEBA = 18.4861
LONGITUD_PRUEBA = -69.9312

print(f"Solicitando clima para Lat: {LATITUD_PRUEBA}, Lon: {LONGITUD_PRUEBA}...")

# Llamamos a la función que queremos probar
datos_clima = clima_service.obtener_clima_actual(lat=LATITUD_PRUEBA, lon=LONGITUD_PRUEBA)

# Verificamos y mostramos el resultado
if datos_clima:
    print("\n✅ ¡Éxito! Se recibieron los datos del clima:")
    print(f"   🌡️ Temperatura Actual:   {datos_clima.get('temperatura_actual')}°C")
    print(f"   💨 Velocidad del Viento: {datos_clima.get('velocidad_viento')} km/h")
    print(f"   📈 Temp. Máx. (24h):     {datos_clima.get('temperatura_max_24h')}°C")
    print(f"   💧 Lluvia (24h):         {datos_clima.get('lluvia_24h')} mm")
else:
    print("\n❌ ¡Fallo! No se pudieron obtener los datos del clima.")
    print("   Revisa la consola en busca de mensajes de error de la API.")

print("\n--- Fin de la prueba ---")