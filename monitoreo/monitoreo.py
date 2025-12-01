import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import time
from dotenv import load_dotenv
import os
import logging
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("REMITENTE")
SENDER_PASSWORD = os.environ.get("PASSWORD")
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

MAX_SMTP_RETRIES = 3
RETRY_DELAY = 5
CONFIG_FILE = "config.json"
CICLO_MONITOREO = 10


def cargar_configuracion_apis(archivo_config):
    """
    Carga la configuración de APIs desde archivo JSON.
    También carga el ciclo de monitoreo si está definido.
    
    Args:
        archivo_config (str): Ruta al archivo JSON
        
    Returns:
        List[Dict]: Lista de APIs a monitorear
    """
    global CICLO_MONITOREO
    
    try:
        with open(archivo_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info("Configuración cargada desde %s", archivo_config)
            
            # Ciclo por defecto de 10 segundos
            if "ciclo_monitoreo" in config:
                CICLO_MONITOREO = int(config["ciclo_monitoreo"])
                logger.info("Ciclo de monitoreo: %d segundos", CICLO_MONITOREO)
            else:
                logger.info("Ciclo de monitoreo: %d segundos (default)", CICLO_MONITOREO)
            
            logger.info("Total de APIs a monitorear: %d", len(config['apis']))
            
            for api in config['apis']:
                logger.info("  - %s: %s (timeout: %ds)", 
                           api['nombre'], 
                           api['url'], 
                           api.get('timeout', 10))
            
            return config['apis']
            
    except FileNotFoundError:
        logger.error("Archivo de configuración no encontrado: %s", archivo_config)
        raise
    except json.JSONDecodeError as e:
        logger.error("Error al parsear JSON: %s", e)
        raise
    except Exception as e:
        logger.error("Error inesperado al cargar configuración: %s", e)
        raise


def main():
    """Función principal que inicia el ciclo de monitoreo."""
    
    try:
        data = cargar_configuracion_apis(CONFIG_FILE)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("No se pudo cargar la configuración. Abortando: %s", e)
        return

    its_down = {api["nombre"]: False for api in data}

    influx_client = conectar_influxdb(retries=3)
    if not influx_client:
        logger.error("No se pudo conectar a InfluxDB. Abortando.")
        return

    influx_write_client = influx_client.write_api(write_options=SYNCHRONOUS)

    logger.info("=" * 60)
    logger.info("SISTEMA DE MONITOREO DE APIs INICIADO")
    logger.info("Ciclo: %ds | APIs: %d | Hora: %s", 
               CICLO_MONITOREO, 
               len(data), 
               datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("=" * 60)
    
    while True:
        try:
            apiDataExtractor(data, its_down, influx_write_client)
        except Exception as e:
            logger.error("Error en ciclo de monitoreo: %s", e)
        
        time.sleep(CICLO_MONITOREO)


def conectar_influxdb(retries=3):
    """
    Intenta conectar a InfluxDB con reintentos.
    
    Args:
        retries (int): Número de intentos de conexión
        
    Returns:
        InfluxDBClient: Cliente conectado o None si falla
    """
    for intento in range(retries):
        try:
            client = influxdb_client.InfluxDBClient(
                url=INFLUXDB_URL,
                token=INFLUXDB_TOKEN,
                org=INFLUXDB_ORG
            )
            client.ping()
            logger.info("Conexión a InfluxDB exitosa (%s)", INFLUXDB_URL)
            return client
        except Exception as e:
            logger.warning("Intento %d/%d fallido: %s", intento + 1, retries, e)
            if intento < retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error("No se pudo conectar a InfluxDB")
    return None


def apiDataExtractor(data, its_down, influx_write_client):
    """
    Extrae datos de las APIs y gestiona alertas.
    
    Args:
        data (List[Dict]): Lista de APIs a monitorear
        its_down (Dict): Estado de APIs caídas
        influx_write_client: Cliente de escritura en InfluxDB
    """
    
    for api in data:
        nombre_api = api["nombre"]
        url_api = api["url"]
        timeout = api.get("timeout", 10)
        
        status_api = consultar_api(url_api, nombre_api, timeout)
        
        logger.info("%s: Status %d", nombre_api, status_api)

        try:
            point = (
                influxdb_client.Point("http_status")
                .tag("api_nombre", nombre_api)
                .field("status", status_api)
                .time(datetime.utcnow())
            )
            influx_write_client.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        except Exception as e:
            logger.error("Error al escribir en InfluxDB para %s: %s", nombre_api, e)

        gestionar_alerta(nombre_api, status_api, its_down, api)


def consultar_api(url, nombre_api, timeout):
    """
    Consulta una API y retorna el código de estado.
    
    Args:
        url (str): URL de la API
        nombre_api (str): Nombre de la API
        timeout (int): Tiempo máximo de espera en segundos
        
    Returns:
        int: Código de estado HTTP
    """
    try:
        response_api = requests.get(url, timeout=timeout)
        
        try:
            json_api = response_api.json()
            status_api = json_api.get("status", response_api.status_code)
        except ValueError:
            logger.warning("Alerta al parsear JSON de %s", nombre_api)
            status_api = response_api.status_code
            
    except requests.exceptions.Timeout:
        logger.error("Timeout en %s (>%ds)", nombre_api, timeout)
        status_api = 500
    except requests.exceptions.ConnectionError:
        logger.error("Error de conexión con %s", nombre_api)
        status_api = 500
    except requests.exceptions.RequestException as e:
        logger.error("Error en %s: %s", nombre_api, e)
        status_api = 500

    return status_api


def gestionar_alerta(nombre_api, status_api, its_down, api):
    """
    Gestiona el envío de alertas según el estado de la API.
    
    Args:
        nombre_api (str): Nombre de la API
        status_api (int): Código de estado
        its_down (Dict): Registro de APIs caídas
        api (Dict): Información de la API
    """
    
    if status_api == 200:
        if its_down[nombre_api]:
            logger.info("%s SE RECUPERÓ (200)", nombre_api)
            its_down[nombre_api] = False

    else:
        if not its_down[nombre_api]:
            logger.warning("%s FALLÓ (%d) - Enviando alerta...", nombre_api, status_api)
            send_mail_with_retry(SENDER_EMAIL, SENDER_PASSWORD, api, status_api)
            its_down[nombre_api] = True


def send_mail_with_retry(sender_email, sender_password, api, status_code, max_retries=MAX_SMTP_RETRIES):
    """
    Envía correo con reintentos automáticos.
    """
    
    recipient_list = api["email_destinatario"]
    subject = "ALERTA: La API %s está caída" % api['nombre']
    body_text = """
    Se ha detectado que la API %s no está disponible.
    
    URL: %s
    Hora: %s
    Status: %d
    
    Por favor, toma las acciones necesarias para restaurar el servicio.
    """ % (api['nombre'], api['url'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), status_code)

    for intento in range(max_retries):
        try:
            send_mail(sender_email, sender_password, recipient_list, subject, body_text)
            logger.info("Alerta enviada a %s", ', '.join(recipient_list))
            return True
        except Exception as e:
            logger.warning("Intento %d/%d fallido: %s", intento + 1, max_retries, e)
            if intento < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error("No se pudo enviar alerta después de %d intentos", max_retries)
    return False


def send_mail(sender_email, sender_password, recipient_list, subject, body_text):
    """
    Envia un correo electrónico.
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_list)
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    server = None
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_list, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        logger.error("Error de autenticación SMTP")
        raise
    except smtplib.SMTPConnectError:
        logger.error("Error de conexión SMTP")
        raise
    except Exception as e:
        logger.error("Error al enviar correo: %s", e)
        raise
    finally:
        if server:
            server.quit()


if __name__ == "__main__":
    main()