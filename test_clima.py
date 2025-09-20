# Este archivo es solo para probar nuestro nuevo servicio de clima.
import sys
sys.path.append('app')

from services.clima_service import clima_service

if __name__ == "__main__":
    print("--- Probando el Servicio del Clima MEJORADO con Open-Meteo ---")
    
    # Usaremos las coordenadas de Azua para la prueba
    lat_azua = 18.4533
    lon_azua = -70.7345
    
    print(f"\nObteniendo clima para Azua (Lat: {lat_azua}, Lon: {lon_azua})...")
    
    datos_clima = clima_service.obtener_clima_actual(lat=lat_azua, lon=lon_azua)
    
    if datos_clima:
        print("\n✅ ¡Éxito! Datos recibidos:")
        print(f"   🌡️ Temperatura Actual: {datos_clima['temperatura_actual']}°C")
        print(f"   💨 Velocidad del Viento: {datos_clima['velocidad_viento']} km/h")
        print(f"   🌦️ Código del Clima: {datos_clima['codigo_clima']}")
        print(f"   ⏰ Hora de la Medición: {datos_clima['hora_medicion']}")
        # --- ¡NUEVO! Verificamos los nuevos datos ---
        print(f"   💧 Lluvia en las últimas 24h: {datos_clima['lluvia_24h']} mm")
        print(f"   🔼 Temperatura Máxima (hoy): {datos_clima['temperatura_max_24h']}°C")
        print(f"   🔽 Temperatura Mínima (hoy): {datos_clima['temperatura_min_24h']}°C")
    else:
        print("\n❌ Fallo al obtener los datos del clima.")

    print("\n--- Prueba finalizada ---")