from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Mi Conuco Smart",
    description="Sistema de alertas climáticas para agricultores dominicanos",
    version="1.0.0"
)

# Configurar CORS para permitir llamadas desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción cambiar por dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Mi Conuco Smart API está funcionando",
        "status": "activo",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
