import paho.mqtt.client as mqtt
import random
import time
import signal
import sys

# Configuración del broker y topics
broker = "techdevsa.com"  # Cambia esto si es necesario
port = 1883               # Puerto para conexión MQTT sin TLS
topics = [
    "Cemestim/Pcasing/",
    "Cemestim/Ptubing/",
    "Cemestim/Flow/"
]

# Crear el cliente MQTT (usando la API de callbacks v2, que es la por defecto)
client = mqtt.Client(client_id="TestPublisher")

# Callback al conectar (firma adaptada para la API v2)
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Conectado exitosamente al broker MQTT.")
    else:
        print(f"Error en la conexión. Código: {rc}")

client.on_connect = on_connect

# Intentar conectarse al broker
try:
    client.connect(broker, port, keepalive=60)
except Exception as e:
    print("Error al conectar con el broker:", e)
    sys.exit(1)

# Iniciar el loop de red en un thread separado
client.loop_start()

# Función para manejar la señal de Ctrl+C y terminar de forma limpia
def signal_handler(sig, frame):
    print("\nInterrupción recibida, cerrando conexión...")
    client.loop_stop()
    client.disconnect()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print("Publicando valores aleatorios en los topics. Presiona Ctrl+C para detener.\n")

# Bucle infinito para publicar valores aleatorios en cada topic
while True:
    for topic in topics:
        # Generar un valor aleatorio entre 0 y 300 con dos decimales
        value = round(random.uniform(40, 200), 2)
        # Publicar el valor y capturar el resultado
        result = client.publish(topic, payload=str(value))
        # result[0] es el código de resultado (0 es éxito)
        if result[0] == 0:
            print(f"Publicado {value} en {topic}")
        else:
            print(f"Fallo al publicar en {topic}. Código de error: {result[0]}")
    # Esperar 2 segundos entre ciclos
    time.sleep(5)
