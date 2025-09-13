from typing import List, Optional, Tuple
from dataclasses import dataclass
from db import DB

@dataclass
class SensorRow:
    id: int
    station_id: int
    company_id: int
    sensor_type_id: int
    name: str
    mqtt_topic: Optional[str]
    is_active: bool
    min_value: Optional[float]
    max_value: Optional[float]

@dataclass
class PolicyRow:
    id: int
    scope: str         # GLOBAL, COMPANY, SENSOR_TYPE, STATION, SENSOR
    alert_mode: str    # ABS or REL
    company_id: Optional[int]
    sensor_type_id: Optional[int]
    station_id: Optional[int]
    sensor_id: Optional[int]
    warn_high: Optional[float]
    alert_high: Optional[float]
    enable_low_thresholds: bool
    warn_low: Optional[float]
    alert_low: Optional[float]
    hysteresis: Optional[float]
    persistence_seconds: Optional[int]
    bands_active: bool
    color_warn: Optional[str]
    color_alert: Optional[str]
    updated_at: str

class Repo:
    def __init__(self, db: DB):
        self.db = db

    def list_active_sensors(self) -> List[SensorRow]:
        sql = '''
            SELECT s.id, s.station_id, st.company_id, s.sensor_type_id, s.name,
                   s.mqtt_topic, s.is_active, s.min_value, s.max_value
            FROM sensorhub_sensor AS s
            JOIN sensorhub_station AS st ON s.station_id = st.id
            WHERE s.is_active = 1 AND s.mqtt_topic IS NOT NULL AND s.mqtt_topic <> ''
        '''
        rows = self.db.execute(sql)
        return [
            SensorRow(
                id=r["id"], station_id=r["station_id"], company_id=r["company_id"],
                sensor_type_id=r["sensor_type_id"], name=r["name"],
                mqtt_topic=r["mqtt_topic"], is_active=bool(r["is_active"]),
                min_value=r["min_value"], max_value=r["max_value"]
            )
            for r in rows
        ]

    def list_active_policies(self) -> List[PolicyRow]:
        sql = '''
            SELECT id, scope, alert_mode, company_id, sensor_type_id, station_id, sensor_id,
                   warn_high, alert_high, enable_low_thresholds, warn_low, alert_low,
                   hysteresis, persistence_seconds, bands_active, color_warn, color_alert, updated_at
            FROM sensorhub_alertpolicy
            WHERE bands_active = 1
            ORDER BY updated_at DESC
        '''
        rows = self.db.execute(sql)
        return [
            PolicyRow(
                id=r["id"], scope=r["scope"], alert_mode=r["alert_mode"],
                company_id=r["company_id"], sensor_type_id=r["sensor_type_id"],
                station_id=r["station_id"], sensor_id=r["sensor_id"],
                warn_high=r["warn_high"], alert_high=r["alert_high"],
                enable_low_thresholds=bool(r["enable_low_thresholds"]),
                warn_low=r["warn_low"], alert_low=r["alert_low"],
                hysteresis=r["hysteresis"], persistence_seconds=r["persistence_seconds"],
                bands_active=bool(r["bands_active"]),
                color_warn=r["color_warn"], color_alert=r["color_alert"],
                updated_at=str(r["updated_at"])
            )
            for r in rows
        ]

    def insert_measurements(self, rows: List[Tuple[int, str, float]]):
        if not rows:
            return
        sql = "INSERT INTO measurements_measurement (sensor_id, measured_at, value) VALUES (%s, %s, %s)"
        self.db.executemany(sql, rows)

    def create_alarm(self, sensor_id: int, iso_ts: str, value: float, severity: str, description: str, notified=False):
        sql = '''INSERT INTO events_alarm
                 (sensor_id, timestamp, value, description, is_active, severity, notified)
                 VALUES (%s,%s,%s,%s,1,%s,%s)'''
        self.db.execute(sql, (sensor_id, iso_ts, value, description or "", severity, 1 if notified else 0))

    def create_warning(self, sensor_id: int, iso_ts: str, value: float, description: str):
        sql = '''INSERT INTO events_warning
                 (sensor_id, timestamp, value, description, is_active)
                 VALUES (%s,%s,%s,%s,1)'''
        self.db.execute(sql, (sensor_id, iso_ts, value, description or ""))
