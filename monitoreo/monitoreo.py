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

load_dotenv()

destinatario = [] # 'vicctorxgames@email.com'  # ARREGLO PARA TENER MAS DE 1 CORREO
asunto = "Alerta: Problema en el sistema"
cuerpo = "Se ha detectado un problema en el sistema. Por favor, revisa los logs."
sender = os.environ.get("REMITENTE")
password = os.environ.get("PASSWORD")
smtp_host = 'smtp.gmail.com'
smtp_puerto = 587


print("remitente del .env: ", sender)
print("contraseña del .env: ", password)


def main():

    data = [{"nombre": "FLY", "url": "http://127.0.0.1:8000/api1", "email_destinatario": ["vicctorxgames@gmail.com"]},
            {"nombre": "FOR", "url": "http://127.0.0.1:8000/api2",
             "email_destinatario": ["vicctox@gmail.com", "vicctorxgames@gmail.com"]},
            {"nombre": "FUN", "url": "http://127.0.0.1:8000/api3", "email_destinatario": ["vicctorx@gmail.com"]}]

    its_down = {api["nombre"]: False for api in data}

    influx_client = influxdb_client.InfluxDBClient(
    url= os.environ.get("INFLUXDB_URL"),
    token= os.environ.get("INFLUXDB_TOKEN"),
    org= os.environ.get("INFLUXDB_ORG")
    )

    influx_write_client = influx_client.write_api(write_options=SYNCHRONOUS)

    while True:
        print("*********************NUEVA EJECUCION*************************")
        apiDataExtractor(data, its_down, influx_write_client)
        time.sleep(10)
        print("**********************FIN EJECUCION**************************")


def apiDataExtractor(data, its_down, influx_write_client):

    for api in data:
        name = api["nombre"]
        try:
            response_api = requests.get(api["url"])
            json_api = response_api.json()
            status_api = json_api["status"]
        except requests.exceptions.ConnectionError:
            print("No existe conexion con la API")
            status_api = 500

        print(f"El status de la {name} es : {status_api}")

        point = (
            influxdb_client.Point("http_status")
            .tag("api_nombre", name)
            .field("status", status_api)
            .time(datetime.utcnow())
        )

        influx_write_client.write(bucket= os.environ.get("INFLUXDB_BUCKET"), org= os.environ.get("INFLUXDB_ORG"), record=point)
        print(f"el punto de insercion es {point}")

        if status_api == 200:
            print(f"entre al if de los 200: {name} {status_api}")
            if its_down[name]:
                print(f"Estado de la api {api['nombre']} : {its_down[name]} en el if 200")
                its_down[name] = False
                print(f"Cambiando el estado de la api {api['nombre']} al: {its_down[name]}")

        if status_api == 500:
            print(f"entre al if de los 500, la api fue {api['nombre']}, con status {status_api}, correos a enviar notificacion {api['email_destinatario']}")
            # evaluar si fue enviado el correo previamente, si fue enviado no entra al IF. Si no ha sido enviado debe entrar a enviar.
            print(f"Estado del envio de correo: {its_down[name]}, en la api: {api['nombre']}")
            if not its_down[name]:
                print(f"Entre al if porque la wea es FALSE =? {its_down[name]} en la api: {api['nombre']}")
#                sendMail(sender, password, api, asunto, cuerpo)
                its_down[name] = True
                print(f"Estado del correo enviado {its_down[name]} en la api: {api['nombre']}")

#Funcion que realiza el envio de correo
#Entradas < 
def sendMail(sender_email, sender_password, api, subject, body_text):
    """
    Envía un correo electrónico a una lista de destinatarios usando SMTP.

    Args:
        sender_email (str): La dirección de correo electrónico del remitente.
        sender_password (str): La contraseña del remitente (o token de aplicación/clave si usas Gmail, por ejemplo).
        recipient_list (list): Una lista de cadenas, donde cada cadena es una dirección de correo electrónico de un destinatario.
        subject (str): El asunto del correo electrónico.
        body_text (str): El cuerpo del correo electrónico (texto plano).
    """

    recipient_list = api["email_destinatario"]
    print("recipient_list es: ", recipient_list)
    # Configuración del servidor SMTP
    smtp_server = "smtp.gmail.com"
    smtp_port = 587  # Puerto para TLS/STARTTLS

    # Crea un objeto mensaje multipart
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['Subject'] = subject

    # Importante: para el encabezado 'To', unir la lista de destinatarios con comas
    msg['To'] = ", ".join(recipient_list)

    # Adjunta el cuerpo del correo como texto plano
    msg.attach(MIMEText(body_text, 'plain'))

    try:
        # Inicia la conexión con el servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(0)  # Establece 1 para ver el log de la comunicación SMTP
        server.starttls()  # Habilita el cifrado TLS
        server.login(sender_email, sender_password)

        # Envía el correo. La función sendmail() espera una lista de destinatarios.
        # Es importante notar que el segundo argumento de sendmail es la lista de
        # destinatarios reales para el "envelope" del correo, mientras que msg['To']
        # es solo para el encabezado visible.
        server.sendmail(sender_email, recipient_list, msg.as_string())

        print(f"Correo enviado exitosamente a: {', '.join(recipient_list)}")

    except smtplib.SMTPAuthenticationError as e:
        print(f"Error de autenticación SMTP: {e}. Revisa tu usuario y contraseña, o las configuraciones de seguridad (ej. acceso de aplicaciones menos seguras en Gmail).")
    except smtplib.SMTPConnectError as e:
        print(f"Error al conectar con el servidor SMTP: {e}. Revisa la dirección del servidor y el puerto.")
    except smtplib.SMTPException as e:
        print(f"Error SMTP general: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
    finally:
        if 'server' in locals() and server:
            server.quit() # Cierra la conexión SMTP


if __name__ == "__main__":
    main()


