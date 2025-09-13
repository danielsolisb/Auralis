Documentación del Servicio auralis-rule-engine

1. Objetivo del Servicio
El auralis-rule-engine es un servicio de alto rendimiento, independiente y autónomo, diseñado para procesar datos de sensores en tiempo real. Sus responsabilidades principales son:
Descubrir y suscribirse de forma inteligente a los tópicos MQTT de los sensores activos definidos en la base de datos de Auralis.
Recibir mediciones de los sensores vía MQTT.
Evaluar reglas complejas y compuestas (basadas en múltiples condiciones, operadores lógicos, etc.) que han sido definidas en el backend de Django.
Gestionar el estado de las reglas en tiempo real utilizando una caché de alta velocidad (Redis).
Crear eventos de alarma o advertencia en la base de datos con la zona horaria local correcta cuando una regla se cumple.
El servicio está diseñado para ser escalable, permitiendo el procesamiento de un alto volumen de mensajes mediante un sistema de workers paralelos.

2. Arquitectura
El servicio se compone de dos tipos de procesos que se ejecutan de forma continua y paralela:
Topic Manager (topic_manager.py): Un único proceso responsable de sincronizarse con la base de datos para obtener la lista de tópicos MQTT activos. Gestiona las suscripciones en el broker MQTT y encola los mensajes entrantes en una cola de tareas de Redis.
Rule Workers (rule_worker.py): Múltiples procesos que consumen los mensajes de la cola de Redis. Cada worker carga la configuración de las reglas desde la base de datos, evalúa los datos entrantes contra estas reglas usando una caché de estado en Redis y, si una regla se dispara, escribe el evento resultante en la base de datos MySQL.

3. Prerrequisitos del Servidor
Sistema Operativo: Ubuntu 20.04+ o similar con systemd.
Python: Versión 3.8 o superior.
Redis: redis-server debe estar instalado y corriendo.
Dependencias de Python: paho-mqtt, python-dotenv, PyMySQL, redis, pytz.

4. Guía de Instalación y Configuración
Paso 4.1: Estructura de Directorios
El servicio se instala en /opt/auralis-rule-engine. La estructura final es la siguiente:
/opt/auralis-rule-engine/
├── venv/
└── src/
    ├── __init__.py
    ├── config.py
    ├── db.py
    ├── topic_manager.py
    └── rule_worker.py

Paso 4.2: Entorno Virtual y Dependencias
Comandos para crear la estructura y el entorno:
# Crear directorios
sudo mkdir -p /opt/auralis-rule-engine/src
# Crear el entorno virtual
sudo python3 -m venv /opt/auralis-rule-engine/venv
# Crear el archivo __init__.py para que 'src' sea un paquete
sudo touch /opt/auralis-rule-engine/src/__init__.py
# Activar el entorno virtual para instalar dependencias
source /opt/auralis-rule-engine/venv/bin/activate
# Instalar librerías
pip install paho-mqtt python-dotenv PyMySQL redis pytz
# Desactivar el entorno (opcional)
deactivate

Paso 4.3: Archivo de Configuración
Este archivo contiene todas las credenciales y parámetros de configuración.
Ubicación: /etc/default/auralis-rule-engine
Comando para crear/editar: sudo nano /etc/default/auralis-rule-engine

Paso 4.4: Código Fuente de los Servicios
Estos son los contenidos finales de los scripts en /opt/auralis-rule-engine/src/.

Paso 4.5: Permisos de Archivos
Comandos para asegurar que el usuario dsb586 pueda leer y ejecutar los archivos.
# Asignar propiedad de todos los archivos al usuario dsb586
sudo chown -R dsb586:dsb586 /opt/auralis-rule-engine

# Asignar permisos 755 (rwxr-xr-x) a los directorios
sudo find /opt/auralis-rule-engine -type d -exec chmod 755 {} \;

# Asignar permisos 644 (rw-r--r--) a los archivos no ejecutables
sudo find /opt/auralis-rule-engine -type f -name "*.py" -exec chmod 644 {} \;

# Asignar permisos de ejecución (744) a los scripts principales
sudo chmod 744 /opt/auralis-rule-engine/src/topic_manager.py
sudo chmod 744 /opt/auralis-rule-engine/src/rule_worker.py

Paso 4.6: Archivos de Servicio systemd

Servicio topic_manager:
Ubicación: /etc/systemd/system/auralis-rule-manager.service
Comando: sudo nano /etc/systemd/system/auralis-rule-manager.service

Servicio rule_worker (plantilla):
Ubicación: /etc/systemd/system/auralis-rule-worker@.service
Comando: sudo nano /etc/systemd/system/auralis-rule-worker@.service

5. Gestión del Servicio
Comandos para habilitar, iniciar, detener y revisar el estado de los servicios.
# Recargar systemd para que reconozca los archivos
sudo systemctl daemon-reload

# Habilitar (para que inicien con el servidor)
sudo systemctl enable auralis-rule-manager.service
sudo systemctl enable auralis-rule-worker@1.service
sudo systemctl enable auralis-rule-worker@2.service
sudo systemctl enable auralis-rule-worker@3.service
sudo systemctl enable auralis-rule-worker@4.service

# Iniciar los servicios
sudo systemctl start auralis-rule-manager.service
sudo systemctl start auralis-rule-worker@.service # Inicia todas las instancias habilitadas

# Detener los servicios
sudo systemctl stop auralis-rule-manager.service
sudo systemctl stop auralis-rule-worker@.service

# Reiniciar los servicios
sudo systemctl restart auralis-rule-manager.service
sudo systemctl restart auralis-rule-worker@.service

# Revisar el estado
sudo systemctl status auralis-rule-manager.service
sudo systemctl status auralis-rule-worker@*.service
