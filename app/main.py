# Agregar este endpoint a tu main.py existente

@app.route('/telegram', methods=['POST'])
def handle_telegram_webhook():
    """Maneja los webhooks de Telegram"""
    try:
        data = request.get_json()
        print(f"Webhook Telegram recibido: {data}")
        
        # Verificar que es un mensaje válido
        if not data or 'message' not in data:
            return jsonify({"status": "no message"}), 200
            
        message = data['message']
        
        # Extraer información del mensaje
        chat_id = str(message['chat']['id'])
        text = message.get('text', '').strip()
        
        if not text:
            return jsonify({"status": "empty message"}), 200
            
        print(f"Mensaje de {chat_id}: {text}")
        
        # Procesar mensaje con el servicio existente
        respuesta = whatsapp_service.procesar_mensaje_entrante(chat_id, text, db)
        
        # Enviar respuesta
        if respuesta:
            whatsapp_service.enviar_mensaje(chat_id, respuesta)
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Error procesando webhook Telegram: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# También agregar este endpoint de verificación
@app.route('/telegram/status', methods=['GET'])
def telegram_status():
    """Endpoint para verificar que el bot está funcionando"""
    return jsonify({
        "status": "active",
        "service": "Mi Conuco Smart - Telegram Bot",
        "timestamp": datetime.now().isoformat()
    })