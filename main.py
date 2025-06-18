from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

class Stream(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str

class Material(BaseModel):
    material_id: str
    nombre: str
    acr_id: str
    fechas: List[str]
    horarios: List[str]
    streams: List[str]

class Proyecto(BaseModel):
    proyecto_id: str
    cliente_id: str
    nombre: str
    marca: str
    producto: str
    materiales: List[Material]
    reportes: List[str]

@app.post("/crear-proyecto")
def crear_proyecto(proyecto: Proyecto):
    return {"mensaje": "Proyecto recibido", "proyecto": proyecto}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

