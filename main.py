from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import os
import pandas as pd
from datetime import datetime

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/subir-proyecto")
async def generar_reporte(request: Request):
    data = await request.json()

    proyecto = data.get("nombre", "Proyecto sin nombre")
    cliente = data.get("cliente", "Sin cliente")
    agencia = data.get("agencia", "Sin agencia")
    marca = data.get("marca", "Sin marca")
    producto = data.get("producto", "Sin producto")

    materiales = data.get("materiales", [])
    rows = []

    for material in materiales:
        nombre_material = material.get("nombre", "Material sin nombre")
        acr_id = material.get("acr_id", "")
        fechas = material.get("fechas_activas", [])
        horarios = material.get("horarios", [])
        streams = material.get("streams", [])
        categoria = material.get("categoria", "")
        conflicto_con = ", ".join(material.get("conflicto_con", []))
        back_to_back = ", ".join(material.get("back_to_back", []))

        for fecha in fechas:
            for horario in horarios:
                hora = horario.get("hora_exacta", "")
                for stream in streams:
                    rows.append({
                        "Proyecto": proyecto,
                        "Cliente": cliente,
                        "Agencia": agencia,
                        "Marca": marca,
                        "Producto": producto,
                        "Material": nombre_material,
                        "Fecha": fecha,
                        "Hora exacta": hora,
                        "Stream ID": stream,
                        "ACR ID": acr_id,
                        "Categoría": categoria,
                        "Conflicto con": conflicto_con,
                        "Back to Back con": back_to_back
                    })

    df = pd.DataFrame(rows)
    archivo = "reporte.xlsx"
    df.to_excel(archivo, index=False)

    return FileResponse(
        path=archivo,
        filename=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
