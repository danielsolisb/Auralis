import time, threading, queue, logging, random, socket
from typing import Dict, Tuple, List
from datetime import datetime
import paho.mqtt.client as mqtt

from config import Settings
from db import DB
from models import Repo, SensorRow, PolicyRow
from evaluator import build_thresholds_for_sensor, StateTracker

def local_iso(dt: datetime) -> str:
    # Hora local del servidor, sin zona
    return dt.strftime("%Y-%m-%d %H:%M:%S")

class SubscriberService:
    def __init__(self, settings: Settings):
        self.s = settings
        self.db = DB(self.s.DB_HOST, self.s.DB_PORT, self.s.DB_USER, self.s.DB_PASSWORD, self.s.DB_NAME)
        self.repo = Repo(self.db)

        self.topic_to_sensor: Dict[str, SensorRow] = {}
        self.subscribed_topics: set[str] = set()
        self.policies: List[PolicyRow] = []

        self.measure_q: "queue.Queue[Tuple[int,str,float]]" = queue.Queue(maxsize=self.s.MAX_QUEUE)
        self.event_q: "queue.Queue[Tuple[str,int,str,float,str]]" = queue.Queue(maxsize=2000)

        self.tracker = StateTracker(
            persistence_default=self.s.EVAL_PERSISTENCE_DEFAULT,
            use_hysteresis=self.s.EVAL_USE_HYSTERESIS
        )
        self.last_value_by_sensor: Dict[int, Tuple[float, float]] = {}

        self.client = None
        self.stop_event = threading.Event()
        self.threads: List[threading.Thread] = []

    def _build_client(self):
        client_id = self.s.MQTT_CLIENT_ID or f"auralis-sub-{socket.gethostname()}-{random.randint(1000,9999)}"
        c = mqtt.Client(client_id=client_id, clean_session=True)
        if self.s.MQTT_TLS:
            c.tls_set()
        if self.s.MQTT_USERNAME:
            c.username_pw_set(self.s.MQTT_USERNAME, self.s.MQTT_PASSWORD or None)
        c.on_connect = self.on_connect
        c.on_message = self.on_message
        c.on_disconnect = self.on_disconnect
        return c

    def start(self):
        logging.info("Starting SubscriberService")
        self.client = self._build_client()
        self.client.connect_async(self.s.MQTT_HOST, self.s.MQTT_PORT, keepalive=self.s.MQTT_KEEPALIVE)
        self.client.loop_start()

        # Hilos no-daemon para join() en stop()
        t_writer = threading.Thread(target=self.writer_loop, name="writer", daemon=False)
        t_events = threading.Thread(target=self.event_writer_loop, name="event-writer", daemon=False)
        t_sync   = threading.Thread(target=self.sync_loop, name="sync", daemon=False)
        self.threads = [t_writer, t_events, t_sync]
        for t in self.threads:
            t.start()

    def stop(self):
        self.stop_event.set()

        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            try:
                self.client.loop_stop(force=True)
            except Exception:
                pass

        for t in self.threads:
            try:
                t.join(timeout=3.0)
            except Exception:
                pass

        logging.info("SubscriberService stopped.")

    # --- Loops ---
    def sync_loop(self):
        while not self.stop_event.is_set():
            try:
                sensors = self.repo.list_active_sensors()
                self._refresh_topics(sensors)
                self.policies = self.repo.list_active_policies()
            except Exception as e:
                logging.exception("sync_loop error: %s", e)
            self.stop_event.wait(self.s.SYNC_INTERVAL_SEC)

    def _refresh_topics(self, sensors: List[SensorRow]):
        new_map = {s.mqtt_topic: s for s in sensors if s.mqtt_topic}
        for topic, srow in new_map.items():
            if topic not in self.subscribed_topics and self.client:
                logging.info("Subscribe %s -> sensor %s(#%d)", topic, srow.name, srow.id)
                self.client.subscribe(topic, qos=self.s.MQTT_QOS)
                self.subscribed_topics.add(topic)
        for topic in list(self.subscribed_topics):
            if topic not in new_map and self.client:
                logging.info("Unsubscribe %s", topic)
                self.client.unsubscribe(topic)
                self.subscribed_topics.remove(topic)
                self.topic_to_sensor.pop(topic, None)
        self.topic_to_sensor = new_map

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT broker")
            for topic in self.topic_to_sensor.keys():
                client.subscribe(topic, qos=self.s.MQTT_QOS)
                self.subscribed_topics.add(topic)
        else:
            logging.error("MQTT connect failed rc=%s", rc)

    def on_disconnect(self, client, userdata, rc):
        logging.warning("MQTT disconnected rc=%s", rc)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        srow = self.topic_to_sensor.get(topic)
        if not srow:
            return
        payload = None
        try:
            payload = msg.payload.decode("utf-8").strip()
            value = float(payload)
        except Exception:
            logging.warning("Non-numeric payload on %s: %r", topic, payload)
            return

        now = datetime.now()              # hora local del servidor
        iso_ts = local_iso(now)

        # Encola medición
        try:
            self.measure_q.put_nowait((srow.id, iso_ts, value))
        except queue.Full:
            try:
                _ = self.measure_q.get_nowait()
                self.measure_q.put_nowait((srow.id, iso_ts, value))
            except Exception:
                logging.error("measure_q overflow; dropping sample")

        # Evalúa políticas
        try:
            by_scope = {}
            for p in self.policies:
                by_scope.setdefault(p.scope, []).append(p)
            th = build_thresholds_for_sensor(by_scope, srow)

            persistence = None
            for scope in ("SENSOR","STATION","SENSOR_TYPE","COMPANY","GLOBAL"):
                for p in by_scope.get(scope, []):
                    if (scope=="SENSOR" and p.sensor_id==srow.id) or \
                       (scope=="STATION" and p.station_id==srow.station_id) or \
                       (scope=="SENSOR_TYPE" and p.sensor_type_id==srow.sensor_type_id) or \
                       (scope=="COMPANY" and p.company_id==srow.company_id) or \
                       (scope=="GLOBAL"):
                        if p.persistence_seconds is not None:
                            persistence = p.persistence_seconds
                            break
                if persistence is not None:
                    break

            band = self.tracker.classify(srow, th, value, now, persistence)
            if band and band != "NORMAL":
                if band.startswith("ALERT"):
                    desc = f"Fuera de rango: {band.replace('_',' ').title()} (v={value:.3f})"
                    self.event_q.put_nowait(("ALARM", srow.id, iso_ts, value, desc))
                else:
                    desc = f"Advertencia: {band.replace('_',' ').title()} (v={value:.3f})"
                    self.event_q.put_nowait(("WARNING", srow.id, iso_ts, value, desc))
        except Exception as e:
            logging.exception("Error evaluating policy for topic %s: %s", topic, e)

    def writer_loop(self):
        buf: List[Tuple[int,str,float]] = []
        last_flush = time.time()
        while not self.stop_event.is_set():
            try:
                item = self.measure_q.get(timeout=0.2)
                buf.append(item)
            except queue.Empty:
                pass
            now = time.time()
            if buf and (len(buf) >= self.s.WRITE_BATCH_SIZE or (now - last_flush) * 1000.0 >= self.s.WRITE_FLUSH_MS):
                try:
                    self.repo.insert_measurements(buf)
                    logging.debug("Inserted %d measurements", len(buf))
                except Exception as e:
                    logging.exception("insert_measurements failed: %s", e)
                finally:
                    buf.clear()
                    last_flush = now

        # Flush final
        if buf:
            try:
                self.repo.insert_measurements(buf)
                logging.debug("Final flush: inserted %d measurements", len(buf))
            except Exception as e:
                logging.exception("final insert_measurements failed: %s", e)

    def event_writer_loop(self):
        while not self.stop_event.is_set():
            try:
                kind, sensor_id, iso_ts, value, desc = self.event_q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                if kind == "ALARM":
                    severity = "ALTA"
                    self.repo.create_alarm(sensor_id, iso_ts, value, severity, desc)
                else:
                    self.repo.create_warning(sensor_id, iso_ts, value, desc)
            except Exception as e:
                logging.exception("Insert event failed: %s", e)

        # Drenaje final
        while True:
            try:
                kind, sensor_id, iso_ts, value, desc = self.event_q.get_nowait()
            except queue.Empty:
                break
            try:
                if kind == "ALARM":
                    severity = "ALTA"
                    self.repo.create_alarm(sensor_id, iso_ts, value, severity, desc)
                else:
                    self.repo.create_warning(sensor_id, iso_ts, value, desc)
            except Exception as e:
                logging.exception("Final insert event failed: %s", e)
