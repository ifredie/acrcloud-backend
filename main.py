from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import io
import httpx
import openpyxl

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = "<AQUÍ_TU_TOKEN_BEARER>"

app = FastAPI()

class Material(BaseModel):
    acr_id: str
    fechas: list[str]  # formato YYYY-MM-DD
    horarios: list[str]  # formato HH:MM
    stream_ids: list[str]
    categoria: str
    conflictos: list[str] = []

class ProyectoRequest(BaseModel):
    proyecto_id: str
    cliente: str
    marca: str
    producto: str
    tipo_cliente: str
    tolerancia_minutos: int
    tipo_reporte: list[str]
    destinatarios: list[str]
    materiales: list[Material]
    catalogo_streams: dict

async def get_results_from_acrcloud(project_id: str, stream_id: str, date: str):
    url = f"{ACRCLOUD_BASE_URL}/{project_id}/streams/{stream_id}/results"
    params = {"date": date, "with_false_positive": 0}
    headers = {
        "Authorization": f"Bearer {ACRCLOUD_BEARER_TOKEN}",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text, "codigo": response.status_code, "detalle": f"Error en stream {stream_id} con fecha {date}"}

def generar_excel(data: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Fecha", "Hora Detectada", "Hora Pautada", "ACR_ID", "Título", "Stream", "Estado", "Desfase (minutos)"])

    for item in data.get("detected", []):
        ws.append([
            item["fecha"], item["hora"], item["hora_pautada"], item["acr_id"],
            item["titulo"], item["stream"], item["estado"], item["desfase"]
        ])

    for item in data.get("faltantes", []):
        ws.append([
            item["fecha"], "", item["hora_pautada"], item["acr_id"],
            "FALTANTE", item["stream"], "FALTANTE", ""
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.post("/generar-reporte")
async def generar_reporte(payload: ProyectoRequest):
    resultados = []
    fechas_consultadas = set()

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                for extra in [0, 1]:  # Consultar el día y el día siguiente
                    fecha_obj = datetime.strptime(fecha, "%Y-%m-%d") + timedelta(days=extra)
                    fecha_formateada = fecha_obj.strftime("%Y%m%d")
                    if (stream_id, fecha_formateada) in fechas_consultadas:
                        continue
                    fechas_consultadas.add((stream_id, fecha_formateada))

                    resultado = await get_results_from_acrcloud(payload.proyecto_id, stream_id, fecha_formateada)
                    if "error" in resultado:
                        return JSONResponse(content=resultado, status_code=500)

                    for deteccion in resultado.get("data", []):
                        for item in deteccion.get("metadata", {}).get("custom_files", []):
                            if item.get("acrid") == material.acr_id:
                                timestamp_utc = deteccion.get("metadata", {}).get("timestamp_utc", "")
                                try:
                                    dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                                    dt_local = dt_utc - timedelta(hours=6)
                                    hora_local = dt_local.strftime("%H:%M")
                                    fecha_local = dt_local.strftime("%Y-%m-%d")
                                except:
                                    hora_local = ""
                                    fecha_local = fecha

                                resultados.append({
                                    "fecha": fecha_local,
                                    "hora": hora_local,
                                    "acr_id": material.acr_id,
                                    "titulo": item.get("title", ""),
                                    "stream": stream_id
                                })

    resultados_finales = []
    faltantes = []
    detectados_ids = set()

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                for hora in material.horarios:
                    hora_objetivo_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                    encontrado = False

                    for r in resultados:
                        if r["acr_id"] == material.acr_id and r["stream"] == stream_id:
                            hora_detectada_dt = datetime.strptime(f"{r['fecha']} {r['hora']}", "%Y-%m-%d %H:%M")
                            desfase = int((hora_detectada_dt - hora_objetivo_dt).total_seconds() / 60)
                            if abs(desfase) <= payload.tolerancia_minutos:
                                resultados_finales.append({**r, "hora_pautada": hora, "estado": "DETECTADO", "desfase": desfase})
                                detectados_ids.add((r['fecha'], r['hora'], r['acr_id'], r['stream']))
                                encontrado = True
                                break

                    if not encontrado:
                        faltantes.append({
                            "fecha": fecha,
                            "hora_pautada": hora,
                            "acr_id": material.acr_id,
                            "stream": stream_id
                        })

    # Agregar fuera de horario
    for r in resultados:
        key = (r['fecha'], r['hora'], r['acr_id'], r['stream'])
        if key not in detectados_ids:
            resultados_finales.append({**r, "hora_pautada": "", "estado": "FUERA DE HORARIO", "desfase": ""})

    excel = generar_excel({"detected": resultados_finales, "faltantes": faltantes})
    filename = f"reporte_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

    return StreamingResponse(excel, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
