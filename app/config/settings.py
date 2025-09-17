from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Base de datos
    database_url: str = "postgresql://usuario:password@localhost:5432/mi_conuco_smart"
    
    # Twilio
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Redis para Celery
    redis_url: str = "redis://localhost:6379/0"
    
    # Configuración general
    debug: bool = True
    secret_key: str = "mi-conuco-smart-secret-key-cambiar-en-produccion"
    
    class Config:
        env_file = ".env"

settings = Settings()
