import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import logging
from database import inicializar_pool, inicializar_db, obtener_usuario, guardar_usuario

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Inicializar el pool de DB ANTES de arrancar
inicializar_pool()
inicializar_db()

@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    telefono = request.values.get('From', '').replace('whatsapp:', '')
    mensaje_entrante = (request.values.get('Body', '') or '').lower().strip()
    
    resp = MessagingResponse()
    mensaje_respuesta = "No entendí. Envía AYUDA."
    
    logging.info(f"Mensaje de {telefono}: '{mensaje_entrante}'")

    try:
        # Lógica de conversación aquí... (la construiremos en el siguiente paso)
        # Por ahora, solo responde que está en construcción.
        
        usuario_data = obtener_usuario(telefono)
        if not usuario_data:
            guardar_usuario({'telefono': telefono, 'estado': 'nuevo'})
            mensaje_respuesta = "¡Bienvenido a Mi Conuco Smart! Te hemos pre-registrado. Envía AYUDA para ver comandos."
        else:
            mensaje_respuesta = f"Hola de nuevo. Tu estado actual es: {usuario_data[7]}"

    except Exception as e:
        logging.error(f"Error crítico en webhook: {e}")
        mensaje_respuesta = "⚠️ Tuvimos un problema técnico. Intenta de nuevo más tarde."

    resp.message(mensaje_respuesta)
    return str(resp)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
