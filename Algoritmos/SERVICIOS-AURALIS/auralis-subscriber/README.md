Estructura:

/opt/auralis-subscriber/
├── requirements.txt
├── config.py
├── db.py
├── models.py
├── evaluator.py
├── mqtt_worker.py
└── run.py

/etc/default/auralis-subscriber
/etc/systemd/system/auralis-subscriber.service


Implementacion:
1.- Usuario/carpetas
sudo mkdir -p /opt/auralis-subscriber
sudo adduser --system --group --home /opt/auralis-subscriber auralis
sudo chown -R auralis:auralis /opt/auralis-subscriber
sudo chmod 750 /opt/auralis-subscriber

2 Crea los archivos en /opt/auralis-subscriber/
(usa sudo nano para cada uno y pega el contenido de arriba):

requirements.txt
config.py
db.py
models.py
evaluator.py
mqtt_worker.py
run.py (recuerda chmod +x al final)

3 Virtualenv + dependencias:
sudo -u auralis python3 -m venv /opt/auralis-subscriber/.venv
sudo -u auralis /opt/auralis-subscriber/.venv/bin/pip install --upgrade pip setuptools wheel
sudo -u auralis /opt/auralis-subscriber/.venv/bin/pip install -r /opt/auralis-subscriber/requirements.txt

4 Variables de entorno
sudo nano /etc/default/auralis-subscriber
# pega el contenido de ejemplo (ajusta DB/MQTT)

5 Servicio Systemd:
sudo nano /etc/systemd/system/auralis-subscriber.service
# pega el unit file

6 Permisos y arranque:
sudo chown -R auralis:auralis /opt/auralis-subscriber
sudo chmod +x /opt/auralis-subscriber/run.py

sudo systemctl daemon-reload
sudo systemctl enable auralis-subscriber
sudo systemctl start auralis-subscriber
sudo journalctl -u auralis-subscriber -f


