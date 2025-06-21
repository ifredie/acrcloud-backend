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
    headers = {
        "Authorization": f"Bearer {ACRCLOUD_BEARER_TOKEN}",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        return {"error": response.text, "codigo": response.status_code, "detalle": f"Error en stream {stream_id} con fecha {date}"}

def generar_excel(data: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append(["Fecha", "Hora Detectada", "Hora Pautada", "ACR_ID", "Título", "Stream", "Estado"])

    for item in data.get("detectados", []):
        ws.append([
            item["fecha"], item["hora"], item["hora_pautada"],
            item["acr_id"], item["titulo"], item["stream"], "DETECTADO"
        ])

    for item in data.get("faltantes", []):
        ws.append([
            item["fecha"], "", item["hora_pautada"],
            item["acr_id"], "FALTANTE", item["stream"], "FALTANTE"
        ])

    for item in data.get("fuera_horario", []):
        ws.append([
            item["fecha"], item["hora"], "", item["acr_id"],
            item["titulo"], item["stream"], "FUERA DE HORARIO"
        ])

    # Hoja resumen
    resumen = wb.create_sheet("Resumen")
    resumen.append(["Fecha", "Stream", "Detectados", "Faltantes", "Fuera de horario", "Total"])
    resumen_data = defaultdict(lambda: {"detectados": 0, "faltantes": 0, "fuera_horario": 0})

    for item in data.get("detectados", []):
        key = (item["fecha"], item["stream"])
        resumen_data[key]["detectados"] += 1
    for item in data.get("faltantes", []):
        key = (item["fecha"], item["stream"])
        resumen_data[key]["faltantes"] += 1
    for item in data.get("fuera_horario", []):
        key = (item["fecha"], item["stream"])
        resumen_data[key]["fuera_horario"] += 1

    for (fecha, stream), valores in resumen_data.items():
        total = sum(valores.values())
        resumen.append([fecha, stream, valores["detectados"], valores["faltantes"], valores["fuera_horario"], total])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@app.post("/generar-reporte")
async def generar_reporte(payload: ProyectoRequest):
    detectados = []
    faltantes = []
    fuera_horario = []

    todas_detectadas_set = set()  # Para evitar duplicados
    materiales_by_acr = {mat.acr_id: mat for mat in payload.materiales}

    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                fecha_formateada = fecha.replace("-", "")
                resultado = await get_results_from_acrcloud(payload.proyecto_id, stream_id, fecha_formateada)
                if "error" in resultado:
                    return JSONResponse(content=resultado, status_code=500)

                matches_por_hora = []

                for deteccion in resultado.get("data", []):
                    metadata = deteccion.get("metadata", {})
                    for item in metadata.get("custom_files", []):
                        if item.get("acrid") != material.acr_id:
                            continue
                        timestamp_utc = metadata.get("timestamp_utc", "")
                        if not timestamp_utc:
                            continue
                        dt_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S")
                        dt_local = dt_utc - timedelta(hours=6)
                        hora_local = dt_local.strftime("%H:%M")
                        fecha_local = dt_local.strftime("%Y-%m-%d")

                        # Intentar emparejar con alguno de los horarios
                        emparejado = False
                        for hora_pautada in material.horarios:
                            pauta_dt = datetime.strptime(f"{fecha} {hora_pautada}", "%Y-%m-%d %H:%M")
                            if abs((dt_local - pauta_dt).total_seconds()) <= payload.tolerancia_minutos * 60:
                                if (material.acr_id, stream_id, fecha, hora_pautada) not in todas_detectadas_set:
                                    detectados.append({
                                        "fecha": fecha,
                                        "hora": hora_local,
                                        "hora_pautada": hora_pautada,
                                        "acr_id": material.acr_id,
                                        "titulo": item.get("title", ""),
                                        "stream": stream_id
                                    })
                                    todas_detectadas_set.add((material.acr_id, stream_id, fecha, hora_pautada))
                                    emparejado = True
                                    break

                        # Si no se emparejó con ninguna pauta
                        if not emparejado:
                            key_unique = (material.acr_id, stream_id, fecha_local, hora_local)
                            if key_unique not in todas_detectadas_set:
                                fuera_horario.append({
                                    "fecha": fecha_local,
                                    "hora": hora_local,
                                    "acr_id": material.acr_id,
                                    "titulo": item.get("title", ""),
                                    "stream": stream_id
                                })
                                todas_detectadas_set.add(key_unique)

    # Detectar faltantes
    for material in payload.materiales:
        for stream_id in material.stream_ids:
            for fecha in material.fechas:
                for hora in material.horarios:
                    if (material.acr_id, stream_id, fecha, hora) not in todas_detectadas_set:
                        faltantes.append({
                            "fecha": fecha,
                            "hora_pautada": hora,
                            "acr_id": material.acr_id,
                            "stream": stream_id
                        })

    excel = generar_excel({
        "detectados": detectados,
        "faltantes": faltantes,
        "fuera_horario": fuera_horario
    })

    fecha_actual = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"reporte_{fecha_actual}.xlsx"
    return StreamingResponse(excel, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
