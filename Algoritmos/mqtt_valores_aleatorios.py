#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER_HOST = "34.135.82.255"
BROKER_PORT = 8081            # WebSocket típicamente en 8081
USE_WEBSOCKET = True          # Usaremos WebSocket porque el puerto es 8081
KEEPALIVE = 60

TOPIC_FLOW    = "Sacha53/Flow/"
TOPIC_PCASING = "Sacha53/PCasing/"
TOPIC_PTUBING = "Sacha53/Ptubing/"
TOPIC_FRECUENCY = "Sacha53/VSDTargetFreq/"
TOPIC_PRESSUREINTAKE = "Sacha53/DHIntakePressure/" 
TOPIC_TEMP_MOT = "Sacha53/DHMotorTemp/" 
TOPIC_AMPER = "Sacha53/Amperimetro/" 


PUBLISH_INTERVAL_SEC = 3
QOS = 0
RETAIN = False  # cambia a True si quieres retener el último valor

# ----- Callbacks -----
def on_connect(client, userdata, flags, reason_code, properties=None):
    ok = reason_code == 0
    print(f"[{ts()}] Conectado: {ok}. reason_code={reason_code}")
    # Suscribirse a los tres topics
    client.subscribe([(TOPIC_FLOW, QOS), (TOPIC_PCASING, QOS), (TOPIC_PTUBING, QOS), (TOPIC_FRECUENCY, QOS), (TOPIC_PRESSUREINTAKE, QOS)])


def on_message(client, userdata, msg):
    print(f"[{ts()}] RX  {msg.topic} -> {msg.payload.decode(errors='ignore')}")

def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"[{ts()}] Desconectado. reason_code={reason_code}")

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ----- Generadores de valores -----
def gen_flow():
    # 100 .. 1,000,000 (entero)
    return str(random.randint(100, 1_000_000))

def gen_pressure():
    # 0 .. 300 (con dos decimales)
    return f"{random.uniform(0, 300):.2f}"

def gen_pressure2():
    # 0 .. 300 (con dos decimales)
    return f"{random.uniform(0, 1000):.2f}"

def gen_frecuency():
    # 0 .. 300 (con dos decimales)
    return f"{random.uniform(0, 100):.2f}"

def gen_temp():
    # 0 .. 300 (con dos decimales)
    return f"{random.uniform(0, 100):.2f}"
def gen_amper():
    # 0 .. 300 (con dos decimales)
    return f"{random.uniform(0, 60):.2f}"

def main():
    # Cliente MQTT
    client = mqtt.Client(transport="websockets" if USE_WEBSOCKET else "tcp")
    # Si tu broker requiere un path WS (por ejemplo "/mqtt"), descomenta:
    # client.ws_set_options(path="/mqtt")

    # Si tu broker requiere usuario/clave:
    # client.username_pw_set("usuario", "clave")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
    client.loop_start()

    try:
        print(f"[{ts()}] Publicando cada {PUBLISH_INTERVAL_SEC}s en:")
        print(f"  - {TOPIC_FLOW}     (100..1,000,000)")
        print(f"  - {TOPIC_PCASING}  (0..300)")
        print(f"  - {TOPIC_PTUBING}  (0..300)")
        print(f"  - {TOPIC_FRECUENCY}  (0..300)")
        print(f"  - {TOPIC_PRESSUREINTAKE}  (0..300)")
        print(f"  - {TOPIC_TEMP_MOT}  (0..100)")
        print(f"  - {TOPIC_AMPER}  (0..60)")


        while True:
            flow_val    = gen_flow()
            casing_val  = gen_pressure()
            tubing_val  = gen_pressure()
            frecuency_val = gen_frecuency()
            pressureintake_val = gen_pressure2()
            temp_mot_val = gen_temp()
            amper_val = gen_amper()


            # Publicar como payloads simples (números en texto)
            client.publish(TOPIC_FLOW,    flow_val,   qos=QOS, retain=RETAIN)
            client.publish(TOPIC_PCASING, casing_val, qos=QOS, retain=RETAIN)
            client.publish(TOPIC_PTUBING, tubing_val, qos=QOS, retain=RETAIN)
            client.publish(TOPIC_FRECUENCY, frecuency_val, qos=QOS, retain=RETAIN)
            client.publish(TOPIC_PRESSUREINTAKE, pressureintake_val, qos=QOS, retain=RETAIN)
            client.publish(TOPIC_TEMP_MOT, temp_mot_val, qos=QOS, retain=RETAIN)
            client.publish(TOPIC_AMPER, amper_val, qos=QOS, retain=RETAIN)



            print(f"[{ts()}] TX  {TOPIC_FLOW}    -> {flow_val}")
            print(f"[{ts()}] TX  {TOPIC_PCASING} -> {casing_val}")
            print(f"[{ts()}] TX  {TOPIC_PTUBING} -> {tubing_val}")
            print(f"[{ts()}] TX  {TOPIC_FRECUENCY} -> {gen_pressure()}")
            print(f"[{ts()}] TX  {TOPIC_PRESSUREINTAKE} -> {gen_pressure()}")
            print(f"[{ts()}] TX  {TOPIC_TEMP_MOT} -> {gen_temp()}")
            print(f"[{ts()}] TX  {TOPIC_AMPER} -> {gen_amper()}")



            time.sleep(PUBLISH_INTERVAL_SEC)
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Saliendo...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
