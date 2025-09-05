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

# ================== CONFIG (según lo que nos diste) ==================
DB_NAME = "Auralis"
DB_USER = "root"
DB_PASSWORD = "daniel586"
DB_HOST = "34.30.17.212"
DB_PORT = 3306

MQTT_HOST = "34.30.17.212"
MQTT_PORT = 8081          # WebSocket
MQTT_WS_PATH = "/"        # importante: en tu front usas "/", mantenemos igual

# Si quieres filtrar solo sensores/estaciones activas, déjalo en True.
ONLY_ACTIVE = True

# ====================================================================

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("mqtt_to_db_simple")

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

SQL_INSERT = """
INSERT INTO measurements_measurement (sensor_id, timestamp, value, is_valid)
VALUES (%s, %s, %s, %s);
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

    def insert_measurement(self, sensor_id: int, ts_utc, value: float, is_valid: bool):
        # Guardamos UTC "naive" (MySQL lo admite sin tz)
        if ts_utc.tzinfo is not None:
            ts_utc = ts_utc.astimezone(dt_timezone.utc).replace(tzinfo=None)
        with self.conn.cursor() as cur:
            cur.execute(SQL_INSERT, (sensor_id, ts_utc, float(value), 1 if is_valid else 0))


def parse_payload(payload: str):
    """
    Devuelve (value: float|None, ts_utc: datetime).
    Acepta:
      - número simple: "123.45"
      - JSON: {"value": 123.45, "ts": "2025-09-03T20:40:15Z"} (ts opcional)
    """
    payload = (payload or "").strip()
    now_utc = datetime.now(dt_timezone.utc)

    # JSON
    try:
        obj = json.loads(payload)
        if isinstance(obj, (int, float)):
            return float(obj), now_utc
        if isinstance(obj, dict) and "value" in obj:
            v = float(obj["value"])
            if obj.get("ts"):
                dt = isoparse(str(obj["ts"]))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=dt_timezone.utc)
                return v, dt.astimezone(dt_timezone.utc)
            return v, now_utc
    except Exception:
        pass

    # número simple
    try:
        return float(payload.replace(",", ".")), now_utc
    except Exception:
        return None, now_utc


def compute_is_valid(value: float, mn: Optional[float], mx: Optional[float]) -> bool:
    if mn is None or mx is None:
        return True
    return mn <= value <= mx


def main():
    db = DB()
    rows = db.load_sensors()
    if not rows:
        log.warning("No se encontraron estaciones/sensores en BD.")
    else:
        log.info("Sensores cargados: %d", len(rows))

    # Mapa para resolver rápidamente sensor_id por tópico
    # topic esperado: "Estacion/Sensor/" (con o sin slash final)
    topic_to_sid: Dict[str, Tuple[int, Optional[float], Optional[float]]] = {}
    subs = []

    for r in rows:
        station = r["station_name"].strip()
        sensor  = r["sensor_name"].strip()
        sid, mn, mx = db.map[(station.lower(), sensor.lower())]

        t1 = f"{station}/{sensor}/"
        t2 = f"{station}/{sensor}"
        # guardamos sin slash final como clave (normalizamos al comparar)
        topic_to_sid[t1.rstrip("/").lower()] = (sid, mn, mx)
        topic_to_sid[t2.rstrip("/").lower()] = (sid, mn, mx)
        subs.append(t1)  # nos suscribimos al que termina con "/"

    # --- MQTT ---
    client = MqttClient(client_id=f"ingestor_{os.getpid()}", transport="websockets")
    client.ws_set_options(path=MQTT_WS_PATH)  # en tu front usas "/", mantenemos "/"

    def on_connect(cli, userdata, flags, rc):
        if rc == 0:
            log.info("MQTT conectado %s:%s (WS path=%s). Suscribiendo %d tópicos...",
                     MQTT_HOST, MQTT_PORT, MQTT_WS_PATH, len(subs))
            for t in subs:
                cli.subscribe(t, qos=0)
            # Opcional: también al patrón sin slash final
            # (no todos los brokers aceptan lista duplicada, pero no hace daño)
            for t in subs:
                cli.subscribe(t.rstrip("/"), qos=0)
        else:
            log.error("Error conectando MQTT rc=%s", rc)

    def on_message(cli, userdata, msg):
        topic_key = msg.topic.rstrip("/").lower()
        info = topic_to_sid.get(topic_key)
        if not info:
            # No estaba en el listado precargado
            return
        sensor_id, mn, mx = info

        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            return

        value, ts_utc = parse_payload(payload)
        if value is None:
            return

        is_valid = compute_is_valid(value, mn, mx)
        try:
            db.insert_measurement(sensor_id, ts_utc, value, is_valid)
        except Exception as e:
            log.exception("Error insertando medición (sensor_id=%s): %s", sensor_id, e)

    def on_disconnect(cli, userdata, rc):
        if rc != 0:
            log.warning("Desconectado inesperadamente (rc=%s). Reintentando…", rc)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Señales para parar limpio
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
