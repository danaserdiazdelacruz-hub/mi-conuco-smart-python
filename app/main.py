from fastapi import FastAPI, Form, Depends
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session

# Importaciones corregidas para que funcionen desde el inicio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import get_db, test_connection
from services.whatsapp_service import whatsapp_service

# --- Creación de la App FastAPI ---
app = FastAPI(
    title="Mi Conuco Smart",
    description="Sistema de Inteligencia Agrícola Conversacional",
    version="1.0.0"
)

# --- Evento de Arranque ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando Mi Conuco Smart...")
    if test_connection():
        print("✅ Conexión a PostgreSQL verificada")
        print("🌱 Sistema de alertas climáticas listo")
    else:
        print("❌ Error: No se puede conectar a PostgreSQL")

# --- Endpoints de la API ---

@app.get("/")
def root():
    return {
        "message": "Mi Conuco Smart API funcionando",
        "status": "Sistema de Inteligencia Agrícola Conversacional activo"
    }

@app.post("/whatsapp")
def webhook_whatsapp(From: str = Form(...), Body: str = Form(...), db: Session = Depends(get_db)):
    """
    Webhook principal para WhatsApp con inteligencia conversacional
    """
    telefono = From.replace('whatsapp:', '')
    
    print(f"Mensaje recibido de {telefono}: '{Body}'")
    
    # Procesar el mensaje con el "cerebro" inteligente (whatsapp_service)
    respuesta = whatsapp_service.procesar_mensaje_entrante(telefono, Body, db)
    
    # Crear y enviar la respuesta para Twilio
    twiml = MessagingResponse()
    twiml.message(respuesta)
    
    print(f"Respuesta enviada: {respuesta}") # Log para ver la respuesta en terminal
    return Response(content=str(twiml), media_type="application/xml")

@app.post("/test/sms")
def test_sms(numero: str, mensaje: str):
    """Endpoint para probar envío directo de mensajes"""
    enviado = whatsapp_service.enviar_mensaje(numero, mensaje)
    return {"enviado": enviado}

@app.get("/health")
def health_check():
    """Verificar estado del sistema y la base de datos"""
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "sistema": "Sistema de Inteligencia Agrícola Conversacional"
    }