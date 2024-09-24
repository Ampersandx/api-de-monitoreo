from fastapi import FastAPI
from typing import Union

app = FastAPI()


@app.get("/api1")
def internal_status():
    return {"status": "200"}
