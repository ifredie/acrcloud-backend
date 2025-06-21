from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
import io
import httpx
import openpyxl
from collections import defaultdict

ACRCLOUD_BASE_URL = "https://api-v2.acrcloud.com/api/bm-cs-projects"
ACRCLOUD_BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI3IiwianRpIjoiNjYwODQwOTYxMzRiNWM5NjljODY2NDMwMGNiZDFjNzllM2NmZjhiODBkN2Q0ZmY4MTMyYTFmN2QzNGI5NTBjMmFmNTk3ODNhMGJlYjRmMzciLCJpYXQiOjE3MzIyMjA3NDcuNzczMjI4LCJuYmYiOjE3MzIyMjA3NDcuNzczMjMxLCJleHAiOjIwNDc3NTM1NDcuNzI2MDMyLCJzdWIiOiIxNTMzMjUiLCJzY29wZXMiOlsiKiIsIndyaXRlLWFsbCIsInJlYWQtYWxsIiwiYnVja2V0cyIsIndyaXRlLWJ1Y2tldHMiLCJyZWFkLWJ1Y2tldHMiLCJhdWRpb3MiLCJ3cml0ZS1hdWRpb3MiLCJyZWFkLWF1ZGlvcyIsImNoYW5uZWxzIiwid3JpdGUtY2hhbm5lbHMiLCJyZWFkLWNoYW5uZWxzIiwiYmFzZS1wcm9qZWN0cyIsIndyaXRlLWJhc2UtcHJvamVjdHMiLCJyZWFkLWJhc2UtcHJvamVjdHMiLCJ1Y2YiLCJ3cml0ZS11Y2YiLCJyZWFkLXVjZiIsImRlbGV0ZS11Y2YiLCJibS1wcm9qZWN0cyIsImJtLWNzLXByb2plY3RzIiwid3JpdGUtYm0tY3MtcHJvamVjdHMiLCJyZWFkLWJtLWNzLXByb2plY3RzIiwiYm0tYmQtcHJvamVjdHMiLCJ3cml0ZS1ibS1iZC1wcm9qZWN0cyIsInJlYWQtYm0tYmQtcHJvamVjdHMiLCJmaWxlc2Nhbm5pbmciLCJ3cml0ZS1maWxlc2Nhbm5pbmciLCJyZWFkLWZpbGVzY2FubmluZyIsIm1ldGFkYXRhIiwicmVhZC1tZXRhZGF0YSJdfQ.b0XSJI7YCgd-AWGCLMdPJWo84470QNqovjtp34TKqrjlrnURCEqoI5jE3pBqqKqkVzh46HQjqtyIj7ge7JbNrEichHClKFIGW-JCrxYk-Oo8iDoWq8u-kCARPUrhAUMB_krK2PkkONN21gN4ZguFXgqBEZg2DwincaZhtDGKlM4MbQ9ctMgGapaHQXGa2SyoBQI9fZdNpQrTIplYznKZ2k8g86_8M9Be-tSpPBFEq0nwCKWF_Ya8USU_lxQUiOmAr4Wo5A0mi2FFeUIY7h4AhgP_LkgOwUMVt2JP95edVLlzUuRRVGkW1BG7536V4K51NOh4zr6tK28dixEQCuMj3nPHNG6w0VsT80yVU8mJTcOKxcjCexJNfwoyyAHRJblx6xsG2IZYECCJM0NFRv9GVMKLp2IUKTYM741HnpIGNowav6sNXsRgM8aVPXghf4jbJwfbuzC6XWD3hnQ0D5ybD-V9wAvkEJ0lIIDdkfrMZLW-bI1ju0oRV2CzFl-NpVRqjRp8tBM--6oq51LPx_qm_6CzZsUC6qQeBc1uFL39g_UbbmR4nT4y9w_ENSq1VDz9t8jDdas2arY8T1YzDQW1unbA2UfsyVc57YD4xjcWSLGrFbceS2SvQkGyqEHtB_riLZhl-x9rt8BCw73aFEu7WfOTOLgPs_y-rwgsVeQcKLc"
OFFSET_HORARIO = -6

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
                for fecha_consulta in [fecha, (datetime.strptime(fecha, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")]:
                    fecha_formateada = fecha_consulta.replace("-", "")
                    resultado = await get_results_from_acrcloud(payload.proyecto_id, stream_id, fecha_formateada)
                    if "error" in resultado:
                        return JSONResponse(content=resultado, status_code=500)

                    for deteccion in resultado.get("data", []):
                        timestamp_utc = deteccion.get("metadata", {}).get("timestamp_utc", "")
                        try:
                            dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                            dt_local = dt_utc + timedelta(hours=OFFSET_HORARIO)
                            hora_local = dt_local.strftime("%H:%M:%S")
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
                                hora_detectada_dt = datetime.strptime(f"{r['fecha']} {r['hora']}", "%Y-%m-%d %H:%M:%S")
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
