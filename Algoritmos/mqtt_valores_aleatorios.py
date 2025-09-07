#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
from collections import OrderedDict
from datetime import datetime
from typing import Optional, Callable
import paho.mqtt.client as mqtt

# ========================
# Config broker
# ========================
BROKER_HOST = "34.30.17.212"
BROKER_PORT = 8081                 # WebSocket en 8081
USE_WEBSOCKET = True               # usar WS
KEEPALIVE = 60

# Si tu broker WS requiere un path (p.ej. "/mqtt"), descomenta:
WS_PATH: Optional[str] = None
# WS_PATH = "/mqtt"

# ========================
# Config tópicos
# ========================
STATION = "Sacha53"                # nombre de estación

def make_topic(station: str, sensor: str) -> str:
    """Devuelve /<station>/<sensor>/ con slash inicial y final."""
    return f"/{station}/{sensor}/"

# ========================
# Generadores de valores
# ========================

def gen_current() -> str:          # A
    return f"{random.uniform(10, 11):.2f}"

def gen_pressure_1k() -> str:      # PSI ~ 0..1000
    return f"{random.uniform(650, 654):.2f}"

def gen_pressure_2k() -> str:      # PSI ~ 0..1000
    return f"{random.uniform(628, 640):.2f}"

def gen_frequency() -> str:        # Hz
    return f"{random.uniform(20, 24):.2f}"

# --- Helper para variaciones suaves (random walk acotado) ---
def make_smooth_gen(
    lo: float,
    hi: float,
    step: float = 0.25,
    start: Optional[float] = None,
    ndigits: int = 2
) -> Callable[[], str]:
    """
    Crea un generador 'suave' entre [lo, hi].
    step: tamaño máximo del paso por muestra (cuanto menor, más suave).
    """
    cur = start if start is not None else (lo + hi) / 2.0

    def _gen() -> str:
        nonlocal cur
        cur += random.uniform(-step, step)
        # rebotes suaves en los bordes
        if cur < lo:
            cur = lo + (lo - cur) * 0.2
        elif cur > hi:
            cur = hi - (cur - hi) * 0.2
        return f"{round(cur, ndigits):.{ndigits}f}"

    return _gen

# Sensores a publicar (nombre_de_sensor -> función generadora)
# Los 3 nuevos usan el generador suave para mantener variación baja.
gen_anular     = make_smooth_gen(120.0, 125.0, step=0.20, start=122.5, ndigits=2)
gen_casing     = make_smooth_gen(80.0, 88.0, step=0.35, start=179.0, ndigits=2)
gen_motor_temp = make_smooth_gen(40.0,  45.0,  step=0.15, start=42.5,  ndigits=2)

SENSORS = OrderedDict([
    ("Motor_Current",            gen_current),
    ("Pump_Discharge_Pressure",  gen_pressure_1k),
    ("Pump_Intake_Pressure",     gen_pressure_2k),
    ("VFD_Output_Frecuency",     gen_frequency),
    # --- nuevos ---
    ("Anular",                   gen_anular),
    ("Casing",                   gen_casing),
    ("Motor_temp",               gen_motor_temp),
])

PUBLISH_INTERVAL_SEC = 3
QOS = 0
RETAIN = False

# ========================
# Util
# ========================
def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ========================
# Callbacks
# ========================
def on_connect(client, userdata, flags, reason_code, properties=None):
    ok = reason_code == 0
    print(f"[{ts()}] Conectado: {ok}. reason_code={reason_code}")
    # Suscripción única por estación para ver en consola todo lo que caiga:
    wildcard = make_topic(STATION, "+")  # "/Sacha53/+/"
    client.subscribe(wildcard, qos=QOS)
    print(f"[{ts()}] Subscrito a {wildcard}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode(errors="ignore")
    except Exception:
        payload = str(msg.payload)
    print(f"[{ts()}] RX  {msg.topic} -> {payload}")

def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"[{ts()}] Desconectado. reason_code={reason_code}")

# ========================
# Main
# ========================
def main():
    # Cliente MQTT
    client = mqtt.Client(transport="websockets" if USE_WEBSOCKET else "tcp")
    if USE_WEBSOCKET and WS_PATH:
        client.ws_set_options(path=WS_PATH)

    # Si tu broker requiere usuario/clave:
    # client.username_pw_set("usuario", "clave")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
    client.loop_start()

    try:
        print(f"[{ts()}] Publicando cada {PUBLISH_INTERVAL_SEC}s:")
        for name in SENSORS:
            print(f"  - {make_topic(STATION, name)}")

        while True:
            for sensor_name, gen_func in SENSORS.items():
                value = gen_func()
                topic = make_topic(STATION, sensor_name)
                # Publica
                client.publish(topic, value, qos=QOS, retain=RETAIN)
                print(f"[{ts()}] TX  {topic} -> {value}")
            time.sleep(PUBLISH_INTERVAL_SEC)

    except KeyboardInterrupt:
        print(f"\n[{ts()}] Saliendo...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
