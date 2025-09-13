import os
from dataclasses import dataclass

def getenv(name: str, default=None, cast=None):
    val = os.getenv(name, default)
    if cast and val is not None:
        try:
            return cast(val)
        except Exception:
            return default
    return val

@dataclass
class Settings:
    # Database
    DB_NAME: str = getenv("DB_NAME", "Auralis")
    DB_USER: str = getenv("DB_USER", "root")
    DB_PASSWORD: str = getenv("DB_PASSWORD", "")
    DB_HOST: str = getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = getenv("DB_PORT", 3306, int)

    # MQTT
    MQTT_HOST: str = getenv("MQTT_HOST", "127.0.0.1")
    MQTT_PORT: int = getenv("MQTT_PORT", 1883, int)
    MQTT_USERNAME: str = getenv("MQTT_USERNAME", None)
    MQTT_PASSWORD: str = getenv("MQTT_PASSWORD", None)
    MQTT_TLS: bool = getenv("MQTT_TLS", "false").lower() in ("1","true","yes","on")
    MQTT_KEEPALIVE: int = getenv("MQTT_KEEPALIVE", 60, int)
    MQTT_CLIENT_ID: str = getenv("MQTT_CLIENT_ID", None)
    MQTT_QOS: int = getenv("MQTT_QOS", 0, int)

    # Subscriber behaviour
    SYNC_INTERVAL_SEC: int = getenv("SYNC_INTERVAL_SEC", 15, int)
    WRITE_BATCH_SIZE: int = getenv("WRITE_BATCH_SIZE", 200, int)
    WRITE_FLUSH_MS: int = getenv("WRITE_FLUSH_MS", 800, int)
    MAX_QUEUE: int = getenv("MAX_QUEUE", 5000, int)
    LOG_LEVEL: str = getenv("LOG_LEVEL", "INFO")
    TZ_NAME: str = getenv("TZ_NAME", "America/Guayaquil")

    # Event evaluation
    EVAL_PERSISTENCE_DEFAULT: int = getenv("EVAL_PERSISTENCE_DEFAULT", 0, int)
    EVAL_USE_HYSTERESIS: bool = getenv("EVAL_USE_HYSTERESIS", "true").lower() in ("1","true","yes","on")

    # Optional dedupe (no usado por defecto)
    ENABLE_DEDUP: bool = getenv("ENABLE_DEDUP", "false").lower() in ("1","true","yes","on")
    DEDUP_MIN_MS: int = getenv("DEDUP_MIN_MS", 50, int)
