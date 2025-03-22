# auralis/mqtt_subscriber.py

import paho.mqtt.client as mqtt
from .config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD
from .tasks import process_measurement
from sqlalchemy import text
from .db import get_db_session

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Conectado con código {rc}")
    # Suscríbete a todos los tópicos o a uno específico
    client.subscribe("#")  # Suscribe a todos los tópicos
    print("[MQTT] Suscrito al tópico: #")

def on_message(client, userdata, msg):
    """
    Callback que se llama cuando llega un mensaje MQTT.
    """
    topic = msg.topic
    payload = msg.payload.decode('utf-8')  # Asumiendo que es texto
    print(f"[MQTT] Mensaje recibido en {topic} -> {payload}")

    # Convertir el payload a float
    try:
        value = float(payload)
    except ValueError:
        print(f"[MQTT] No se pudo convertir a float: {payload}")
        return

    # Parsear topic para extraer (estación, sensor)
    # Ejemplo: "Estacion1/SensorTemp"
    parts = topic.split('/')
    if len(parts) < 2:
        print("[MQTT] Tópico con formato inválido, se necesitan al menos 2 partes")
        return
    
    station_name = parts[0]
    sensor_name = parts[1]

    # Mapear (station_name, sensor_name) a sensor_id
    sensor_id = get_sensor_id(station_name, sensor_name)
    if not sensor_id:
        print(f"[MQTT] No se encontró sensor_id para {station_name}/{sensor_name}")
        return

    # Llamar a la tarea Celery
    process_measurement.delay(sensor_id, value)
    print(f"[MQTT] Tarea Celery encolada -> sensor_id={sensor_id}, value={value}")

def get_sensor_id(station_name, sensor_name):
    """
    Obtiene el sensor_id a partir del nombre de la estación y el nombre del sensor.
    Se asume que:
      - La tabla sensorhub_station tiene la columna 'name'.
      - La tabla sensorhub_sensor tiene la columna 'name' y la columna 'station_id' que
        se relaciona con sensorhub_station.id.
    """
    sensor_id = None
    # Se abre una sesión a la base de datos
    with next(get_db_session()) as db:
        query = text("""
            SELECT s.id
            FROM sensorhub_sensor s
            JOIN sensorhub_station st ON s.station_id = st.id
            WHERE st.name = :station_name AND s.name = :sensor_name
            LIMIT 1
        """)
        result = db.execute(query, {"station_name": station_name, "sensor_name": sensor_name}).fetchone()
        if result:
            sensor_id = result[0]
    return sensor_id

#def get_sensor_id(station_name, sensor_name):
#    """
#    Función MOCK de ejemplo.
#    Deberías consultar tu tabla station y sensor para obtener el ID real.
#    """
#    # Por ejemplo:
#    # SELECT s.id 
#    # FROM sensorhub_sensor s
#    # JOIN sensorhub_station st ON s.station_id = st.id
#    # WHERE st.name = station_name AND s.name = sensor_name
#    #
#    # Aquí devolvemos 1 para simplificar.
#    return 1

def run_mqtt_subscriber():
    client = mqtt.Client()
    
    # Si tu broker no tiene usuario/contraseña, no hace falta llamar username_pw_set
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_forever()
