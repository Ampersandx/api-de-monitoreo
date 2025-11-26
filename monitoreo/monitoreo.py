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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("REMITENTE")
SENDER_PASSWORD = os.environ.get("PASSWORD")
INFLUXDB_URL = os.environ.get("INFLUXDB_URL")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

MAX_SMTP_RETRIES = 3
RETRY_DELAY = 5  # segundos
CONFIG_FILE = "../monitoreo/config.json"  # Ruta al archivo de configuración


def cargar_configuracion_apis(archivo_config):
    """
    Carga la configuración de APIs desde archivo JSON.
    
    Args:
        archivo_config (str): Ruta al archivo JSON
        
    Returns:
        List[Dict]: Lista de APIs configuradas
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        json.JSONDecodeError: Si el JSON es inválido
    """
    try:
        with open(archivo_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.info(f"✓ Configuración de APIs cargada desde {archivo_config}")
            logger.info(f"  Total de APIs a monitorear: {len(config['apis'])}")
            
            # Log de cada API configurada
            for api in config['apis']:
                logger.info(f"  - {api['nombre']}: {api['url']} (timeout: {api.get('timeout', 10)}s, frecuencia: {api.get('frecuencia', 10)}s)")
            
            return config['apis']
    except FileNotFoundError:
        logger.error(f"❌ Archivo de configuración no encontrado: {archivo_config}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error al parsear JSON: {e}")
        raise


def main():
    """Función principal que inicia el ciclo de monitoreo."""
    
    # Cargar configuración de APIs desde archivo JSON
    try:
        data = cargar_configuracion_apis(CONFIG_FILE)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"No se pudo cargar la configuración. Abortando: {e}")
        return

    # Diccionario para rastrear si ya se envió alerta
    its_down = {api["nombre"]: False for api in data}

    # Intentar conectar a InfluxDB con reintentos
    influx_client = conectar_influxdb(retries=3)
    if not influx_client:
        logger.error("No se pudo conectar a InfluxDB. Abortando.")
        return

    influx_write_client = influx_client.write_api(write_options=SYNCHRONOUS)

    logger.info("="*80)
    logger.info("🚀 SISTEMA DE MONITOREO DE APIs INICIADO")
    logger.info("="*80)
    
    while True:
        try:
            apiDataExtractor(data, its_down, influx_write_client)
        except Exception as e:
            logger.error(f"❌ Error en ciclo de monitoreo: {e}")
        
        time.sleep(1)  # Pequeña pausa entre ciclos


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
            # Verificar conexión
            client.ping()
            logger.info("✓ Conexión a InfluxDB exitosa")
            return client
        except Exception as e:
            logger.warning(f"⚠️  Intento {intento + 1}/{retries} fallido: {e}")
            if intento < retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error("❌ No se pudo conectar a InfluxDB")
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
        
        # Consultar la API con su timeout específico
        status_api = consultar_api(url_api, nombre_api, timeout)
        
        logger.info(f"{nombre_api}: Status {status_api}")

        # Registrar en InfluxDB
        try:
            point = (
                influxdb_client.Point("http_status")
                .tag("api_nombre", nombre_api)
                .field("status", status_api)
                .time(datetime.utcnow())
            )
            influx_write_client.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        except Exception as e:
            logger.error(f"❌ Error al escribir en InfluxDB para {nombre_api}: {e}")

        # Gestionar alertas según estado
        gestionar_alerta(nombre_api, status_api, its_down, api)


def consultar_api(url, nombre_api, timeout):
    """
    Consulta una API y retorna el código de estado.
    
    Args:
        url (str): URL de la API
        nombre_api (str): Nombre de la API
        timeout (int): Tiempo máximo de espera en segundos
        
    Returns:
        int: Código de estado HTTP (200, 500, etc.)
    """
    try:
        response_api = requests.get(url, timeout=timeout)
        
        try:
            json_api = response_api.json()
            status_api = json_api.get("status", response_api.status_code)
        except ValueError:
            logger.warning(f"⚠️  Error al parsear JSON de {nombre_api}")
            status_api = response_api.status_code
            
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout en {nombre_api} (>{timeout}s)")
        status_api = 500
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Error de conexión con {nombre_api}")
        status_api = 500
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error en {nombre_api}: {e}")
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
            logger.info(f"✓ {nombre_api} SE RECUPERÓ (200)")
            its_down[nombre_api] = False

    else:  # Status != 200
        if not its_down[nombre_api]:
            logger.warning(f"🚨 {nombre_api} FALLÓ ({status_api}) - Enviando alerta...")
            send_mail_with_retry(SENDER_EMAIL, SENDER_PASSWORD, api, status_api)
            its_down[nombre_api] = True


def send_mail_with_retry(sender_email, sender_password, api, status_code, max_retries=MAX_SMTP_RETRIES):
    """
    Envía correo con reintentos automáticos.
    
    Args:
        sender_email (str): Correo del remitente
        sender_password (str): Contraseña del remitente
        api (Dict): Información de la API
        status_code (int): Código de estado HTTP
        max_retries (int): Número máximo de reintentos
    """
    
    recipient_list = api["email_destinatario"]
    subject = f"🚨 ALERTA: La API {api['nombre']} está caída"
    body_text = f"""
    Se ha detectado que la API {api['nombre']} no está disponible.
    
    URL: {api['url']}
    Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Status: {status_code}
    
    Por favor, toma las acciones necesarias para restaurar el servicio.
    """

    for intento in range(max_retries):
        try:
            send_mail(sender_email, sender_password, recipient_list, subject, body_text)
            logger.info(f"✓ Alerta enviada a {', '.join(recipient_list)}")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Intento {intento + 1}/{max_retries} fallido: {e}")
            if intento < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error(f"❌ No se pudo enviar alerta a {', '.join(recipient_list)} después de {max_retries} intentos")
    return False


def send_mail(sender_email, sender_password, recipient_list, subject, body_text):
    """
    Envía un correo electrónico.
    
    Args:
        sender_email (str): Correo del remitente
        sender_password (str): Contraseña del remitente
        recipient_list (List[str]): Lista de correos destinatarios
        subject (str): Asunto del correo
        body_text (str): Cuerpo del correo
        
    Raises:
        smtplib.SMTPException: Si falla el envío
    """
    
    smtp_server = SMTP_HOST
    smtp_port = SMTP_PORT

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_list)
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    server = None
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_list, msg.as_string())
        logger.info(f"✓ Correo enviado exitosamente")
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Error de autenticación SMTP. Revisa credenciales.")
        raise
    except smtplib.SMTPConnectError:
        logger.error("❌ Error al conectar con servidor SMTP.")
        raise
    except Exception as e:
        logger.error(f"❌ Error al enviar correo: {e}")
        raise
    finally:
        if server:
            server.quit()


if __name__ == "__main__":
    main()