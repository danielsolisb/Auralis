# /opt/auralis-rule-engine/src/rule_worker.py (VERSIÓN FINAL Y COMPLETA)

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
        self.cache = {}
        self.last_sync_time = 0
        try:
            self.local_tz = pytz.timezone(config.TZ_NAME)
            logging.info(f"Zona horaria configurada: {config.TZ_NAME}")
        except pytz.UnknownTimeZoneError:
            logging.error(f"Zona horaria desconocida: '{config.TZ_NAME}'. Usando UTC por defecto.")
            self.local_tz = pytz.utc

    def sync_configuration(self):
        if time.time() - self.last_sync_time < config.SYNC_INTERVAL_RULES:
            return
        logging.info("Sincronizando configuración de alertas desde la base de datos...")
        connection = db.get_db_connection()
        if not connection: return

        new_cache = {'sensors': {}, 'rules': {}, 'policies': {}}
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT s.id, s.name, s.min_value, s.max_value, 
                           st.id as station_id, st.company_id, s.sensor_type_id
                    FROM sensorhub_sensor s
                    JOIN sensorhub_station st ON s.station_id = st.id
                    WHERE s.is_active = TRUE
                """)
                for row in cursor.fetchall():
                    new_cache['sensors'][row['id']] = row

                cursor.execute("SELECT * FROM sensorhub_alertpolicy WHERE bands_active = TRUE")
                for row in cursor.fetchall():
                    scope = row['scope']
                    if scope not in new_cache['policies']:
                        new_cache['policies'][scope] = []
                    new_cache['policies'][scope].append(row)

                cursor.execute("""
                    SELECT r.id as rule_id, r.name as rule_name, r.severity,
                           c.id as condition_id, c.name as condition_name, c.source_sensor_id, 
                           c.threshold_type, c.operator, c.threshold_config, c.linked_policy_id
                    FROM rulesengine_rule r
                    JOIN rulesengine_rulenode rn ON r.id = rn.rule_id
                    JOIN rulesengine_condition c ON rn.condition_id = c.id
                    WHERE r.is_active = TRUE AND rn.node_type = 'COND' AND rn.parent_id IS NULL
                """)
                for row in cursor.fetchall():
                    rule_id = row['rule_id']
                    if rule_id not in new_cache['rules']:
                        new_cache['rules'][rule_id] = {
                            'id': rule_id, 'name': row['rule_name'], 'severity': row['severity'],
                            'conditions': {}
                        }
                    sensor_id = row['source_sensor_id']
                    new_cache['rules'][rule_id]['conditions'][sensor_id] = row
            
            self.cache = new_cache
            self.last_sync_time = time.time()
            logging.info(f"Sincronización completada. Sensores: {len(self.cache['sensors'])}, Reglas: {len(self.cache['rules'])}")
        except Exception as e:
            logging.exception(f"Error durante la sincronización de reglas: {e}")
        finally:
            connection.close()

    def evaluate(self, message):
        sensor_id = message['sensor_id']
        value = message['value']
        logging.debug(f"Procesando: Sensor ID {sensor_id}, Valor {value}")
        sensor_info = self.cache['sensors'].get(sensor_id)
        if not sensor_info: return

        for rule in self.cache.get('rules', {}).values():
            condition = rule.get('conditions', {}).get(sensor_id)
            if condition:
                self.process_incident(rule, condition, sensor_info, value)

    def process_incident(self, rule, condition, sensor_info, value):
        redis_key = f"incident:rule:{rule['id']}:sensor:{sensor_info['id']}"
        is_triggered, threshold_info = self.check_condition(rule, condition, sensor_info, value)
        active_incident_json = self.redis_client.get(redis_key)
        
        if is_triggered:
            if not active_incident_json:
                logging.info(f"NUEVO INCIDENTE: Regla '{rule['name']}' para sensor '{sensor_info['name']}'. Valor: {value} {threshold_info}")
                self.manage_event_db('CREATE', rule=rule, sensor_id=sensor_info['id'], value=value, redis_key=redis_key)
            else:
                logging.debug(f"INCIDENTE ACTIVO: Regla '{rule['name']}'. Valor: {value}")
                self.manage_event_db('UPDATE', value=value, active_incident_json=active_incident_json)
        else:
            if active_incident_json:
                logging.info(f"INCIDENTE RESUELTO: Regla '{rule['name']}' para sensor '{sensor_info['name']}'. Valor: {value}")
                self.manage_event_db('RESOLVE', value=value, active_incident_json=active_incident_json, redis_key=redis_key)

    def check_condition(self, rule, condition, sensor_info, value):
        threshold = None
        threshold_key_map = { 'CRITICAL': 'alert_high', 'WARNING': 'warn_high' }
        
        if condition['threshold_type'] == 'STATIC':
            config_data = condition['threshold_config']
            if isinstance(config_data, str):
                try:
                    config_data = json.loads(config_data) if config_data else {}
                except json.JSONDecodeError:
                    logging.error(f"Error al decodificar JSON de threshold_config: {config_data}")
                    config_data = {}
            threshold = config_data.get('value')

        elif condition['threshold_type'] == 'POLICY' and condition['linked_policy_id']:
            policy = self.find_policy_by_id(condition['linked_policy_id'])
            if policy:
                threshold_key = threshold_key_map.get(rule['severity'], 'alert_high')
                threshold = self.calculate_absolute_threshold(policy, sensor_info, threshold_key)

        if threshold is None: return False, ""

        try:
            threshold = float(threshold)
            value = float(value)
        except (ValueError, TypeError):
            logging.warning(f"No se pudo convertir el valor o el umbral a número. Valor: {value}, Umbral: {threshold}")
            return False, ""

        op = condition['operator']
        triggered = False
        if op == '>' and value > threshold: triggered = True
        elif op == '<' and value < threshold: triggered = True
        elif op == '==' and value == threshold: triggered = True
        
        return triggered, f"(Umbral: {op} {threshold})"

    def find_policy_by_id(self, policy_id):
        for scope_policies in self.cache.get('policies', {}).values():
            for policy in scope_policies:
                if policy['id'] == policy_id:
                    return policy
        return None

    def calculate_absolute_threshold(self, policy, sensor_info, threshold_key):
        v = policy.get(threshold_key)
        if v is None: return None
        if policy['alert_mode'] == 'ABS': return float(v)
        
        smin = float(sensor_info.get('min_value') or 0.0)
        smax = float(sensor_info.get('max_value') or 1.0)
        span = max(0.0, smax - smin)
        return smin + float(v) * span

    def manage_event_db(self, action, **kwargs):
        connection = db.get_db_connection()
        if not connection: return
        try:
            with connection.cursor() as cursor:
                local_now = datetime.now(self.local_tz)

                if action == 'CREATE':
                    rule = kwargs['rule']
                    severity = rule['severity']
                    table_name = "events_alarm" if severity == 'CRITICAL' else "events_warning"
                    
                    if table_name == "events_alarm":
                        query = f"""
                            INSERT INTO {table_name} 
                            (sensor_id, rule_id, started_at, triggering_value, peak_value, `last_value`, description, is_active, update_count, severity, notified)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, 1, %s, FALSE)
                        """
                        # Asignamos una severidad por defecto si no viene en la regla
                        alarm_severity = rule.get('severity', 'CRITICAL')
                        params = (
                            kwargs['sensor_id'], rule['id'], local_now, kwargs['value'], kwargs['value'], kwargs['value'],
                            f"Incidente iniciado por la regla '{rule['name']}'.", alarm_severity
                        )
                    else: # events_warning
                        # --- INICIO DE LA CORRECCIÓN ---
                        query = f"""
                            INSERT INTO {table_name}
                            (sensor_id, rule_id, started_at, triggering_value, peak_value, `last_value`, description, is_active, update_count, acknowledged)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, 1, FALSE)
                        """
                        params = (
                            kwargs['sensor_id'], rule['id'], local_now, kwargs['value'], kwargs['value'], kwargs['value'],
                            f"Incidente iniciado por la regla '{rule['name']}'."
                        )
                        # --- FIN DE LA CORRECCIÓN ---

                    cursor.execute(query, params)
                    event_id = cursor.lastrowid
                    
                    incident_data = json.dumps({'status': 'FIRING', 'event_id': event_id, 'table': table_name})
                    self.redis_client.set(kwargs['redis_key'], incident_data)
                    logging.info(f"Creado nuevo incidente ID {event_id} en tabla {table_name}.")

                elif action == 'UPDATE':
                    active_incident = json.loads(kwargs['active_incident_json'])
                    event_id, table_name, value = active_incident['event_id'], active_incident['table'], kwargs['value']
                    query = f"UPDATE {table_name} SET `last_value` = %s, update_count = update_count + 1, peak_value = GREATEST(peak_value, %s) WHERE id = %s"
                    cursor.execute(query, (value, value, event_id))

                elif action == 'RESOLVE':
                    active_incident = json.loads(kwargs['active_incident_json'])
                    event_id, table_name, value = active_incident['event_id'], active_incident['table'], kwargs['value']
                    query = f"UPDATE {table_name} SET is_active = FALSE, resolved_at = %s, `last_value` = %s WHERE id = %s"
                    cursor.execute(query, (local_now, value, event_id))
                    self.redis_client.delete(kwargs['redis_key'])
            
            connection.commit()
        except Exception as e:
            logging.exception(f"Error gestionando evento en la BD: {e}")
            connection.rollback()
        finally:
            connection.close()

    def run(self):
        logging.info("Iniciando worker del motor de reglas...")
        while True:
            try:
                self.sync_configuration()
                message_json = self.redis_client.brpop(config.REDIS_QUEUE_NAME, timeout=5)
                if message_json:
                    _, message_data = message_json
                    message = json.loads(message_data)
                    self.evaluate(message)
            except redis.exceptions.ConnectionError as e:
                logging.error(f"Error de conexión con Redis: {e}. Reintentando...")
                time.sleep(5)
            except Exception as e:
                logging.exception(f"Error inesperado en el bucle principal del worker: {e}")
                time.sleep(5)

if __name__ == '__main__':
    worker = RuleWorker()
    worker.run()
