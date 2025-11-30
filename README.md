# api-de-monitoreo

Sistema de monitoreo automático para servicios y APIs.

##  Descripción

Sistema de monitoreo en tiempo real que:
-  Consulta periódicamente APIs configuradas
-  Almacena datos históricos en InfluxDB
-  Visualiza métricas en dashboards de Grafana
-  Envía alertas por correo ante fallos
-  Se ejecuta completamente contenerizado

---

##  Inicio Rápido

### Requisitos Previos

- Docker Engine
- Docker Compose
- Git

### 1. Clonar o descargar el proyecto

```bash
cd api-de-monitoreo
```

### 2. Configurar el archivo `.env`

Asegúrate de que contiene:

```env
REMITENTE=tu_email@gmail.com
PASSWORD=tu_contraseña_o_token
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=_ADZL7eFFOaugIzIqoDzXuL5_TkstXUrwmIdvsit9Xi_yHg1EDeUFz2d1QPtbGNkFCVnkHr679MwcdGYcxZVaw==
INFLUXDB_ORG=MiOrganizacion
INFLUXDB_BUCKET=estados_programa
USERGRAFANA=admin
PASSGRAFANA=Claveparalatesis.
```

### 3. Configurar APIs a monitorear

Edita el archivo `monitoreo/config.json`:

```json
{
  "ciclo_monitoreo": 10,
  "apis": [
    {
      "nombre": "NombreAPI1",
      "url": "http://api:8000/api1",
      "email_destinatario": ["correo@example.com"],
      "timeout": 10,
      "frecuencia": 10
    },
    {
      "nombre": "NombreAPI2",
      "url": "http://api:8000/api2",
      "email_destinatario": ["correo@example.com"],
      "timeout": 10,
      "frecuencia": 10
    },
    {
      "nombre": "NombreAPI3",
      "url": "http://api:8000/api3",
      "email_destinatario": ["correo@example.com"],
      "timeout": 10,
      "frecuencia": 10
    }
  ]
}
```

### 4. Levantar los contenedores

```bash
docker-compose up -d
```

Esto iniciará automáticamente:
-  InfluxDB (puerto 8086)
-  Grafana (puerto 3000)
-  APIs de prueba (puerto 8000)
-  Sistema de monitoreo

### 5. Verificar estado

```bash
# Ver contenedores corriendo
docker-compose ps

# Ver logs del monitoreo
docker logs api-monitoreo -f

# Ver logs de InfluxDB
docker logs influxdb -f

# Ver logs de Grafana
docker logs grafana -f
```

---

##  Acceso a Servicios

Una vez levantados los contenedores:

| Servicio | URL | Usuario/Contraseña |
|---|---|---|
| **Grafana** | http://localhost:3000 | admin / Claveparalatesis. |
| **InfluxDB** | http://localhost:8086 | admin_influx / admin_influx |
| **APIs de prueba** | http://localhost:8000/docs | - |

---

##  Usar Grafana

1. Accede a http://localhost:3000
2. Inicia sesión con las credenciales por defecto
3. El datasource de InfluxDB está preconfigurado
4. Crea dashboards para visualizar el estado de tus APIs

---

##  Detener los Contenedores

```bash
# Detener sin eliminar volúmenes (datos persisten)
docker-compose stop

# Reiniciar
docker-compose start

# Detener y eliminar (los volúmenes persisten)
docker-compose down

# Detener, eliminar TODO incluyendo volúmenes (CUIDADO: pierdes datos)
docker-compose down -v
```

---

##  Estructura del Proyecto

```
api-de-monitoreo/
├── api.py                          # APIs de prueba con FastAPI
├── Dockerfile                       # Para contenedor de APIs
├── requirements.txt                 # Dependencias de FastAPI
├── docker-compose.yml               # Orquestación de contenedores
├── .env                             # Variables de entorno
├── .gitignore
├── README.md
├── monitoreo/
│   ├── monitoreo.py                # Sistema de monitoreo (main)
│   ├── Dockerfile                  # Para contenedor de monitoreo
│   ├── requirements.txt             # Dependencias de Python
│   ├── config.json                 # Configuración de APIs a monitorear
└── grafana-provisioning/
    └── datasources/
        └── influxdb.yml            # Datasource preconfigurado
```

---

##  Configuración Avanzada

### Cambiar tiempos de monitoreo

En `monitoreo/config.json`, ajusta `timeout` y `frecuencia`:

```json
{
  "nombre": "API_Critica",
  "url": "http://api:8000/critical",
  "email_destinatario": ["admin@example.com"],
  "timeout": 5,        // Falla si no responde en 5s
  "frecuencia": 5      // Consultar cada 5 segundos
}
```

### Cambiar el tiempo de ciclo del monitoreo

```json
{
  "ciclo_monitoreo": 10, // 10 segundos por defecto, ciclo de monitoreo.
}
```

### Agregar más destinatarios de alertas

```json
"email_destinatario": [
  "admin1@example.com",
  "admin2@example.com",
  "operaciones@example.com"
]
```

### Cambiar credenciales de Grafana

Edita el `docker-compose.yml`:

```yaml
environment:
  - GF_SECURITY_ADMIN_USER=tu_usuario
  - GF_SECURITY_ADMIN_PASSWORD=tu_contraseña
```

---

##  Troubleshooting

### Error: "Cannot connect to InfluxDB"
- Verifica que InfluxDB esté corriendo: `docker logs influxdb`
- Espera unos segundos a que InfluxDB termine de iniciarse
- Verifica que `INFLUXDB_URL=http://influxdb:8086` en `.env`

### Error: "SMTP authentication failed"
- Revisa las credenciales en `.env`
- Para Gmail, usa contraseña de aplicación, no la contraseña regular
- Asegúrate de que REMITENTE y PASSWORD sean correctos

### Error: "config.json not found"
- Verifica que `monitoreo/config.json` exista y sea válido
- El Dockerfile debe copiar este archivo: `COPY config.json .`

### Logs no aparecen
```bash
docker logs api-monitoreo --tail=100
```

---

##  Notas Importantes

- Los datos de InfluxDB y Grafana se guardan en volúmenes Docker (persistentes)
- El monitoreo se reinicia automáticamente si falla
- Las APIs de prueba responden con `{"status": 200}`
- Los errores se registran en los logs de cada contenedor

---

##  Contacto

Para preguntas o reportes de problemas, consulta la documentación del proyecto.