import requests
from datetime import datetime

class ClimaService:
    def __init__(self):
        self.BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def obtener_clima_historico(self, lat: float, lon: float, dias_atras: int = 2) -> dict | None:
        """
        Obtiene el clima actual Y un historial de los últimos días (hasta 2 días / 48h).
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
            "past_days": dias_atras # ¡CLAVE! Pedimos historial de X días
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            clima_actual = data.get("current_weather")
            historial_diario = data.get("daily")

            if not clima_actual or not historial_diario:
                return None

            return {
                "actual": {
                    "temperatura": clima_actual.get("temperature"),
                    "velocidad_viento": clima_actual.get("windspeed"),
                },
                "historial": {
                    "fechas": historial_diario.get("time", []),
                    "temp_max": historial_diario.get("temperature_2m_max", []),
                    "temp_min": historial_diario.get("temperature_2m_min", []),
                    "lluvia_sum": historial_diario.get("precipitation_sum", [])
                }
            }
        except Exception as e:
            print(f"Error al obtener datos históricos del clima: {e}")
            return None

clima_service = ClimaService()