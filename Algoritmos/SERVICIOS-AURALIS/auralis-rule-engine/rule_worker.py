import redis
import time
import json
import logging
import os
from datetime import datetime
import pytz
from . import config, db

WORKER_ID = f"worker-{os.getpid()}"
log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
logging.basicConfig(level=log_level, format=f'%(asctime)s - %(levelname)s - [{WORKER_ID}] - %(message)s')

class RuleWorker:
    def __init__(self):
        self.redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB, decode_responses=True)
        self.rules_cache = {}
        self.last_sync_time = 0
        try:
            self.local_tz = pytz.timezone(config.TZ_NAME)
            logging.info(f"Zona horaria configurada: {config.TZ_NAME}")
        except pytz.UnknownTimeZoneError:
            logging.error(f"Zona horaria desconocida: '{config.TZ_NAME}'. Usando UTC por defecto.")
            self.local_tz = pytz.utc

    def sync_rules(self):
        if time.time() - self.last_sync_time < config.SYNC_INTERVAL_RULES:
            return
        logging.info("Sincronizando reglas desde la base de datos...")
        # Lógica de carga de reglas (se implementará en detalle más adelante)
        self.last_sync_time = time.time()
        logging.info("Sincronización de reglas completada.")

    def evaluate(self, message):
        sensor_id = message['sensor_id']
        value = message['value']
        logging.info(f"Procesando: Sensor ID {sensor_id}, Valor {value}")
        # Lógica de evaluación (se implementará en detalle más adelante)
        # Simulación:
        rule_name_simulated = "Simulación de Temperatura Alta"
        rule_severity_simulated = "CRITICAL"
        self.create_event(sensor_id, value, rule_name_simulated, rule_severity_simulated)

    def create_event(self, sensor_id, value, rule_name, severity):
        connection = db.get_db_connection()
        if not connection:
            logging.error("No se pudo crear el evento por fallo de conexión a la BD.")
            return
        try:
            with connection.cursor() as cursor:
                table_name = "events_alarm" if severity == 'CRITICAL' else "events_warning"
                local_now = datetime.now(self.local_tz)
                description = f"Regla avanzada '{rule_name}' disparada."
                common_cols = "sensor_id, value, `timestamp`, description, is_active"
                if table_name == "events_alarm":
                    query = f"INSERT INTO {table_name} ({common_cols}, severity, notified) VALUES (%s, %s, %s, %s, TRUE, %s, FALSE)"
                    params = (sensor_id, value, local_now, description, severity)
                else: # events_warning
                    query = f"INSERT INTO {table_name} ({common_cols}, acknowledged) VALUES (%s, %s, %s, %s, TRUE, FALSE)"
                    params = (sensor_id, value, local_now, description)
                cursor.execute(query, params)
            connection.commit()
            logging.info(f"Evento de {table_name} creado para el sensor {sensor_id} con hora local {local_now}.")
        except Exception as e:
            logging.error(f"Error al crear evento para el sensor {sensor_id}: {e}")
            connection.rollback()
        finally:
            connection.close()

    def run(self):
        logging.info("Iniciando worker del motor de reglas...")
        self.sync_rules()
        while True:
            try:
                self.sync_rules()
                message_json = self.redis_client.brpop(config.REDIS_QUEUE_NAME, timeout=10)
                if message_json:
                    _, message_data = message_json
                    message = json.loads(message_data)
                    self.evaluate(message)
            except redis.exceptions.ConnectionError as e:
                logging.error(f"Error de conexión con Redis: {e}. Reintentando en 5 segundos...")
                time.sleep(5)
            except Exception as e:
                logging.error(f"Error inesperado en el bucle principal del worker: {e}")
                time.sleep(5)

if __name__ == '__main__':
    worker = RuleWorker()
    worker.run()