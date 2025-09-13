import os
from dotenv import load_dotenv

CONFIG_PATH = '/etc/default/auralis-rule-engine'
load_dotenv(dotenv_path=CONFIG_PATH)

# --- Configuración de la Base de Datos ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT', 3306))

# --- Configuración de MQTT ---
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USERNAME')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')
MQTT_CLIENT_ID_MANAGER = os.getenv('MQTT_CLIENT_ID_MANAGER', 'rule-engine-manager')
MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', 60))

# --- Configuración de Redis ---
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_QUEUE_NAME = os.getenv('REDIS_QUEUE_NAME', 'auralis_rule_engine_queue')

# --- Configuración General del Servicio ---
SYNC_INTERVAL_TOPICS = int(os.getenv('SYNC_INTERVAL_TOPICS', 60))
SYNC_INTERVAL_RULES = int(os.getenv('SYNC_INTERVAL_RULES', 300))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
TZ_NAME = os.getenv('TZ_NAME', 'UTC')