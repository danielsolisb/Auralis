# /opt/auralis-rule-engine/src/rule_worker.py

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
        """Carga y cachea todas las reglas y condiciones desde la base de datos."""
        if time.time() - self.last_sync_time < config.SYNC_INTERVAL_RULES:
            return

        logging.info("Sincronizando reglas desde la base de datos...")
        # (La lógica de carga de reglas completa la implementaremos en el futuro)
        # Por ahora, nos aseguramos de que la caché esté vacía si no hay reglas.
        self.rules_cache = {}
        # TODO: Implementar la carga real de la estructura de árbol de reglas.
        
        self.last_sync_time = time.time()
        logging.info("Sincronización de reglas completada.")
    
    def evaluate(self, message):
        """
        Punto de entrada para la evaluación de un mensaje.
        Ahora solo crea un evento si una regla REAL se cumple.
        """
        sensor_id = message['sensor_id']
        value = message['value']
        
        logging.info(f"Procesando: Sensor ID {sensor_id}, Valor {value}")

        # >>> INICIO DE LA LÓGICA CORREGIDA <<<
        
        # 1. Comprobar si hay reglas relevantes en la caché para este sensor.
        #    Esta es la comprobación que faltaba.
        if not self.rules_cache:
             logging.debug(f"No hay reglas cargadas en la caché. Se ignora el mensaje del sensor {sensor_id}.")
             return

        # TODO: Implementar la lógica de evaluación real contra las reglas en `self.rules_cache`.
        # El siguiente bloque es un ejemplo de cómo se vería la lógica final.
        # Por ahora, no hará nada hasta que implementemos la carga de reglas en sync_rules.
        
        # rules_for_sensor = self.find_rules_for_sensor(sensor_id)
        # for rule in rules_for_sensor:
        #     is_triggered = self.evaluate_rule_tree(rule, message)
        #     if is_triggered:
        #         logging.info(f"¡REGLA DISPARADA! Nombre: {rule['name']}, Sensor: {sensor_id}")
        #         self.create_event(sensor_id, value, rule['name'], rule['severity'])
        
        # >>> FIN DE LA LÓGICA CORREGIDA <<<
        

    def create_event(self, sensor_id, value, rule_name, severity):
        """Inserta un nuevo registro de evento en la base de datos con la hora local."""
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