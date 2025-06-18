from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI()

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/test-bubble-key")
def test_bubble_key():
    key = os.getenv("BUBBLE_API_KEY")
    if not key:
        return JSONResponse(status_code=500, content={"error": "BUBBLE_API_KEY no está configurada"})
    return {"message": "BUBBLE_API_KEY está configurada"}

@app.get("/test-acr-token")
def test_acr_token():
    token = os.getenv("ACR_TOKEN")
    if not token:
        return JSONResponse(status_code=500, content={"error": "ACR_TOKEN no está configurado"})
    return {"message": "ACR_TOKEN está configurado"}
