34from fastapi import FastAPI

app = FastAPI(
    title="Mi Conuco Smart",
    description="Sistema de alertas climáticas para agricultores dominicanos",
    version="1.0.0"
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

@app.get("/cultivos")
async def get_cultivos():
    return {
        "cultivos": [
            {"codigo": "TOM", "nombre": "Tomate"},
            {"codigo": "AJI", "nombre": "Ají Cubanela"}, 
            {"codigo": "BAN", "nombre": "Banano"},
            {"codigo": "HAB", "nombre": "Habichuela"},
            {"codigo": "YUC", "nombre": "Yuca"}
        ]
    }