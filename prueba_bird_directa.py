import os
import requests
from dotenv import load_dotenv

# Carga las credenciales del archivo .env
load_dotenv()

BIRD_ACCESS_KEY = os.getenv("BIRD_ACCESS_KEY")
BIRD_WHATSAPP_CHANNEL_ID = os.getenv("BIRD_WHATSAPP_CHANNEL_ID")
# --- ¡IMPORTANTE! Pon aquí tu número de WhatsApp para la prueba ---
TO_NUMBER = "+18098643863" 

print("--- DIAGNÓSTICO DE AUTENTICACIÓN DE BIRD ---")

if not BIRD_ACCESS_KEY or not BIRD_WHATSAPP_CHANNEL_ID:
    raise ValueError("Faltan credenciales de Bird en el .env")

# --- Prueba 1: Método "AccessKey" ---
print(f"\n[PRUEBA 1] Intentando con 'AccessKey {BIRD_ACCESS_KEY[-4:]}'...")

url = "https://conversations.messagebird.com/v1/conversations/start"
payload_1 = {"to": TO_NUMBER, "channelId": BIRD_WHATSAPP_CHANNEL_ID, "type": "text", "content": {"text": "Prueba con AccessKey"}}
headers_accesskey = {"Authorization": f"AccessKey {BIRD_ACCESS_KEY}", "Content-Type": "application/json"}

try:
    response_accesskey = requests.post(url, json=payload_1, headers=headers_accesskey)
    if response_accesskey.status_code == 201:
        print("✅ ¡ÉXITO con 'AccessKey'!")
    else:
        print(f"❌ FALLO con 'AccessKey'. Código: {response_accesskey.status_code}")
        print(response_accesskey.json())
except Exception as e:
    print(f"ERROR DE RED (AccessKey): {e}")


# --- Prueba 2: Método "Bearer" ---
print(f"\n[PRUEBA 2] Intentando con 'Bearer {BIRD_ACCESS_KEY[-4:]}'...")

payload_2 = {"to": TO_NUMBER, "channelId": BIRD_WHATSAPP_CHANNEL_ID, "type": "text", "content": {"text": "Prueba con Bearer"}}
headers_bearer = {"Authorization": f"Bearer {BIRD_ACCESS_KEY}", "Content-Type": "application/json"}

try:
    response_bearer = requests.post(url, json=payload_2, headers=headers_bearer)
    if response_bearer.status_code == 201:
        print("✅ ¡ÉXITO con 'Bearer'!")
    else:
        print(f"❌ FALLO con 'Bearer'. Código: {response_bearer.status_code}")
        print(response_bearer.json())
except Exception as e:
    print(f"ERROR DE RED (Bearer): {e}")


print("\n--- Fin del diagnóstico ---")