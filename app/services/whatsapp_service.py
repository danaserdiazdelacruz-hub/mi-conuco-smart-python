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
        self.estados_usuario = {}
        self.cultivos_data = {
            "1": {"nombre": "Tomate", "codigo": "TOM", "ciclo_dias": 90},
            "2": {"nombre": "Ají Cubanela", "codigo": "AJI", "ciclo_dias": 120},
            "3": {"nombre": "Banano", "codigo": "BAN", "ciclo_dias": 365},
            "4": {"nombre": "Habichuela", "codigo": "HAB", "ciclo_dias": 65},
            "5": {"nombre": "Yuca", "codigo": "YUC", "ciclo_dias": 300}
        }

    def enviar_mensaje(self, to_number: str, mensaje: str) -> bool:
        try:
            message = self.client.messages.create(body=mensaje, from_=f'whatsapp:{self.twilio_number}', to=f'whatsapp:{to_number}')
            print(f"Mensaje enviado: {message.sid}")
            return True
        except Exception as e:
            print(f"Error enviando mensaje: {e}")
            return False

    def procesar_mensaje_entrante(self, from_number: str, mensaje: str, db) -> str:
        mensaje = mensaje.upper().strip()
        estado_actual = self.estados_usuario.get(from_number, {})

        if estado_actual.get("esperando_feedback"):
            if "👍" in mensaje or "SI" in mensaje:
                self.guardar_feedback(from_number, "util", db)
                del self.estados_usuario[from_number]
                return "¡Gracias por tu respuesta! Tu feedback nos ayuda a mejorar. 👍"
            elif "👎" in mensaje or "NO" in mensaje:
                self.guardar_feedback(from_number, "no_util", db)
                del self.estados_usuario[from_number]
                return "Entendido. Gracias, aprenderemos de esto para darte mejores sugerencias en el futuro. 👎"

        if mensaje == "REGISTRO": return self.iniciar_registro(from_number, db)
        elif mensaje == "REPORTE": return self.generar_reporte_inteligente(from_number, db)
        elif mensaje == "AYUDA": return self.mostrar_ayuda()
        elif from_number in self.estados_usuario: return self.continuar_conversacion(from_number, mensaje, db)
        else: return self.mensaje_bienvenida()

    def mensaje_bienvenida(self) -> str:
        return "Hola! Soy Mi Conuco Smart...\nEnvía REGISTRO para comenzar\nEnvía REPORTE para ver tu cultivo\nEnvía AYUDA para más opciones"

    def iniciar_registro(self, from_number: str, db) -> str:
        result = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE telefono = :phone"), {"phone": from_number})
        if result.fetchone()[0] > 0:
            return "Ya estás registrado! Envía REPORTE para ver el estado de tu cultivo."
        self.estados_usuario[from_number] = {"paso": "seleccionar_cultivo"}
        return "Perfecto! ¿Qué estás cultivando?\n1 - Tomate\n2 - Ají Cubanela\n3 - Banano\n4 - Habichuela\n5 - Yuca\nEnvía solo el número (1-5)"

    def continuar_conversacion(self, from_number: str, mensaje: str, db) -> str:
        estado = self.estados_usuario[from_number]
        if estado["paso"] == "seleccionar_cultivo": return self.procesar_cultivo(from_number, mensaje, estado)
        elif estado["paso"] == "fecha_siembra": return self.procesar_fecha_siembra(from_number, mensaje, estado)
        elif estado["paso"] == "ubicacion": return self.completar_registro(from_number, mensaje, estado, db)
        return "No entendí tu respuesta. Envía AYUDA si necesitas ver los comandos."

    def procesar_cultivo(self, from_number: str, mensaje: str, estado: Dict) -> str:
        if mensaje in self.cultivos_data:
            cultivo = self.cultivos_data[mensaje]
            estado.update({"cultivo_id": mensaje, "cultivo_data": cultivo, "paso": "fecha_siembra"})
            return f"✅ ¡{cultivo['nombre']}!\n\n¿Cuándo lo sembraste?\n- \"hoy\"\n- \"hace X días\"\n- \"hace X semanas\"\n- Fecha exacta (ej: 15/8/2025)"
        return "Opción no válida. Envía un número del 1 al 5."

    def procesar_fecha_siembra(self, from_number: str, mensaje: str, estado: Dict) -> str:
        fecha_siembra = self.parsear_fecha(mensaje)
        if fecha_siembra:
            dias = (datetime.now().date() - fecha_siembra).days
            estado.update({"fecha_siembra": fecha_siembra, "paso": "ubicacion", "dias_transcurridos": dias})
            return f"✅ Fecha registrada! ({dias} días desde siembra)\n\nPor último, ¿dónde estás ubicado?\nEj: \"Santiago\", \"Azua\", \"Constanza\""
        return "No entendí la fecha. Prueba:\n- \"hoy\"\n- \"hace 10 días\"\n- \"15/8/2025\""

    def parsear_fecha(self, mensaje: str) -> Optional[datetime]:
        mensaje = mensaje.lower().strip()
        try:
            if mensaje == "hoy": return datetime.now().date()
            if "hace" in mensaje:
                num = int(re.findall(r'\d+', mensaje)[0])
                if "día" in mensaje: return datetime.now().date() - timedelta(days=num)
                if "semana" in mensaje: return datetime.now().date() - timedelta(weeks=num)
            if "/" in mensaje:
                d, m, a = map(int, mensaje.split("/"))
                return datetime(a, m, d).date()
        except: pass
        return None

    def completar_registro(self, from_number: str, ubicacion: str, estado: Dict, db) -> str:
        try:
            zona_id = self.determinar_zona(ubicacion)
            db.execute(text("""
                INSERT INTO usuarios (telefono, nombre, status, zona_id) VALUES (:p, :n, 'activo', :z)
                ON CONFLICT (telefono) DO UPDATE SET status = 'activo', zona_id = :z
            """), {"p": from_number, "n": f"Agricultor {estado['cultivo_data']['nombre']}", "z": zona_id})
            
            user_id = db.execute(text("SELECT id FROM usuarios WHERE telefono = :p"), {"p": from_number}).fetchone()[0]
            cultivo_id = db.execute(text("SELECT id FROM cultivos WHERE codigo = :c"), {"c": estado['cultivo_data']['codigo']}).fetchone()[0]
            
            db.execute(text("""
                INSERT INTO siembras (usuario_id, cultivo_id, fecha_siembra, dia_actual, activa)
                VALUES (:uid, :cid, :f, :d, true)
            """), {"uid": user_id, "cid": cultivo_id, "f": estado["fecha_siembra"], "d": estado["dias_transcurridos"]})
            
            db.commit()
            del self.estados_usuario[from_number]
            
            progreso = round((estado["dias_transcurridos"] / estado['cultivo_data']['ciclo_dias']) * 100, 1)
            return f"🎉 ¡REGISTRO COMPLETO!\n\nCultivo: {estado['cultivo_data']['nombre']}\nFecha: {estado['fecha_siembra']}\nZona: {self.obtener_nombre_zona(zona_id)}\nProgreso: {progreso}%\n\nAhora envía REPORTE."
        except Exception as e:
            print(f"Error en registro: {e}")
            return "Error al guardar tu registro. Intenta de nuevo."

    def determinar_zona(self, ubicacion: str) -> int:
        ubicacion = ubicacion.lower()
        if "santiago" in ubicacion: return 2
        elif "constanza" in ubicacion: return 3
        elif "hato mayor" in ubicacion: return 4
        return 1

    def obtener_nombre_zona(self, zona_id: int) -> str:
        return {1: "Azua (Suroeste Seco)", 2: "Santiago (Cibao Húmedo)", 3: "Constanza (Montaña Alta)", 4: "Hato Mayor (Este Húmedo)"}.get(zona_id, "N/A")

    def generar_reporte_inteligente(self, from_number: str, db) -> str:
        try:
            siembra = db.execute(text("""
                SELECT s.id as siembra_id, c.nombre as cultivo, s.fecha_siembra, c.dias_ciclo_promedio, 
                       z.id as zona_id, z.latitud, z.longitud,
                       c.precio_mercado_libra, c.tendencia_precio
                FROM siembras s 
                JOIN usuarios u ON u.id = s.usuario_id 
                JOIN cultivos c ON c.id = s.cultivo_id 
                JOIN zonas_agroecologicas z ON z.id = u.zona_id
                WHERE u.telefono = :p AND s.activa = true ORDER BY s.created_at DESC LIMIT 1
            """), {"p": from_number}).fetchone()
            
            if not siembra: return "No encontré tu cultivo. Envía REGISTRO para empezar."

            datos_clima = clima_service.obtener_clima_historico(lat=siembra.latitud, lon=siembra.longitud, dias_atras=2)
            
            dias = (datetime.now().date() - siembra.fecha_siembra).days
            progreso = round((dias / siembra.dias_ciclo_promedio) * 100, 1) if siembra.dias_ciclo_promedio > 0 else 0
            
            reporte = f"📊 REPORTE DE CULTIVO\n\n🌱 Cultivo: {siembra.cultivo}\n📅 Días: {dias}\n📈 Progreso: {progreso}%\n📍 Zona: {self.obtener_nombre_zona(siembra.zona_id)}\n"

            if datos_clima and datos_clima['historial']['temp_max']:
                lluvia_48h = sum(datos_clima['historial']['lluvia_sum'])
                temp_max_48h = max(datos_clima['historial']['temp_max'])
                
                clima_hoy = f"\n☀️ CLIMA (Hoy)\n   🌡️ Temp. Actual: {datos_clima['actual']['temperatura']}°C\n   💧 Lluvia Hoy: {datos_clima['historial']['lluvia_sum'][-1]} mm\n"
                reporte += clima_hoy
                
                recomendacion = self.generar_recomendacion_climatica(lluvia_48h, temp_max_48h, siembra.cultivo, dias)
                reporte += f"\n💡 SUGERENCIA (basada en últimas 48h)\n   {recomendacion}"

                self.estados_usuario[from_number] = {
                    "esperando_feedback": True,
                    "siembra_id": siembra.siembra_id,
                    "recomendacion": recomendacion
                }
            else:
                reporte += "\nNo se pudieron obtener datos del clima."
            
            if siembra.precio_mercado_libra:
                reporte += f"\n\n💰 Precio Mercado (MERCADOM):\n   RD${siembra.precio_mercado_libra:.2f}/libra ({siembra.tendencia_precio})"

            self.enviar_mensaje(from_number, reporte + "\n\nMi Conuco Smart 🌱")
            return "¿Te sirvió esta sugerencia? (👍/👎)"

        except Exception as e:
            print(f"Error generando reporte: {e}")
            return "Hubo un error al generar tu reporte."
            
    def obtener_etapa_cultivo(self, cultivo: str, dias: int) -> str:
        if cultivo in ["Tomate", "Ají Cubanela", "Habichuela"]:
            if dias < 25: return "Establecimiento / Vegetativo Temprano"
            elif dias < 50: return "Floración"
            elif dias < 75: return "Fructificación / Llenado de Fruto"
            else: return "Maduración / Cosecha"
        elif cultivo == "Yuca":
            if dias < 90: return "Establecimiento"
            elif dias < 240: return "Engrosamiento de Raíces"
            else: return "Maduración"
        return "Desarrollo General"

    def generar_recomendacion_climatica(self, lluvia_48h: float, temp_max_48h: float, cultivo: str, dias_cultivo: int) -> str:
        etapa = self.obtener_etapa_cultivo(cultivo, dias_cultivo)

        if temp_max_48h > 32 and lluvia_48h < 5.0:
            return f"🔥 SUGERENCIA POR CALOR SOSTENIDO: Las temperaturas han sido altas y ha llovido poco ({lluvia_48h}mm en 48h). El suelo está perdiendo humedad. Considera un riego profundo para recargar la reserva de agua de tus plantas."

        if lluvia_48h > 30.0:
            return f"💧 SUGERENCIA POR HUMEDAD ALTA: Ha llovido bastante ({lluvia_48h}mm en 48h). El riesgo de hongos es elevado. Es un buen momento para revisar el drenaje y asegurar buena ventilación en tu cultivo de {cultivo}."

        else:
            recomendacion = f"✅ Condiciones estables en las últimas 48h. Tu cultivo está en '{etapa}'.\n   💡 TIP: "
            if etapa == "Floración":
                recomendacion += "Es una fase crítica. Un buen nivel de Fósforo (P) y Potasio (K) puede mejorar la calidad de las flores y futuros frutos."
            else:
                recomendacion += "Es un buen día para continuar con las labores de rutina planificadas para esta etapa."
            return recomendacion

    def guardar_feedback(self, from_number: str, respuesta: str, db):
        try:
            estado = self.estados_usuario.get(from_number, {})
            siembra_id = estado.get("siembra_id")
            recomendacion = estado.get("recomendacion")

            if not siembra_id:
                print(f"No se pudo guardar feedback para {from_number}: no se encontró siembra_id.")
                return

            db.execute(text("""
                INSERT INTO feedback_recomendaciones (siembra_id, recomendacion_texto, respuesta_usuario)
                VALUES (:sid, :rt, :ru)
            """), {"sid": siembra_id, "rt": recomendacion, "ru": respuesta})
            db.commit()
            print(f"Feedback '{respuesta}' guardado para siembra {siembra_id}.")
        
        except Exception as e:
            db.rollback()
            print(f"Error al guardar feedback: {e}")

    def mostrar_ayuda(self) -> str:
        return "MI CONUCO SMART - AYUDA\n\n📝 REGISTRO\n📊 REPORTE\n❓ AYUDA\n\nCultivos: Tomate, Ají, Banano, Habichuela, Yuca"

whatsapp_service = WhatsAppService()