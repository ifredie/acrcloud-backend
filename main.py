from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import io
import httpx
import openpyxl
from collections import defaultdict

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."

app = FastAPI()

class Material(BaseModel):
    acr_id: str
    fechas: list[str]
    horarios: list[str]
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
    headers = {"Authorization": f"Bearer {ACRCLOUD_BEARER_TOKEN}", "Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.text, "codigo": response.status_code, "detalle": f"Error en stream {stream_id} con fecha {date}"}

def generar_excel(data: dict, resumen: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Fecha", "Hora Detectada", "Hora Pautada", "ACR_ID", "Título", "Stream", "Estado", "Desfase (min)"])

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

    resumen_ws = wb.create_sheet(title="Resumen Diario")
    resumen_ws.append(["Fecha", "Stream", "Detectados", "Faltantes", "Fuera de Horario", "Total"])
    total_detectados = total_faltantes = total_fuera_horario = 0

    for (fecha, stream), conteo in resumen.items():
        detectados = conteo.get("detectados", 0)
        faltantes = conteo.get("faltantes", 0)
        fuera_horario = conteo.get("fuera_horario", 0)
        total = detectados + fuera_horario
        resumen_ws.append([fecha, stream, detectados, faltantes, fuera_horario, total])
        total_detectados += detectados
        total_faltantes += faltantes
        total_fuera_horario += fuera_horario

    resumen_ws.append(["TOTAL", "", total_detectados, total_faltantes, total_fuera_horario, total_detectados - total_faltantes + total_fuera_horario])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.post("/generar-reporte")
async def generar_reporte(payload: ProyectoRequest):
    resultados = []

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                fecha_formateada = fecha.replace("-", "")
                resultado = await get_results_from_acrcloud(payload.proyecto_id, stream_id, fecha_formateada)
                if "error" in resultado:
                    return JSONResponse(content=resultado, status_code=500)

                for deteccion in resultado.get("data", []):
                    timestamp_utc = deteccion.get("metadata", {}).get("timestamp_utc", "")
                    try:
                        dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                        dt_local = dt_utc - timedelta(hours=6)
                        hora_local = dt_local.strftime("%H:%M")
                        fecha_local = dt_local.strftime("%Y-%m-%d")
                    except:
                        continue

                    for item in deteccion.get("metadata", {}).get("custom_files", []):
                        if item.get("acrid") == material.acr_id:
                            resultados.append({
                                "fecha": fecha_local,
                                "hora": hora_local,
                                "acr_id": material.acr_id,
                                "titulo": item.get("title", ""),
                                "stream": stream_id
                            })

    faltantes = []
    resultados_finales = []
    fuera_horario = []
    resumen_diario = defaultdict(lambda: {"detectados": 0, "faltantes": 0, "fuera_horario": 0})

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                for hora in material.horarios:
                    hora_objetivo_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                    detectado = None

                    for r in resultados:
                        if r["acr_id"] == material.acr_id and r["stream"] == stream_id:
                            try:
                                hora_detectada_dt = datetime.strptime(f"{r['fecha']} {r['hora']}", "%Y-%m-%d %H:%M")
                            except:
                                continue
                            desfase = int((hora_detectada_dt - hora_objetivo_dt).total_seconds() / 60)
                            if abs(desfase) <= payload.tolerancia_minutos:
                                detectado = {
                                    **r,
                                    "hora_pautada": hora,
                                    "estado": "DETECTADO",
                                    "desfase": desfase
                                }
                                break

                    if detectado:
                        resultados_finales.append(detectado)
                        resumen_diario[(fecha, stream_id)]["detectados"] += 1
                    else:
                        faltantes.append({
                            "fecha": fecha,
                            "hora_pautada": hora,
                            "acr_id": material.acr_id,
                            "stream": stream_id
                        })
                        resumen_diario[(fecha, stream_id)]["faltantes"] += 1

            for r in resultados:
                if r["acr_id"] == material.acr_id and r["stream"] == stream_id:
                    ya_detectado = any(
                        d["fecha"] == r["fecha"] and d["hora"] == r["hora"] and d["stream"] == r["stream"] for d in resultados_finales
                    )
                    if not ya_detectado:
                        fuera_horario.append({
                            **r,
                            "hora_pautada": "",
                            "estado": "FUERA DE HORARIO",
                            "desfase": ""
                        })
                        resumen_diario[(r["fecha"], r["stream"])]["fuera_horario"] += 1

    excel = generar_excel({"detected": resultados_finales + fuera_horario, "faltantes": faltantes}, resumen_diario)
    fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"reporte_{fecha_actual}.xlsx"

    return StreamingResponse(excel, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
