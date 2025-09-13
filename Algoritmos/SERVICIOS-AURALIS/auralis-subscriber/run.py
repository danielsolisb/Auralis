#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import signal, logging, time
from config import Settings
from mqtt_worker import SubscriberService

def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
    )

def main():
    s = Settings()
    setup_logging(s.LOG_LEVEL)
    logging.info("Auralis Subscriber starting…")
    logging.info("DB=%s@%s:%s MQTT=%s:%s TLS=%s", s.DB_NAME, s.DB_HOST, s.DB_PORT, s.MQTT_HOST, s.MQTT_PORT, s.MQTT_TLS)

    srv = SubscriberService(s)

    def _sigterm(signum, frame):
        logging.warning("Signal %s received, stopping…", signum)
        srv.stop()
        raise SystemExit(0)  # salir del loop principal de inmediato

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    srv.start()
    try:
        while True:
            time.sleep(2)
    finally:
        srv.stop()
        logging.info("Auralis Subscriber stopped.")

if __name__ == "__main__":
    main()
