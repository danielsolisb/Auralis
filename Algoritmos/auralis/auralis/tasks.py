# auralis/tasks.py

from celery import Celery
from sqlalchemy import text
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, SENSOR_INACTIVITY_THRESHOLD
from .db import get_db_session
from .validations import is_valid_value, is_near_threshold
from datetime import datetime

celery_app = Celery(
    'auralis',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

@celery_app.task
def process_measurement(sensor_id, value):
    """
    Procesa una medición:
    - Inserta la medición en measurements_measurement.
    - Si el valor no es válido, inserta un registro en events_alarm.
    - Si el valor es válido pero está cerca del umbral, inserta un registro en events_warning.
    """
    with next(get_db_session()) as db:
        # Validamos el valor según los rangos definidos para el sensor.
        valid, min_val, max_val = is_valid_value(db, sensor_id, value)
        
        # Insertamos la medición en measurements_measurement
        query_measure = text("""
            INSERT INTO measurements_measurement (sensor_id, value, is_valid, timestamp)
            VALUES (:sensor_id, :value, :is_valid, NOW())
        """)
        db.execute(query_measure, {
            "sensor_id": sensor_id,
            "value": value,
            "is_valid": valid
        })
        # Opcional: obtener el ID de la medición (si es necesario)
        measurement_id = db.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
        
        # Si el valor no es válido, registramos una alarma en events_alarm
        if not valid:
            # Inserción en events_alarm (Alarma)
            query_alarm = text("""
                INSERT INTO events_alarm (sensor_id, value, timestamp, severity, notified, description, is_active, resolution_notes)
                VALUES (:sensor_id, :value, NOW(), :severity, :notified, :description, :is_active, :resolution_notes)
            """)
            db.execute(query_alarm, {
                "sensor_id": sensor_id,
                "value": value,
                "severity": "MEDIA",    # O la severidad determinada según la lógica de tu aplicación
                "notified": False,
                "description": "",        # Cadena vacía si no se requiere descripción
                "is_active": True,        # Según el modelo, por defecto True
                "resolution_notes": ""    # Se asigna cadena vacía para evitar el error
            })



            #query_alarm = text("""
            #    INSERT INTO events_alarm (sensor_id, value, timestamp, severity, notified, description)
            #    VALUES (:sensor_id, :value, NOW(), :severity, :notified, :description)
            #""")
            #db.execute(query_alarm, {
            #    "sensor_id": sensor_id,
            #    "value": value,
            #    "severity": "MEDIA",  # Puedes ajustar la severidad según la lógica de tu aplicación
            #    "notified": False,
            #    "description": ""     # Se asigna una cadena vacía
            #})
        
        # Si el valor es válido pero está cerca del umbral, registramos una advertencia en events_warning
        if valid and is_near_threshold(value, min_val, max_val, threshold=0.1):
            query_warning = text("""
                INSERT INTO events_warning (sensor_id, value, timestamp, acknowledged, description, is_active, resolution_notes)
                VALUES (:sensor_id, :value, NOW(), :acknowledged, :description, :is_active, :resolution_notes)
            """)
            db.execute(query_warning, {
                "sensor_id": sensor_id,
                "value": value,
                "acknowledged": False,
                "description": "",
                "is_active": True,
                "resolution_notes": ""
            })

            
            #query_warning = text("""
            #    INSERT INTO events_warning (sensor_id, value, timestamp, acknowledged, description)
            #    VALUES (:sensor_id, :value, NOW(), :acknowledged, :description)
            #""")
            #db.execute(query_warning, {
            #    "sensor_id": sensor_id,
            #    "value": value,
            #    "acknowledged": False,
            #    "description": ""     # Se asigna una cadena vacía
            #})
        
        # Confirmamos la transacción
        db.commit()
        
    return True

@celery_app.task
def check_sensor_status():
    """
    Tarea periódica que revisa la actividad de los sensores y actualiza el estado:
      1. Para cada sensor en sensorhub_sensor, se consulta la última medición registrada en measurements_measurement.
         Si no existe dato o si la diferencia entre NOW() y ese timestamp supera el umbral configurado,
         se marca el sensor como inactivo (is_active = False); de lo contrario, se marca como activo.
      2. Luego, para cada estación en sensorhub_station, se cuenta la cantidad de sensores activos asociados.
         Si ninguno está activo, se actualiza la estación (is_active = False); si al menos uno está activo, se marca como activa.
    """
    threshold = SENSOR_INACTIVITY_THRESHOLD  # umbral en segundos
    now = datetime.now()
    with next(get_db_session()) as db:
        # Actualizamos el estado de cada sensor
        sensors = db.execute(text("SELECT id FROM sensorhub_sensor")).fetchall()
        for sensor in sensors:
            sensor_id = sensor[0]
            result = db.execute(text("""
                SELECT MAX(timestamp) 
                FROM measurements_measurement 
                WHERE sensor_id = :sensor_id
            """), {"sensor_id": sensor_id}).fetchone()
            last_ts = result[0]  # Puede ser None si no hay mediciones
            if last_ts is None:
                # Sin mediciones, consideramos el sensor inactivo
                db.execute(text("UPDATE sensorhub_sensor SET is_active = False WHERE id = :sensor_id"), {"sensor_id": sensor_id})
            else:
                diff = (now - last_ts).total_seconds()
                if diff > threshold:
                    db.execute(text("UPDATE sensorhub_sensor SET is_active = False WHERE id = :sensor_id"), {"sensor_id": sensor_id})
                else:
                    db.execute(text("UPDATE sensorhub_sensor SET is_active = True WHERE id = :sensor_id"), {"sensor_id": sensor_id})
        
        # Actualizamos el estado de cada estación
        stations = db.execute(text("SELECT id FROM sensorhub_station")).fetchall()
        for station in stations:
            station_id = station[0]
            active_count = db.execute(text("""
                SELECT COUNT(*) 
                FROM sensorhub_sensor 
                WHERE station_id = :station_id AND is_active = True
            """), {"station_id": station_id}).fetchone()[0]
            if active_count == 0:
                db.execute(text("UPDATE sensorhub_station SET is_active = False WHERE id = :station_id"), {"station_id": station_id})
            else:
                db.execute(text("UPDATE sensorhub_station SET is_active = True WHERE id = :station_id"), {"station_id": station_id})
        db.commit()
    return True

# Configuración de Celery Beat para ejecutar la tarea periódica
celery_app.conf.beat_schedule = {
    'check-sensor-status-every-minute': {
        'task': 'auralis.tasks.check_sensor_status',
        'schedule': 60.0,  # se ejecuta cada 60 segundos
    },
}