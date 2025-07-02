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

admin
Claveparalatesis.
