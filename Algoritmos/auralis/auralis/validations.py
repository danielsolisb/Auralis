# auralis/validations.py

from sqlalchemy import text

def is_valid_value(db, sensor_id, value):
    """
    Verifica si el valor está dentro del rango [min_value, max_value].
    Retorna (bool, min_value, max_value).
    """
    # Consulta a la tabla sensorhub_sensor (o la que uses para almacenar min_value, max_value).
    query = text("SELECT min_value, max_value FROM sensorhub_sensor WHERE id = :sensor_id")
    result = db.execute(query, {"sensor_id": sensor_id}).fetchone()
    if not result:
        # Si no se encontró el sensor, consideramos no válido por defecto.
        return (False, None, None)
    
    min_val, max_val = result
    valid = (min_val <= value <= max_val)
    return (valid, min_val, max_val)

def is_near_threshold(value, min_val, max_val, threshold=0.1):
    """
    Retorna True si el valor está cerca del 10% de los extremos.
    threshold=0.1 => 10%
    """
    if min_val is None or max_val is None:
        return False
    
    range_val = max_val - min_val
    if range_val <= 0:
        return False

    margin = range_val * threshold
    
    # Cerca del mínimo
    if abs(value - min_val) <= margin:
        return True
    # Cerca del máximo
    if abs(max_val - value) <= margin:
        return True
    
    return False
