# /opt/auralis-subscriber/models.py

from typing import List, Tuple
from dataclasses import dataclass
from db import DB

@dataclass
class SensorRow:
    id: int
    mqtt_topic: str

class Repo:
    def __init__(self, db: DB):
        self.db = db

    def list_active_sensors(self) -> List[SensorRow]:
        """
        Obtiene solo los campos necesarios para el subscriber:
        el ID del sensor y su tópico MQTT.
        """
        sql = """
            SELECT id, mqtt_topic 
            FROM sensorhub_sensor 
            WHERE is_active = TRUE AND mqtt_topic IS NOT NULL AND mqtt_topic != ''
        """
        rows = self.db.execute(sql)
        return [SensorRow(id=r["id"], mqtt_topic=r["mqtt_topic"]) for r in rows]

    def insert_measurements(self, rows: List[Tuple[int, str, float]]):
        """
        Inserta un lote de mediciones en la base de datos.
        Esta es ahora la única función de escritura de este repositorio.
        """
        if not rows:
            return
        # La consulta asume que el campo timestamp en la BD se llama 'measured_at'
        sql = "INSERT INTO measurements_measurement (sensor_id, measured_at, value) VALUES (%s, %s, %s)"
        self.db.executemany(sql, rows)