import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional
from datetime import datetime
import pandas as pd

app = FastAPI()


# Modelos de validación
class Horario(BaseModel):
    hora_exacta: str


class Material(BaseModel):
    nombre: str
    acr_id: str
    fechas_activas: List[str]
    horarios: List[Horario]
    streams: List[str]
    categoria: str
    conflicto_con: Optional[List[str]] = []
    back_to_back: Optional[List[str]] = []


class Stream(BaseModel):
    stream_id: str
    nombre: str
    url_stream: str


class Proyecto(BaseModel):
    proyecto_id: str
    nombre: str
    cliente: str
    agencia: Optional[str] = ""
    marca: str
    producto: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipo_reportes: List[str]
    destinatarios: List[EmailStr]
    materiales: List[Material]
    streams_catalogo: List[Stream]

    @validator("tipo_reportes", each_item=True)
    def validate_tipo_reportes(cls, v):
        permitidos = {"diario", "total"}
        if v not in permitidos:
            raise ValueError(f"Tipo de reporte inválido: {v}")
        return v


@app.post("/generar-reporte")
async def generar_reporte(proyecto: Proyecto):
    try:
        # Ruta de archivo temporal
        file_name = "reporte_simulado.xlsx"

        # Simulación de datos
        datos = []
        for mat in proyecto.materiales:
            for fecha in mat.fechas_activas:
                for horario in mat.horarios:
                    datos.append({
                        "Proyecto": proyecto.nombre,
                        "Material": mat.nombre,
                        "Fecha": fecha,
                        "Hora exacta": horario.hora_exacta,
                        "Stream ID": ", ".join(mat.streams),
                        "Categoría": mat.categoria,
                        "Conflictos": ", ".join(mat.conflicto_con),
                        "Back to Back": ", ".join(mat.back_to_back),
                    })

        df = pd.DataFrame(datos)
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Reporte", index=False)

        return FileResponse(file_name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=file_name)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    return {"message": "pong"}
