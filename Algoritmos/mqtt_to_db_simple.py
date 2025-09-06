#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import signal
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional

import pymysql
from paho.mqtt.client import Client as MqttClient
from zoneinfo import ZoneInfo  # Python 3.9+

# ================== CONFIG ==================
DB_NAME = "Auralis"
DB_USER = "root"
DB_PASSWORD = "daniel586"
DB_HOST = "34.30.17.212"
DB_PORT = 3306

MQTT_HOST = "34.30.17.212"
MQTT_PORT = 8081          # WebSocket
MQTT_WS_PATH = "/"        # como en tu front

ONLY_ACTIVE = True

# Guardado en HORA LOCAL (naive)
LOCAL_TZ = ZoneInfo("America/Guayaquil")
# ============================================

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("mqtt_to_db_local_now")

SQL_SENSORS_ALL = """
SELECT st.name AS station_name, s.name AS sensor_name,
       s.id AS sensor_id, s.min_value, s.max_value, s.is_active AS sensor_active,
       st.is_active AS station_active
FROM sensorhub_sensor s
JOIN sensorhub_station st ON s.station_id = st.id
"""
if ONLY_ACTIVE:
    SQL_SENSORS_ALL += "WHERE s.is_active = 1 AND st.is_active = 1; "
else:
    SQL_SENSORS_ALL += ";"

# INSERT en measured_at (NO 'timestamp', NO 'is_valid')
SQL_INSERT = """
INSERT INTO measurements_measurement (sensor_id, measured_at, value)
VALUES (%s, %s, %s);
"""

class DB:
    def __init__(self):
        self.conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME, autocommit=True, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        # (estación.lower(), sensor.lower()) -> (sensor_id, min, max)
        self.map: Dict[Tuple[str, str], Tuple[int, Optional[float], Optional[float]]] = {}

    def load_sensors(self):
        with self.conn.cursor() as cur:
            cur.execute(SQL_SENSORS_ALL)
            rows = cur.fetchall()
        self.map.clear()
        for r in rows:
            key = (r["station_name"].strip().lower(), r["sensor_name"].strip().lower())
            self.map[key] = (
                int(r["sensor_id"]),
                None if r["min_value"] is None else float(r["min_value"]),
                None if r["max_value"] is None else float(r["max_value"]),
            )
        return rows

    def insert_measurement(self, sensor_id: int, ts_local_naive: datetime, value: float):
        # ts_local_naive DEBE ser naive (sin tz), ya en hora local
        if ts_local_naive.tzinfo is not None:
            ts_local_naive = ts_local_naive.astimezone(LOCAL_TZ).replace(tzinfo=None)
        with self.conn.cursor() as cur:
            cur.execute(SQL_INSERT, (sensor_id, ts_local_naive, float(value)))


def now_local_naive() -> datetime:
    """Devuelve ahora en hora local, naive (sin tzinfo)."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def parse_value(payload: str) -> Optional[float]:
    """
    Devuelve solo el valor numérico.
    Siempre usaremos 'now_local_naive()' como timestamp de inserción.
    Acepta:
      - "123.45"
      - JSON: {"value": 123.45, ...}
    """
    payload = (payload or "").strip()
    # JSON
    try:
        obj = json.loads(payload)
        if isinstance(obj, (int, float)):
            return float(obj)
        if isinstance(obj, dict) and "value" in obj:
            return float(obj["value"])
    except Exception:
        pass
    # número simple
    try:
        return float(payload.replace(",", "."))
    except Exception:
        return None


def main():
    db = DB()
    rows = db.load_sensors()
    if not rows:
        log.warning("No se encontraron estaciones/sensores en BD.")
    else:
        log.info("Sensores cargados: %d", len(rows))

    # topic normalizado -> (sensor_id, mn, mx)  (mn/mx por si luego validas)
    topic_to_sid: Dict[str, Tuple[int, Optional[float], Optional[float]]] = {}
    subs: list[str] = []

    # Normalizador de tópico para lookup
    def norm(t: str) -> str:
        return t.strip("/").lower()

    for r in rows:
        station = r["station_name"].strip()
        sensor  = r["sensor_name"].strip()
        sid, mn, mx = db.map[(station.lower(), sensor.lower())]

        # Suscribir a TODAS las variantes para evitar misses:
        variants = [
            f"{station}/{sensor}",
            f"{station}/{sensor}/",
            f"/{station}/{sensor}",
            f"/{station}/{sensor}/",
        ]
        for vt in variants:
            key = norm(vt)
            topic_to_sid[key] = (sid, mn, mx)
            subs.append(vt)

    client = MqttClient(client_id=f"ingestor_local_now_{os.getpid()}", transport="websockets")
    client.ws_set_options(path=MQTT_WS_PATH)

    def on_connect(cli, userdata, flags, rc):
        if rc == 0:
            # Suscribir todas las variantes (duplicados no dañan; el broker lo maneja)
            uniq = []
            seen = set()
            for t in subs:
                if t not in seen:
                    uniq.append(t)
                    seen.add(t)
            for t in uniq:
                cli.subscribe(t, qos=0)
            log.info("MQTT conectado. Suscritos %d tópicos.", len(uniq))
        else:
            log.error("Error conectando MQTT rc=%s", rc)

    def on_message(cli, userdata, msg):
        key = norm(msg.topic)
        info = topic_to_sid.get(key)
        if not info:
            return
        sensor_id, mn, mx = info
        try:
            payload = msg.payload.decode("utf-8", errors="ignore")
        except Exception:
            return

        value = parse_value(payload)
        if value is None:
            return

        ts_local = now_local_naive()   # <<< SIEMPRE AHORA LOCAL
        try:
            db.insert_measurement(sensor_id, ts_local, value)
        except Exception as e:
            log.exception("Error insertando medición (sensor_id=%s): %s", sensor_id, e)

    client.on_connect = on_connect
    client.on_message = on_message

    stop = {"flag": False}
    def _stop(*_):
        stop["flag"] = True
        try:
            client.disconnect()
        except Exception:
            pass
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    log.info("Conectando a ws://%s:%s%s ...", MQTT_HOST, MQTT_PORT, MQTT_WS_PATH)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    try:
        while not stop["flag"]:
            time.sleep(0.2)
    finally:
        client.loop_stop()
        log.info("Detenido.")
        try:
            db.conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
