# /opt/auralis-subscriber/mqtt_worker.py

import time, threading, queue, logging
from typing import Dict, Tuple, List
from datetime import datetime
import paho.mqtt.client as mqtt
import pytz

from config import Settings
from db import DB
from models import Repo, SensorRow

def local_iso_now(tz: pytz.timezone) -> str:
    """Retorna el timestamp actual localizado en formato ISO para la BD."""
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

class SubscriberService:
    def __init__(self, settings: Settings):
        self.s = settings
        self.db = DB(self.s.DB_HOST, self.s.DB_PORT, self.s.DB_USER, self.s.DB_PASSWORD, self.s.DB_NAME)
        self.repo = Repo(self.db)

        self.topic_to_sensor: Dict[str, SensorRow] = {}
        self.subscribed_topics: set[str] = set()

        self.measure_q: "queue.Queue[Tuple[int, str, float]]" = queue.Queue(maxsize=self.s.MAX_QUEUE)
        self.stop_event = threading.Event()
        
        try:
            self.local_tz = pytz.timezone(self.s.TZ_NAME)
            logging.info(f"Zona horaria configurada para mediciones: {self.s.TZ_NAME}")
        except pytz.UnknownTimeZoneError:
            logging.error(f"Zona horaria desconocida: '{self.s.TZ_NAME}'. Usando UTC por defecto.")
            self.local_tz = pytz.utc
        
        self.mqtt_client = mqtt.Client(client_id=self.s.MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

    def start(self):
        # Iniciar hilos de trabajo
        self.writer_thread = threading.Thread(target=self.writer_loop, name="WriterThread")
        self.sync_thread = threading.Thread(target=self.sync_loop, name="SyncThread")

        self.writer_thread.start()
        self.sync_thread.start()

        # Conectar al broker MQTT
        if self.s.MQTT_USERNAME:
            self.mqtt_client.username_pw_set(self.s.MQTT_USERNAME, self.s.MQTT_PASSWORD)
        
        try:
            self.mqtt_client.connect(self.s.MQTT_HOST, self.s.MQTT_PORT, self.s.MQTT_KEEPALIVE)
            self.mqtt_client.loop_start()
        except Exception as e:
            logging.error("Fallo en la conexión MQTT inicial: %s", e)
            self.stop()

    def stop(self):
        self.stop_event.set()
        logging.info("Deteniendo servicios...")
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        self.writer_thread.join(timeout=2)
        self.sync_thread.join(timeout=2)
        self.db.close_thread()
        logging.info("Servicios detenidos.")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Conectado al broker MQTT.")
            self.sync_mqtt_subscriptions()
        else:
            logging.error("Fallo al conectar a MQTT, código: %s", rc)

    def on_message(self, client, userdata, msg):
        try:
            sensor = self.topic_to_sensor.get(msg.topic)
            if not sensor:
                return
            
            value = float(msg.payload.decode())
            iso_ts = local_iso_now(self.local_tz)

            # Poner la medición en la cola para el writer
            self.measure_q.put((sensor.id, iso_ts, value))

        except (ValueError, UnicodeDecodeError) as e:
            logging.warning("No se pudo decodificar el mensaje de %s: %s", msg.topic, e)
        except queue.Full:
            logging.error("Cola de mediciones llena. Descartando dato de %s", msg.topic)

    def sync_mqtt_subscriptions(self):
        try:
            sensors = self.repo.list_active_sensors()
            self.topic_to_sensor = {s.mqtt_topic: s for s in sensors if s.mqtt_topic}
            
            new_topics = set(self.topic_to_sensor.keys())
            
            to_subscribe = new_topics - self.subscribed_topics
            to_unsubscribe = self.subscribed_topics - new_topics

            if to_subscribe:
                sub_list = [(topic, self.s.MQTT_QOS) for topic in to_subscribe]
                self.mqtt_client.subscribe(sub_list)
                logging.info("Suscrito a %d nuevos tópicos.", len(to_subscribe))
            
            if to_unsubscribe:
                self.mqtt_client.unsubscribe(list(to_unsubscribe))
                logging.info("Desuscrito de %d tópicos obsoletos.", len(to_unsubscribe))

            self.subscribed_topics = new_topics
        except Exception as e:
            logging.exception("Fallo al sincronizar suscripciones MQTT: %s", e)

    def sync_loop(self):
        while not self.stop_event.is_set():
            logging.info("Iniciando ciclo de sincronización...")
            self.sync_mqtt_subscriptions()
            self.stop_event.wait(self.s.SYNC_INTERVAL_SEC)

    def writer_loop(self):
        """
        Toma mediciones de la cola y las escribe en la base de datos en lotes.
        """
        buf: List[Tuple[int, str, float]] = []
        last_flush = time.monotonic()

        while not self.stop_event.is_set():
            try:
                item = self.measure_q.get(timeout=0.1)
                buf.append(item)
            except queue.Empty:
                pass # Continuar para revisar si se debe hacer flush

            should_flush = (
                (len(buf) >= self.s.WRITE_BATCH_SIZE) or
                (buf and (time.monotonic() - last_flush) * 1000 >= self.s.WRITE_FLUSH_MS)
            )

            if should_flush:
                try:
                    self.repo.insert_measurements(buf)
                    logging.info("Lote de %d mediciones guardado en la BD.", len(buf))
                    buf.clear()
                    last_flush = time.monotonic()
                except Exception as e:
                    logging.exception("Fallo al escribir el lote de mediciones: %s", e)
        
        # Drenaje final de la cola al detener
        if buf:
            try:
                self.repo.insert_measurements(buf)
                logging.debug("Drenaje final: insertadas %d mediciones.", len(buf))
            except Exception as e:
                logging.exception("Fallo en el drenaje final de mediciones: %s", e)