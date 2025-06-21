from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import io
import pandas as pd
import httpx
from datetime import datetime, timedelta
import os

app = FastAPI()

# Configuración ACRCloud
ACR_TOKEN = os.getenv("ACR_BEARER_TOKEN") or "tu_token_bearer_aqui"
ACR_BASE_URL = "https://api.acrcloud.com/v1/monitor/stream/analytics/results"

# Modelos
class Horario(BaseModel):
    hora_exacta: str  # formato HH:MM

class Material(BaseModel):
    nombre: str
    acr_id: str
    fechas_activas: List[str]
    horarios: List[Horario]
    streams: List[str]
    categoria: str
    conflicto_con: List[str]
    back_to_back: List[str]

class Stream(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str

class ProyectoRequest(BaseModel):
    proyecto_id: str
    nombre: str
    cliente: str
    agencia: Optional[str]
    marca: str
    producto: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipo_reportes: List[str]
    destinatarios: List[str]
    materiales: List[Material]
    streams_catalogo: List[Stream]

# Función para consultar ACRCloud
async def obtener_detecciones(acr_id: str, stream_id: str, fecha: str):
    url = f"{ACR_BASE_URL}?acr_id={acr_id}&stream_id={stream_id}&date={fecha}&timezone=-6"
    headers = {"Authorization": f"Bearer {ACR_TOKEN}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()

@app.post("/generar-reporte")
async def generar_reporte(data: ProyectoRequest):
    pautados = []
    faltantes = []

    for material in data.materiales:
        for fecha in material.fechas_activas:
            for stream_id in material.streams:
                detecciones = await obtener_detecciones(material.acr_id, stream_id, fecha)
                detectados = [
                    datetime.strptime(d["timestamp"], "%Y-%m-%d %H:%M:%S")
                    for d in detecciones.get("data", [])
                ]

                for horario in material.horarios:
                    hora_obj = datetime.strptime(f"{fecha} {horario.hora_exacta}", "%Y-%m-%d %H:%M")
                    encontrado = any(
                        abs((hora_obj - detect).total_seconds()) <= data.tolerancia_minutos * 60
                        for detect in detectados
                    )
                    resultado = {
                        "fecha": fecha,
                        "hora": horario.hora_exacta,
                        "material": material.nombre,
                        "stream_id": stream_id,
                        "estado": "Pautado" if encontrado else "Faltante"
                    }
                    if encontrado:
                        pautados.append(resultado)
                    else:
                        faltantes.append(resultado)

    # Generar Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        pd.DataFrame(pautados).to_excel(writer, sheet_name="Pautados", index=False)
        pd.DataFrame(faltantes).to_excel(writer, sheet_name="Faltantes", index=False)

    output.seek(0)
    filename = "reporte_acrcloud.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
