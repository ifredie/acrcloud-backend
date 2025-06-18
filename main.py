from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List
import os

app = FastAPI()

# Modelos
class StreamConfig(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str

class Horario(BaseModel):
    hora_exacta: str  # Ejemplo: "08:15"

class Material(BaseModel):
    nombre: str
    acr_id: str
    fechas_activas: List[str]  # Ej: ["2025-06-17", "2025-06-18"]
    horarios: List[Horario]
    streams: List[str]
    categoria: str
    conflicto_con: List[str] = Field(default_factory=list)
    back_to_back: List[str] = Field(default_factory=list)

class Proyecto(BaseModel):
    proyecto_id: str
    nombre: str
    cliente: str
    agencia: str
    marca: str
    producto: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipo_reportes: List[str]
    destinatarios: List[str]
    materiales: List[Material]
    streams_catalogo: List[StreamConfig]

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/subir-proyecto")
async def subir_proyecto(data: Proyecto):
    return {
        "status": "ok",
        "mensaje": f"Proyecto {data.nombre} recibido con {len(data.materiales)} materiales."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
