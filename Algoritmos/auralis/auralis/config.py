# auralis/config.py

import os

# MQTT (Mosquitto)
MQTT_BROKER_HOST = "34.135.82.255"
MQTT_BROKER_PORT = 1883
MQTT_USERNAME = ""  # sin usuario
MQTT_PASSWORD = ""  # sin password

# Celery + Redis (si decides usarlo como broker)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Base de datos MySQL
DB_HOST = "localhost"               # Cambia si tu DB está en otra IP
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "Daniel14586solis"
DB_NAME = "Auralis"


# Tiempo en segundos para considerar un sensor inactivo (por defecto 5 minutos)
SENSOR_INACTIVITY_THRESHOLD = int(os.getenv("SENSOR_INACTIVITY_THRESHOLD", "300"))