sudo nano /etc/systemd/system/auralis-rule-manager.service

[Unit]
Description=Auralis Rule Engine - Topic Manager
After=network.target mysql.service redis-server.service

[Service]
User=dsb586
Group=dsb586
WorkingDirectory=/opt/auralis-rule-engine
ExecStart=/opt/auralis-rule-engine/venv/bin/python -m src.topic_manager
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

---------------------------------------------------------------------------
sudo nano /etc/systemd/system/auralis-rule-worker@.service

[Unit]
Description=Auralis Rule Engine - Worker %i
After=network.target mysql.service redis-server.service

[Service]
User=dsb586
Group=dsb586
WorkingDirectory=/opt/auralis-rule-engine
ExecStart=/opt/auralis-rule-engine/venv/bin/python -m src.rule_worker
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

---------------------------------------------------------------------
# 1. Recargar la configuración de systemd
sudo systemctl daemon-reload

# 2. Habilitar los servicios
sudo systemctl enable auralis-rule-manager.service
for i in {1..4}; do sudo systemctl enable auralis-rule-worker@$i.service; done

# 3. Iniciar los servicios
sudo systemctl start auralis-rule-manager.service
for i in {1..4}; do sudo systemctl start auralis-rule-worker@$i.service; done

# 4. Verificar el estado
sudo systemctl status auralis-rule-manager.service
sudo systemctl status auralis-rule-worker@*.service

----------------------------------------------------------------------------
sudo nano /etc/default/auralis-rule-engine

# Rellena con tus datos
DB_HOST=34.30.17.212
DB_PORT=3306
DB_NAME=Auralis
DB_USER=root
DB_PASSWORD=daniel586
MQTT_BROKER_HOST=34.30.17.212
MQTT_BROKER_PORT=1883
REDIS_HOST=127.0.0.1
SYNC_INTERVAL_TOPICS=60
SYNC_INTERVAL_RULES=300
LOG_LEVEL=INFO
TZ_NAME=America/Guayaquil

----------------------------------------------------------------------------
# Crear la estructura de directorios
sudo mkdir -p /opt/auralis-rule-engine/src
sudo touch /opt/auralis-rule-engine/src/__init__.py

# Crear y activar el entorno virtual
sudo python3 -m venv /opt/auralis-rule-engine/venv
source /opt/auralis-rule-engine/venv/bin/activate

# Instalar las librerías necesarias
pip install paho-mqtt python-dotenv PyMySQL redis pytz

# Desactivar el entorno por ahora
deactivate

# Asignar permisos a tu usuario
sudo chown -R dsb586:dsb586 /opt/auralis-rule-engine

