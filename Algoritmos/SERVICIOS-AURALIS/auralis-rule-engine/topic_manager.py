import paho.mqtt.client as mqtt
import redis
import time
import json
import logging
from threading import Thread, Event
from . import config, db

log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - [TopicManager] - %(message)s')

class TopicManager:
    def __init__(self):
        self.mqtt_client = mqtt.Client(client_id=config.MQTT_CLIENT_ID_MANAGER)
        self.redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)
        self.topic_map = {}
        self.stop_event = Event()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Conectado exitosamente al broker MQTT.")
            self.sync_topics()
        else:
            logging.error(f"Fallo al conectar al broker MQTT, código de retorno: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logging.debug(f"Mensaje recibido en {topic} -> {payload}")
            sensor_id = self.topic_map.get(topic)
            if sensor_id:
                message_data = {
                    'sensor_id': sensor_id,
                    'value': float(payload),
                    'topic': topic,
                    'timestamp': time.time()
                }
                self.redis_client.lpush(config.REDIS_QUEUE_NAME, json.dumps(message_data))
            else:
                logging.warning(f"Mensaje recibido en un tópico no mapeado: {topic}")
        except (ValueError, UnicodeDecodeError) as e:
            logging.error(f"Error al procesar mensaje de {msg.topic}: {e}")
        except Exception as e:
            logging.error(f"Error inesperado en on_message: {e}")

    def sync_topics(self):
        logging.info("Iniciando sincronización de tópicos...")
        connection = db.get_db_connection()
        if not connection:
            logging.error("No se pudo conectar a la base de datos para sincronizar tópicos.")
            return
        try:
            with connection.cursor() as cursor:
                query = "SELECT id, mqtt_topic FROM sensorhub_sensor WHERE mqtt_topic IS NOT NULL AND mqtt_topic != '' AND is_active = TRUE"
                cursor.execute(query)
                results = cursor.fetchall()
        finally:
            connection.close()
        new_topic_map = {row['mqtt_topic']: row['id'] for row in results}
        current_topics = set(self.topic_map.keys())
        new_topics = set(new_topic_map.keys())
        topics_to_subscribe = new_topics - current_topics
        topics_to_unsubscribe = current_topics - new_topics
        if topics_to_subscribe:
            subscription_list = [(topic, 0) for topic in topics_to_subscribe]
            logging.info(f"Suscribiendo a {len(subscription_list)} nuevos tópicos.")
            self.mqtt_client.subscribe(subscription_list)
        if topics_to_unsubscribe:
            logging.info(f"Desuscribiendo de {len(topics_to_unsubscribe)} tópicos obsoletos.")
            self.mqtt_client.unsubscribe(list(topics_to_unsubscribe))
        self.topic_map = new_topic_map
        logging.info(f"Sincronización completada. {len(self.topic_map)} tópicos activos.")

    def sync_loop(self):
        while not self.stop_event.is_set():
            self.sync_topics()
            self.stop_event.wait(config.SYNC_INTERVAL_TOPICS)

    def run(self):
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        if config.MQTT_USERNAME and config.MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        try:
            self.mqtt_client.connect(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT, config.MQTT_KEEPALIVE)
        except Exception as e:
            logging.error(f"No se pudo conectar al broker MQTT: {e}")
            return
        sync_thread = Thread(target=self.sync_loop)
        sync_thread.daemon = True
        sync_thread.start()
        self.mqtt_client.loop_forever()

if __name__ == '__main__':
    manager = TopicManager()
    manager.run()