#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import signal
import logging
from datetime import datetime, timezone as dt_timezone
from typing import Dict, Tuple, Optional

import pymysql
from paho.mqtt.client import Client as MqttClient
from dateutil.parser import isoparse
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
log = logging.getLogger("mqtt_to_db_local")

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

# OJO: medimos en 'timestamp' y SIN is_valid (lo eliminaste)
SQL_INSERT = """
INSERT INTO measurements_measurement (sensor_id, `timestamp`, value)
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

def to_local_naive_from_any(dt_any: datetime | None) -> datetime:
    """
    Convierte un datetime cualquiera (naive/aware, utc/local) a LOCAL naive.
    Si viene None, usa ahora local.
    """
    if dt_any is None:
        return now_local_naive()
    if dt_any.tzinfo is None:
        # asumimos que un dt naive del payload es LOCAL (decisión de negocio)
        return dt_any
    # si vino aware, lo pasamos a local y lo dejamos naive
    return dt_any.astimezone(LOCAL_TZ).replace(tzinfo=None)

def parse_payload(payload: str):
    """
    Devuelve (value: float|None, ts_local_naive: datetime).
    Acepta:
      - número simple: "123.45"  -> ahora local
      - JSON: {"value": 123.45, "ts": "2025-09-03T20:40:15Z" }  -> usa 'ts'
              (si 'ts' no tiene tz, lo tomamos como LOCAL)
    """
    payload = (payload or "").strip()

    # JSON
    try:
        obj = json.loads(payload)
        if isinstance(obj, (int, float)):
            return float(obj), now_local_naive()
        if isinstance(obj, dict) and "value" in obj:
            v = float(obj["value"])
            ts = obj.get("ts")
            if ts:
                # soporta ISO con Z/offset o sin tz (local)
                if isinstance(ts, str):
                    s = ts.strip()
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    try:
                        dt = datetime.fromisoformat(s)
                    except Exception:
                        dt = isoparse(ts)
                else:
                    dt = None
                return v, to_local_naive_from_any(dt)
            return v, now_local_naive()
    except Exception:
        pass

    # número simple
    try:
        return float(payload.replace(",", ".")), now_local_naive()
    except Exception:
        return None, now_local_naive()

def main():
    db = DB()
    rows = db.load_sensors()
    if not rows:
        log.warning("No se encontraron estaciones/sensores en BD.")
    else:
        log.info("Sensores cargados: %d", len(rows))

    # topic -> (sensor_id, mn, mx)  (para validaciones futuras si quieres)
    topic_to_sid: Dict[str, Tuple[int, Optional[float], Optional[float]]] = {}
    subs = []

    for r in rows:
        station = r["station_name"].strip()
        sensor  = r["sensor_name"].strip()
        sid, mn, mx = db.map[(station.lower(), sensor.lower())]

        t1 = f"{station}/{sensor}/"
        t2 = f"{station}/{sensor}"
        topic_to_sid[t1.rstrip("/").lower()] = (sid, mn, mx)
        topic_to_sid[t2.rstrip("/").lower()] = (sid, mn, mx)
        subs.append(t1)

    client = MqttClient(client_id=f"ingestor_local_{os.getpid()}", transport="websockets")
    client.ws_set_options(path=MQTT_WS_PATH)

    def on_connect(cli, userdata, flags, rc):
        if rc == 0:
            log.info("MQTT conectado. Suscribiendo %d tópicos…", len(subs))
            for t in subs:
                cli.subscribe(t, qos=0)
            for t in subs:
                cli.subscribe(t.rstrip("/"), qos=0)
        else:
            log.error("Error conectando MQTT rc=%s", rc)

    def on_message(cli, userdata, msg):
        info = topic_to_sid.get(msg.topic.rstrip("/").lower())
        if not info:
            return
        sensor_id, mn, mx = info
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            return

        value, ts_local = parse_payload(payload)
        if value is None:
            return

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
