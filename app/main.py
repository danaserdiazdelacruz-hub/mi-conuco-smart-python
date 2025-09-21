from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session
from .config.database import get_db, test_connection
from .services.whatsapp_service import whatsapp_service

app = FastAPI(
    title="Mi Conuco Smart",
    description="Sistema de Inteligencia Agrícola para WhatsApp con Bird",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando Mi Conuco Smart (Modo Bird)...")
    if test_connection():
        print("✅ Conexión a PostgreSQL verificada.")
    else:
        print("❌ ERROR: No se pudo conectar a PostgreSQL.")

@app.get("/")
def root():
    return {"message": "Mi Conuco Smart API v2.0 (Bird) funcionando"}

@app.post("/whatsapp")
async def webhook_bird(request: Request, db: Session = Depends(get_db)):
    """
    Webhook para recibir mensajes de WhatsApp desde Bird
    """
    try:
        data = await request.json()
        
        print(f"--- Webhook de Bird recibido ---")
        print(data)
        print("---------------------------------")

        # Verificar que sea un mensaje entrante de WhatsApp
        if data.get('event') == 'whatsapp.inbound':
            payload = data.get('payload', {})
            
            # Extraer datos según la estructura real de Bird
            from_number = payload.get('sender', {}).get('contact', {}).get('identifierValue')
            contenido = payload.get('body', {}).get('text', {}).get('text')
            
            if from_number and contenido:
                print(f"Mensaje de '{from_number}' dice: '{contenido}'")
                
                # Procesar con el servicio de WhatsApp
                respuesta = whatsapp_service.procesar_mensaje_entrante(from_number, contenido, db)
                
                if respuesta:
                    print(f"Enviando respuesta a '{from_number}': '{respuesta}'")
                    whatsapp_service.enviar_mensaje(from_number, respuesta)
                
                return {"status": "ok", "message": "Mensaje procesado"}
            else:
                print(f"Datos faltantes - from: {from_number}, contenido: {contenido}")
                
    except Exception as e:
        print(f"❌ ERROR en webhook Bird: {e}")
        return {"status": "error", "detail": str(e)}

    return {"status": "ignored", "message": "Evento no procesado"}

@app.get("/health")
def health_check():
    """
    Verificar estado del sistema y base de datos
    """
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "sistema": "Mi Conuco Smart v2.0 (Bird)"
    }