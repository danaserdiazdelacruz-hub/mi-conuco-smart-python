import requests

class ClimaService:
    def __init__(self):
        self.BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def obtener_clima_actual(self, lat: float, lon: float) -> dict | None:
        """
        Obtiene un resumen climático completo para las próximas 24 horas.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,precipitation_sum,relative_humidity_2m_mean,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 1 # Solo necesitamos el pronóstico para HOY
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            resumen_diario = data.get("daily")
            if not resumen_diario:
                return None

            # Extraemos los datos del primer (y único) día del pronóstico
            return {
                "temperatura_max_24h": resumen_diario.get("temperature_2m_max", [0])[0],
                "lluvia_24h": resumen_diario.get("precipitation_sum", [0])[0],
                "humedad_media": resumen_diario.get("relative_humidity_2m_mean", [0])[0],
                "prob_lluvia": resumen_diario.get("precipitation_probability_max", [0])[0]
            }

        except requests.exceptions.RequestException as e:
            print(f"Error al contactar la API de Open-Meteo: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error procesando la respuesta de la API del clima: {e}")
            return None

clima_service = ClimaService()