import os
import unicodedata
from typing import Dict, Optional
from datetime import datetime, timedelta
import re
import requests
from dotenv import load_dotenv
from sqlalchemy import text
from .clima_service import clima_service  # CON PUNTO

load_dotenv()

class WhatsAppService:
    def __init__(self):
        # Cambio a Telegram Bot API
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN no configurado en el archivo .env")
        
        self.telegram_base_url = f"https://api.telegram.org/bot{self.telegram_token}"
        
        self.estados_usuario = {}
        self.cultivos_data = {
            "1": {"nombre": "Tomate", "codigo": "TOM", "ciclo_dias": 90},
            "2": {"nombre": "Ají Cubanela", "codigo": "AJI", "ciclo_dias": 120},
            "3": {"nombre": "Banano", "codigo": "BAN", "ciclo_dias": 365}
        }

    def enviar_mensaje(self, chat_id: str, mensaje: str) -> bool:
        """Envía mensaje vía Telegram Bot API"""
        url = f"{self.telegram_base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print(f"Mensaje enviado a {chat_id}")
                return True
            else:
                print(f"Error enviando mensaje: {response.status_code}")
                print(response.json())
                return False
        except Exception as e:
            print(f"Error inesperado enviando mensaje: {e}")
            return False

    def limpiar_texto(self, texto: str) -> str:
        """Limpia texto: mayúsculas, sin tildes, sin espacios extra"""
        texto = texto.upper().strip()
        texto = ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )
        return texto

    def normalizar_comando(self, mensaje: str) -> str:
        """Convierte sinónimos a comandos estándar"""
        mensaje = self.limpiar_texto(mensaje)
        sinonimos = {
            "REGISTRAR": "REGISTRO",
            "APUNTAR": "REGISTRO",
            "ANOTAR": "REGISTRO",
            "CLIMA": "REPORTE",
            "CLIMITA": "REPORTE", 
            "PRECIO": "REPORTE",
            "PRECIOS": "REPORTE",
            "INFO": "AYUDA",
            "INFORMACION": "AYUDA",
            "/START": "AYUDA",  # Comando típico de Telegram
            "/HELP": "AYUDA"
        }
        return sinonimos.get(mensaje, mensaje)

    def normalizar_cultivo(self, mensaje: str) -> str:
        """Acepta cultivos por número o nombre"""
        mensaje = self.limpiar_texto(mensaje)
        
        if mensaje in self.cultivos_data:
            return mensaje
            
        nombres = {
            "TOMATE": "1",
            "AJI": "2",
            "CUBANELA": "2",
            "BANANO": "3",
            "BANANA": "3",
            "PLATANO": "3"
        }
        return nombres.get(mensaje, None)

    def procesar_mensaje_entrante(self, chat_id: str, mensaje: str, db) -> str:
        comando_normalizado = self.normalizar_comando(mensaje)
        
        if chat_id in self.estados_usuario:
            return self.continuar_conversacion(chat_id, mensaje, db)
        
        comandos = {
            "REGISTRO": lambda: self.iniciar_registro(chat_id, db),
            "REPORTE": lambda: self.generar_reporte_inteligente(chat_id, db),
            "AYUDA": lambda: self.mostrar_ayuda()
        }
        
        if comando_normalizado in comandos:
            return comandos[comando_normalizado]()
        else:
            return "No agarré ese comando, compa. Manda /help o AYUDA pa' ver opciones."

    def mensaje_bienvenida(self) -> str:
        return "¡Dime a ver, compa! 👋 Soy tu Conuco Smart. Manda REGISTRO pa' apuntar siembra o REPORTE pa' ver como va todo."

    def iniciar_registro(self, chat_id: str, db) -> str:
        result = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE telefono = :phone"), {"phone": chat_id})
        if result.fetchone()[0] > 0:
            return "Ya te conozco, manito. Manda REPORTE pa' ver lo de tu siembra."
        
        self.estados_usuario[chat_id] = {"paso": "seleccionar_cultivo"}
        opciones = "\n".join([f"{k}-{v['nombre']}" for k, v in self.cultivos_data.items()])
        return f"¡Claro que si! Vamos a apuntar esa siembra. ¿Que sembraste?\n\n{opciones}\n\n(Manda el numero o el nombre)"

    def continuar_conversacion(self, chat_id: str, mensaje: str, db) -> str:
        estado = self.estados_usuario[chat_id]
        
        pasos = {
            "seleccionar_cultivo": lambda: self.procesar_cultivo(chat_id, mensaje, estado),
            "fecha_siembra": lambda: self.procesar_fecha_siembra(chat_id, mensaje, estado),
            "ubicacion": lambda: self.completar_registro(chat_id, mensaje, estado, db)
        }
        
        if estado["paso"] in pasos:
            return pasos[estado["paso"]]()
        else:
            return "No agarré eso. Manda /help si te perdiste."

    def procesar_cultivo(self, chat_id: str, mensaje: str, estado: Dict) -> str:
        cultivo_id = self.normalizar_cultivo(mensaje)
        
        if cultivo_id and cultivo_id in self.cultivos_data:
            cultivo = self.cultivos_data[cultivo_id]
            estado.update({
                "cultivo_id": cultivo_id, 
                "cultivo_data": cultivo, 
                "paso": "fecha_siembra"
            })
            return f"¡Perfecto! {cultivo['nombre']}. ¿Y cuando fue que lo sembraste?\n\n(Ejemplo: hoy, hace 10 dias, hace 2 semanas)"
        else:
            return "No encontré ese cultivo, compa. Opciones:\n1-Tomate\n2-Ají\n3-Banano"

    def procesar_fecha_siembra(self, chat_id: str, mensaje: str, estado: Dict) -> str:
        fecha_siembra = self.parsear_fecha(mensaje)
        if fecha_siembra:
            dias = (datetime.now().date() - fecha_siembra).days
            estado.update({
                "fecha_siembra": fecha_siembra, 
                "paso": "ubicacion", 
                "dias_transcurridos": dias
            })
            return f"Listo ({dias} dias). Ahora dime, ¿en que municipio o paraje estas?"
        else:
            return "Esa fecha no la agarré bien. Prueba asi:\n• hace 10 dias\n• 15/8/2025"

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

    def completar_registro(self, chat_id: str, ubicacion: str, estado: Dict, db) -> str:
        try:
            zona_id = self.determinar_zona(ubicacion)
            
            db.execute(text("""
                INSERT INTO usuarios (telefono, nombre, status, zona_id) 
                VALUES (:p, :n, 'activo', :z) 
                ON CONFLICT (telefono) DO UPDATE SET status = 'activo', zona_id = :z
            """), {
                "p": chat_id, 
                "n": f"Agricultor {estado['cultivo_data']['nombre']}", 
                "z": zona_id
            })
            
            user_id = db.execute(text("SELECT id FROM usuarios WHERE telefono = :p"), {"p": chat_id}).fetchone()[0]
            cultivo_id = db.execute(text("SELECT id FROM cultivos WHERE codigo = :c"), {"c": estado['cultivo_data']['codigo']}).fetchone()[0]
            
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
            del self.estados_usuario[chat_id]
            
            return f"¡De una! ✅ Apunté tu siembra de {estado['cultivo_data']['nombre']} en {self.obtener_nombre_zona(zona_id)}.\n\nManda REPORTE cuando quieras el dato del tiempo y precios."
            
        except Exception as e:
            db.rollback()
            print(f"Error en registro: {e}")
            return "Se me enredó algo guardando eso. Intenta otra vez mandando REGISTRO."

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
        return 1

    def obtener_nombre_zona(self, zona_id: int) -> str:
        zonas = {1: "Azua", 2: "Santiago", 3: "Constanza", 4: "Hato Mayor"}
        return zonas.get(zona_id, "Zona desconocida")

    def generar_reporte_inteligente(self, chat_id: str, db) -> str:
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
            """), {"p": chat_id}).fetchone()
            
            if not siembra: 
                return "No encontré tu siembra registrada, compa. Manda REGISTRO pa' empezar."

            dias = (datetime.now().date() - siembra.fecha_siembra).days
            progreso = round((dias / siembra.dias_ciclo_promedio) * 100, 1) if siembra.dias_ciclo_promedio > 0 else 0
            
            # Construir encabezado
            cultivo_emoji = {"Tomate": "🍅", "Ají Cubanela": "🌶️", "Banano": "🍌"}.get(siembra.cultivo, "🌱")
            
            reporte = f"<b>{cultivo_emoji} {siembra.cultivo.upper()}</b>\n"
            reporte += f"📅 {dias} dias ({progreso}% de crecimiento)\n"
            reporte += f"📍 {self.obtener_nombre_zona(siembra.zona_id)}\n\n"
            
            # Procesar clima
            datos_clima = clima_service.obtener_clima_actual(lat=siembra.latitud, lon=siembra.longitud)
            
            if datos_clima:
                temp_max = datos_clima.get('temperatura_max_24h')
                humedad = datos_clima.get('humedad_media')
                
                if temp_max is not None:
                    clima_str = f"🌡️ <b>HOY:</b> {temp_max}°C"
                    if humedad is not None:
                        if humedad > 85:
                            clima_str += ", con mucha humedad (bochorno)"
                        elif humedad < 60:
                            clima_str += ", ambiente seco"
                        else:
                            clima_str += ", humedad normal"
                    
                    reporte += clima_str + "\n\n"
                    
                    # Generar recomendación
                    recomendacion = self._generar_recomendacion_estrategica(datos_clima, siembra.cultivo, dias)
                    reporte += f"🔍 <b>REVISAR:</b>\n{recomendacion}\n\n"
                else:
                    reporte += "🌡️ No pude conseguir datos del clima ahora mismo.\n\n"
            else:
                reporte += "🌡️ No pude conseguir el dato del tiempo pa' tu zona.\n\n"
            
            # Agregar precio
            if siembra.precio_mercado_libra:
                fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                reporte += f"💰 <b>Precios MERCADOM - {fecha_hoy}:</b>\n"
                reporte += f"• Detalle: RD${siembra.precio_mercado_libra + 3:.2f}/libra\n"
                reporte += f"• Por mayor: RD${siembra.precio_mercado_libra:.2f}/libra\n\n"

            reporte += "🌱 <i>Mi Conuco Smart</i>"
            return reporte

        except Exception as e:
            print(f"Error generando reporte: {e}")
            return "Hubo un problema generando el reporte. Intenta otra vez en un rato."

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
                return "🔥💧 CALOR Y HUMEDAD: Revisa las hojas por si aparecen manchas. Si ves algo raro, actúa rápido pa' evitar hongos."
            elif humedad and humedad < 60:
                return f"🔥☀️ MUCHO CALOR SECO: {temp_max}°C. Si las hojas se ven agachadas, riégalas temprano y en la tarde."

        if prob_lluvia and prob_lluvia > 50:
            return f"🌧️ VA A LLOVER ({prob_lluvia}%): Mira el cielo antes de regar. Si llueve, te ahorras el agua."

        # Consejos por etapa
        consejos_etapa = {
            "Crecimiento": "🌱 Las plantas están creciendo. Si las hojas se ven pálidas o crecen lento, pueden necesitar abono.",
            "Floración": "🌸 Están saliendo flores. Un abono rico en fósforo ayuda, pero solo si no has abonado recientemente.",
            "Fructificación": "🍅 Los frutos están engordando. Cuida que no les falte agua y vigila las plagas.",
            "Cosecha": "✂️ Tiempo de cosechar. Revisa a diario pa' coger los frutos en su punto.",
            "Establecimiento": "🌱 El banano se está estableciendo. Mantén limpia el área de maleza.",
            "Desarrollo": "🍌 El banano está creciendo. Vigila manchas amarillas en hojas (sigatoka)."
        }

        return consejos_etapa.get(etapa, "✅ Todo se ve normal. Sigue con tus labores normales.")

    def mostrar_ayuda(self) -> str:
        return """<b>🤖 MI CONUCO SMART - COMANDOS:</b>

🌱 <b>REGISTRO</b> (o registrar, apuntar)
   Pa' guardar siembra nueva

📊 <b>REPORTE</b> (o clima, precio)
   Pa' ver como va todo

❓ <b>/help</b> o <b>AYUDA</b>
   Pa' ver estos comandos

<i>Escribe cualquier comando pa' empezar</i>"""

whatsapp_service = WhatsAppService()