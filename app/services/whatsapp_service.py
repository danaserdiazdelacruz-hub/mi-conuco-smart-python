import os
from twilio.rest import Client
from typing import Dict, Optional
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
from sqlalchemy import text
from .clima_service import clima_service

load_dotenv()

class WhatsAppService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN") 
        self.twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.client = Client(self.account_sid, self.auth_token)
        self.estados_usuario = {}  # Incluye estados de conversación y feedback
        self.cultivos_data = {
            "1": {"nombre": "Tomate", "codigo": "TOM", "ciclo_dias": 90},
            "2": {"nombre": "Ají Cubanela", "codigo": "AJI", "ciclo_dias": 120},
            "3": {"nombre": "Banano", "codigo": "BAN", "ciclo_dias": 365}
        }

    def enviar_mensaje(self, to_number: str, mensaje: str) -> bool:
        try:
            message = self.client.messages.create(
                body=mensaje, 
                from_=f'whatsapp:{self.twilio_number}', 
                to=f'whatsapp:{to_number}'
            )
            print(f"Mensaje enviado: {message.sid}")
            return True
        except Exception as e:
            print(f"Error enviando mensaje: {e}")
            return False

    def procesar_mensaje_entrante(self, from_number: str, mensaje: str, db) -> str:
        mensaje = mensaje.upper().strip()
        
        # Detectar si estamos esperando feedback
        estado = self.estados_usuario.get(from_number, {})
        if estado.get("esperando_feedback"):
            return self.procesar_feedback(from_number, mensaje, db)
        
        comandos = {
            "REGISTRO": lambda: self.iniciar_registro(from_number, db),
            "REPORTE": lambda: self.generar_reporte_inteligente(from_number, db),
            "AYUDA": lambda: self.mostrar_ayuda()
        }
        
        if mensaje in comandos:
            return comandos[mensaje]()
        elif from_number in self.estados_usuario:
            return self.continuar_conversacion(from_number, mensaje, db)
        else:
            return self.mensaje_bienvenida()

    def mensaje_bienvenida(self) -> str:
        return "¡A la orden! Soy Mi Conuco Smart. Manda REGISTRO para apuntar tu siembra o REPORTE para ver cómo va todo."

    def iniciar_registro(self, from_number: str, db) -> str:
        result = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE telefono = :phone"), {"phone": from_number})
        if result.fetchone()[0] > 0:
            return "Ya te conozco, compa. Envía REPORTE para ver lo de tu siembra."
        
        self.estados_usuario[from_number] = {"paso": "seleccionar_cultivo"}
        opciones = "\n".join([f"{k}-{v['nombre']}" for k, v in self.cultivos_data.items()])
        return f"¡Claro que sí! Vamos a apuntar esa siembra. ¿Qué sembraste?\n{opciones}\n(Manda solo el número)"

    def continuar_conversacion(self, from_number: str, mensaje: str, db) -> str:
        estado = self.estados_usuario[from_number]
        pasos = {
            "seleccionar_cultivo": lambda: self.procesar_cultivo(from_number, mensaje, estado),
            "fecha_siembra": lambda: self.procesar_fecha_siembra(from_number, mensaje, estado),
            "ubicacion": lambda: self.completar_registro(from_number, mensaje, estado, db)
        }
        
        return pasos.get(estado["paso"], lambda: "No te entendí. Manda AYUDA si quieres ver los comandos.")()

    def procesar_cultivo(self, from_number: str, mensaje: str, estado: Dict) -> str:
        if mensaje in self.cultivos_data:
            cultivo = self.cultivos_data[mensaje]
            estado.update({
                "cultivo_id": mensaje, 
                "cultivo_data": cultivo, 
                "paso": "fecha_siembra"
            })
            return f"✅ ¡{cultivo['nombre']}! ¿Y cuándo fue que lo sembraste?\n(Ej: \"hoy\", \"hace 10 días\", \"hace 2 semanas\")"
        return "Ese número no es válido. Manda uno del 1 al 3."

    def procesar_fecha_siembra(self, from_number: str, mensaje: str, estado: Dict) -> str:
        fecha_siembra = self.parsear_fecha(mensaje)
        if fecha_siembra:
            dias = (datetime.now().date() - fecha_siembra).days
            estado.update({
                "fecha_siembra": fecha_siembra, 
                "paso": "ubicacion", 
                "dias_transcurridos": dias
            })
            return f"✅ Anotado ({dias} días).\nAhora, dime, ¿en qué municipio o paraje estás?"
        return "No entendí la fecha. Prueba con: \"hace 10 días\" o \"15/8/2025\"."

    def parsear_fecha(self, mensaje: str) -> Optional[datetime]:
        mensaje = mensaje.lower().strip()
        try:
            if mensaje == "hoy": 
                return datetime.now().date()
            if "hace" in mensaje:
                num = int(re.findall(r'\d+', mensaje)[0])
                if "día" in mensaje or "dias" in mensaje: 
                    return datetime.now().date() - timedelta(days=num)
                if "semana" in mensaje or "semanas" in mensaje: 
                    return datetime.now().date() - timedelta(weeks=num)
            if "/" in mensaje:
                d, m, a = map(int, mensaje.split("/"))
                return datetime(a, m, d).date()
        except:
            pass
        return None

    def completar_registro(self, from_number: str, ubicacion: str, estado: Dict, db) -> str:
        try:
            zona_id = self.determinar_zona(ubicacion)
            
            # Insertar/actualizar usuario
            db.execute(text("""
                INSERT INTO usuarios (telefono, nombre, status, zona_id) 
                VALUES (:p, :n, 'activo', :z) 
                ON CONFLICT (telefono) DO UPDATE SET status = 'activo', zona_id = :z
            """), {
                "p": from_number, 
                "n": f"Agricultor {estado['cultivo_data']['nombre']}", 
                "z": zona_id
            })
            
            # Obtener IDs necesarios
            user_id = db.execute(text("SELECT id FROM usuarios WHERE telefono = :p"), {"p": from_number}).fetchone()[0]
            cultivo_id = db.execute(text("SELECT id FROM cultivos WHERE codigo = :c"), {"c": estado['cultivo_data']['codigo']}).fetchone()[0]
            
            # Insertar siembra
            db.execute(text("""
                INSERT INTO siembras (usuario_id, cultivo_id, fecha_siembra, dia_actual, activa) 
                VALUES (:uid, :cid, :f, :d, true)
            """), {
                "uid": user_id, 
                "cid": cultivo_id, 
                "f": estado["fecha_siembra"], 
                "d": estado["dias_transcurridos"]
            })
            
            db.commit()
            del self.estados_usuario[from_number]
            
            return f"¡Listo, compa! Ya tengo los datos de tu siembra de {estado['cultivo_data']['nombre']} en {self.obtener_nombre_zona(zona_id)}.\n\nManda REPORTE cuando quieras pa' darte el dato del tiempo."
            
        except Exception as e:
            db.rollback()
            print(f"Error en registro: {e}")
            return "Hubo un lío guardando los datos. Intenta de nuevo mandando REGISTRO."

    def determinar_zona(self, ubicacion: str) -> int:
        ubicacion = ubicacion.lower()
        zonas = {
            "santiago": 2,
            "constanza": 3, 
            "hato mayor": 4
        }
        for zona, id_zona in zonas.items():
            if zona in ubicacion:
                return id_zona
        return 1  # Azua por defecto

    def obtener_nombre_zona(self, zona_id: int) -> str:
        zonas = {1: "Azua", 2: "Santiago", 3: "Constanza", 4: "Hato Mayor"}
        return zonas.get(zona_id, "Zona desconocida")

    def generar_reporte_inteligente(self, from_number: str, db) -> str:
        try:
            siembra = db.execute(text("""
                SELECT c.nombre as cultivo, s.fecha_siembra, c.dias_ciclo_promedio, 
                       z.id as zona_id, z.latitud, z.longitud,
                       c.precio_mercado_libra, c.tendencia_precio
                FROM siembras s 
                JOIN usuarios u ON u.id = s.usuario_id 
                JOIN cultivos c ON c.id = s.cultivo_id 
                JOIN zonas_agroecologicas z ON z.id = u.zona_id
                WHERE u.telefono = :p AND s.activa = true 
                ORDER BY s.created_at DESC LIMIT 1
            """), {"p": from_number}).fetchone()
            
            if not siembra: 
                return "No encontré tu siembra. Manda REGISTRO para empezar."

            # Calcular progreso
            dias = (datetime.now().date() - siembra.fecha_siembra).days
            progreso = round((dias / siembra.dias_ciclo_promedio) * 100, 1) if siembra.dias_ciclo_promedio > 0 else 0
            
            # Construir reporte base
            reporte = self._construir_encabezado_reporte(siembra, dias, progreso)
            
            # Agregar información climática
            clima_info = self._procesar_clima(siembra)
            reporte += clima_info
            
            # Agregar recomendación inteligente
            datos_clima = clima_service.obtener_clima_actual(lat=siembra.latitud, lon=siembra.longitud)
            if datos_clima:
                recomendacion = self._generar_recomendacion_estrategica(datos_clima, siembra.cultivo, dias)
                reporte += f"💡 REVISA:\n{recomendacion}"
            
            # Agregar precio
            if siembra.precio_mercado_libra:
                reporte += f"\n\n💰 Precio Mercado (MERCADOM):\n   RD${siembra.precio_mercado_libra:.2f}/libra ({siembra.tendencia_precio})"

            # Enviar mensaje y solicitar feedback ocasionalmente
            self.enviar_mensaje(from_number, reporte + "\n\nMi Conuco Smart 🌱")
            
            # Solicitar feedback 1 de cada 3 reportes
            if dias % 3 == 0:
                self._solicitar_feedback(from_number, datos_clima, siembra, db)
            
            return ""

        except Exception as e:
            print(f"Error generando reporte: {e}")
            return "Hubo un lío generando el reporte. Intenta otra vez en un rato."

    def _construir_encabezado_reporte(self, siembra, dias, progreso) -> str:
        return f"""📊 REPORTE - {siembra.cultivo.upper()}
📅 {dias} días ({progreso}% de crecimiento)
📍 {self.obtener_nombre_zona(siembra.zona_id)}

"""

    def _procesar_clima(self, siembra) -> str:
        datos_clima = clima_service.obtener_clima_actual(lat=siembra.latitud, lon=siembra.longitud)
        
        if not datos_clima:
            return "No pude conseguir el dato del tiempo pa' tu zona ahora mismo.\n\n"
        
        temp_max = datos_clima.get('temperatura_max_24h')
        humedad = datos_clima.get('humedad_media')
        
        # Debug para ver qué está devolviendo la API
        print(f"DEBUG - Temperatura: {temp_max}, Humedad: {humedad}")
        
        if temp_max is None:
            return "Datos de clima no disponibles.\n\n"
        
        clima_str = f"🌡️ HOY: {temp_max}°C"
        
        # Verificar humedad y agregar contexto
        if humedad is not None:
            if humedad > 85:
                clima_str += ", con mucha humedad (bochorno)"
            elif humedad < 60:
                clima_str += ", ambiente seco"
            else:
                clima_str += ", humedad normal"
        else:
            print("DEBUG - Humedad es None")
        
        return clima_str + "\n\n"

    def _obtener_etapa_cultivo(self, cultivo: str, dias: int) -> str:
        etapas = {
            "Tomate": [(30, "Crecimiento"), (55, "Floración"), (80, "Fructificación"), (float('inf'), "Cosecha")],
            "Ají Cubanela": [(30, "Crecimiento"), (55, "Floración"), (80, "Fructificación"), (float('inf'), "Cosecha")],
            "Banano": [(90, "Establecimiento"), (180, "Desarrollo"), (300, "Floración"), (float('inf'), "Fructificación")]
        }
        
        for limite, etapa in etapas.get(cultivo, [(float('inf'), "Desarrollo")]):
            if dias < limite:
                return etapa
        return "Desarrollo"

    def _generar_recomendacion_estrategica(self, clima: dict, cultivo: str, dias_cultivo: int) -> str:
        temp_max = clima.get("temperatura_max_24h")
        humedad = clima.get("humedad_media") 
        prob_lluvia = clima.get("prob_lluvia")
        etapa = self._obtener_etapa_cultivo(cultivo, dias_cultivo)

        # Alertas climáticas prioritarias
        if temp_max and temp_max > 32:
            if humedad and humedad > 80:
                return "   🔥 ALERTA: Mucho calor y humedad. Revisa las hojas por si aparecen manchas (hongos). Si ves algo raro, actúa rápido."
            elif humedad and humedad < 60:
                return f"   🔥 CALOR SECO: {temp_max}°C es mucho para las plantas. Si las hojas se ven tristes, considera regar temprano y al final del día."

        if prob_lluvia and prob_lluvia > 50:
            return f"   🌦️ PROBABLE LLUVIA ({prob_lluvia}%): Mira el cielo antes de regar. Si llueve, te ahorras el trabajo y el agua."

        # Consejos por etapa (no prescriptivos)
        consejos_etapa = {
            "Crecimiento": "👀 Las plantas están creciendo. Si las hojas se ven pálidas o el crecimiento es lento, puede que necesiten abono.",
            "Floración": "🌸 Van saliendo flores. Si quieres que cuajen bien, un abono rico en fósforo ayuda (pero solo si no has abonado recientemente).",
            "Fructificación": "🍅 Los frutos están engordando. Vigila que no les falte agua y ojo con las plagas que les gusta lo dulce.",
            "Cosecha": "✂️ Tiempo de cosechar. Revisa a diario para coger los frutos en su punto.",
            "Establecimiento": "🌱 El banano se está estableciendo. Mantén el área limpia de maleza.",
            "Desarrollo": "📈 El banano está creciendo fuerte. Vigila por si aparecen manchas amarillas en las hojas (sigatoka)."
        }

        return consejos_etapa.get(etapa, "✅ Todo se ve normal. Sigue con tus labores de siempre.")

    def procesar_feedback(self, from_number: str, mensaje: str, db) -> str:
        """Procesa respuesta de feedback del usuario"""
        respuestas_validas = ["SÍ", "SI", "NO", "ÚTIL", "INÚTIL", "BUENO", "MALO"]
        
        if mensaje in respuestas_validas:
            self.guardar_feedback(from_number, mensaje, db)
            # Limpiar estado de feedback
            if from_number in self.estados_usuario:
                del self.estados_usuario[from_number]
            return "¡Gracias por tu opinión! Nos ayuda a mejorar."
        else:
            return "Responde SÍ o NO. ¿Te sirvió el consejo del último reporte?"

    def guardar_feedback(self, from_number: str, respuesta: str, db):
        """Guarda feedback en la base de datos"""
        try:
            estado = self.estados_usuario.get(from_number, {})
            siembra_id = estado.get("siembra_id")
            recomendacion = estado.get("recomendacion")

            if not siembra_id:
                print(f"No se pudo guardar feedback para {from_number}: siembra_id no encontrado.")
                return

            db.execute(text("""
                INSERT INTO feedback_recomendaciones (siembra_id, recomendacion_texto, respuesta_usuario, fecha_feedback)
                VALUES (:sid, :rt, :ru, NOW())
            """), {"sid": siembra_id, "rt": recomendacion, "ru": respuesta})
            db.commit()
            print(f"Feedback '{respuesta}' guardado para siembra {siembra_id}.")
        
        except Exception as e:
            db.rollback()
            print(f"Error al guardar feedback: {e}")

    def _solicitar_feedback(self, from_number: str, datos_clima: dict, siembra, db):
        """Solicita feedback sobre la recomendación enviada"""
        try:
            # Obtener siembra_id
            siembra_id = db.execute(text("""
                SELECT s.id FROM siembras s 
                JOIN usuarios u ON u.id = s.usuario_id 
                WHERE u.telefono = :p AND s.activa = true 
                ORDER BY s.created_at DESC LIMIT 1
            """), {"p": from_number}).fetchone()
            
            if siembra_id:
                # Guardar estado para feedback
                recomendacion = self._generar_recomendacion_estrategica(datos_clima, siembra.cultivo, 
                    (datetime.now().date() - siembra.fecha_siembra).days)
                
                self.estados_usuario[from_number] = {
                    "esperando_feedback": True,
                    "siembra_id": siembra_id[0],
                    "recomendacion": recomendacion
                }
                
                # Enviar solicitud de feedback
                mensaje_feedback = "¿Te sirvió el consejo? Responde SÍ o NO (esto nos ayuda a mejorar)"
                self.enviar_mensaje(from_number, mensaje_feedback)
                
        except Exception as e:
            print(f"Error solicitando feedback: {e}")

    def mostrar_ayuda(self) -> str:
        return """COMANDOS:
- REGISTRO: Para apuntar una siembra nueva
- REPORTE: Para ver cómo va todo y el dato del tiempo
- AYUDA: Para ver estos comandos"""

# Instancia única del servicio
whatsapp_service = WhatsAppService()