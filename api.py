from fastapi import FastAPI
import random
import time

app = FastAPI()


# Variables de caché
cache_status = None
cache_timestamp = 0
cache_duration = 60  # 5 minutos en segundos = 300


def get_status_code():
    global cache_status, cache_timestamp

    current_time = time.time()

    if cache_status == 500 and (current_time - cache_timestamp) < cache_duration:
        return 500

    if random.random() < 0.95:
        return 200
    else:
        cache_status = 500
        cache_timestamp = current_time
        return 500


@app.get("/Unab APP")
async def internal_status_api1():
    status_code = get_status_code()
    return {"status": (status_code), "Nombre": "Pepito"}


@app.get("/Intranet")
async def internal_status_api2():
    status_code = 200
    return {"status": (status_code)}


@app.get("/Portal de pagos")
async def internal_status_api3():
    status_code = 200
    return {"status": (status_code)}

