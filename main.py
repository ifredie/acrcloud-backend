from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import uuid
import os

app = FastAPI()

class Horario(BaseModel):
    hora_exacta: str

class Stream(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str

class Material(BaseModel):
    nombre: str
    acr_id: str
    fechas_activas: List[str]
    horarios: List[Horario]
    streams: List[str]
    categoria: str
    conflicto_con: Optional[List[str]] = []
    back_to_back: Optional[List[str]] = []

class ProyectoRequest(BaseModel):
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
    streams_catalogo: List[Stream]

@app.get("/")
def read_root():
    return {"message": "Backend ACRCloud funcionando correctamente"}

@app.post("/generar-reporte")
async def generar_reporte(request: ProyectoRequest):
    detecciones = []
    for material in request.materiales:
        for fecha in material.fechas_activas:
            for horario in material.horarios:
                for stream_id in material.streams:
                    stream_info = next((s for s in request.streams_catalogo if s.stream_id == stream_id), None)
                    if stream_info:
                        detecciones.append({
                            "Fecha": fecha,
                            "Hora esperada": horario.hora_exacta,
                            "Hora detectada": horario.hora_exacta,
                            "Material": material.nombre,
                            "ACR_ID": material.acr_id,
                            "Stream": stream_info.nombre,
                            "URL Stream": stream_info.url_stream
                        })

    df = pd.DataFrame(detecciones)
    filename = f"/mnt/data/reporte_{request.proyecto_id}_{uuid.uuid4().hex[:6]}.xlsx"
    df.to_excel(filename, index=False)

    return FileResponse(
        path=filename,
        filename=os.path.basename(filename),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ != "main":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
