# api-de-monitoreo
sistema para monitorear servicios

El archivo api.py contiene las apis de prueba para que el sistema de monitoreo pueda ejecutarse.

Apis creadas con FastApi (Doc https://fastapi.tiangolo.com/)
Instalacion de FastApi: $pip install "fastapi[all]"
Con el parametro "all" se instala uvicorn de igual manera (Doc https://www.uvicorn.org/)
Inicio de servidor: $uvicorn api:app

-------------------

Para iniciar el contenedor debes dentro de la carpeta grafana-dashboard y ejecutar $docker compose up -d
Para detener el contenedor $docker compose down

Esto detendrá y eliminará el contenedor, pero tus datos persistirán en el volumen grafana-storage.

----- INICIO DEL PROYECTO -----

- Iniciar Api's con fast api 
$ uvicorn api:app --reload

- Tener docker abierto con los contenedores INFLUX Y GRAFANA

- Iniciar el proyecto de monitoreo desde la carpeta /monitoreo/... con
 $ python monitoreo.py

 Para ver dashboard en grafana de manera local:
 http://localhost:3000

 Para ver la base de datos influx:
 http://localhost:8086


