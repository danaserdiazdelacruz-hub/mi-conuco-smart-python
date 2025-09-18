# app/main.py - Versión 2 (con endpoint de WhatsApp)

from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI(
    title="Mi Conuco Smart",
    description="Sistema de alertas climáticas para agricultores dominicanos",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "API funcionando"}

# --- WEBHOOK PRINCIPAL DE WHATSAPP ---
@app.post("/whatsapp")
def webhook_whatsapp(From: str = Form(...), Body: str = Form(...)):
    """
    Este es el 'portero' que recibe todos los mensajes de Twilio.
    """
    telefono = From.replace('whatsapp:', '')
    mensaje_entrante = Body.lower().strip()
    
    print(f"Mensaje recibido de {telefono}: '{mensaje_entrante}'") # Log para ver en la terminal
    
    # Por ahora, solo responderemos un eco para probar la conexión
    mensaje_respuesta = f"Recibí tu mensaje: '{mensaje_entrante}'"
    
    # Creamos la respuesta para Twilio
    twiml = MessagingResponse()
    twiml.message(mensaje_respuesta)
    
    return Response(content=str(twiml), media_type="application/xml")