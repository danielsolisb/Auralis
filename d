{% extends 'main/dashboard.html' %}
{% load static %}

{% block fixedbar %}
<!--Fixedbar-->
<!--~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~-->
<div class="page-fixedbar-container">
  <div class="page-fixedbar-content">
    <div class="nano">
      <div class="nano-content">
        <div class="pad-all">
          <span class="pad-ver text-main text-sm text-uppercase text-bold">SELECCIONE ESTACIÓN</span>
          <div class="form-group">
            <select id="station-selector" class="form-control">
              <option value="">Seleccione una estación</option>
              {% for station in stations %}
                <option value="{{ station.id }}">{{ station.name }}</option>
              {% endfor %}
            </select>
          </div>
          <!-- Botón para consultar sensores -->
          <div class="form-group">
            <button id="load-sensors-btn" class="btn btn-primary btn-block">Consultar Sensores</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<!--~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~-->
<!--End Fixedbar-->
{% endblock %}

{% block content %}
<!--Page content-->
<!--===================================================-->
<div id="page-content">
  <div class="row" id="sensors-container">
    <div class="text-center" id="no-station-selected">
      <h3 class="text-muted">Seleccione una estación para ver los sensores</h3>
    </div>
    <!-- Sensors will be loaded here dynamically -->
  </div>
</div>
<!--===================================================-->
<!--End page content-->
{% endblock %}

{% block script %}
<!-- Asegurarnos de que Chart.js y MQTT están cargados -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js" type="text/javascript"></script>

<script>
  // Store charts references
  const charts = {};
  // Store sensor data
  const sensorData = {};
  // MQTT client
  let mqttClient = null;
  let currentSubscriptions = [];
  
  $(document).ready(function() {
    console.log("Document ready, setting up event handlers");
    
    // Initialize MQTT client
    initMQTTClient();
    
    // Deshabilitar el botón inicialmente si no hay estación seleccionada
    if (!$('#station-selector').val()) {
      $('#load-sensors-btn').prop('disabled', true);
      console.log("Botón deshabilitado inicialmente");
    }
    
    // Habilitar/deshabilitar el botón según la selección
    $('#station-selector').change(function() {
      const stationId = $(this).val();
      console.log("Selector de estación cambiado, valor:", stationId);
      $('#load-sensors-btn').prop('disabled', !stationId);
    });
    
    // Manejar clic en el botón de consultar sensores
    $('#load-sensors-btn').click(function() {
      console.log("Botón de cargar sensores clickeado");
      const stationId = $('#station-selector').val();
      console.log("ID de estación del selector:", stationId);
      
      if (stationId) {
        console.log("Llamando a loadSensors con ID:", stationId);
        loadSensors(stationId);
      } else {
        console.log("No hay estación seleccionada, mostrando mensaje");
        $('#sensors-container').html('<div class="text-center" id="no-station-selected"><h3 class="text-muted">Seleccione una estación para ver los sensores</h3></div>');
        unsubscribeFromAllTopics();
      }
    });
  });
  
  function initMQTTClient() {
    // Generate a random client ID
    const clientId = "auralis_dashboard_" + Math.random().toString(16).substr(2, 8);
    
    console.log("Inicializando cliente MQTT con ID:", clientId);
    
    try {
      // Connect to MQTT broker
      mqttClient = new Paho.MQTT.Client(
        window.location.hostname, // Use the same hostname as the web server
        9001, // WebSocket port for MQTT
        clientId
      );
      
      // Set callback handlers
      mqttClient.onConnectionLost = onConnectionLost;
      mqttClient.onMessageArrived = onMessageArrived;
      
      // Connect
      mqttClient.connect({
        onSuccess: onConnect,
        onFailure: function(e) {
          console.error("Conexión MQTT fallida:", e);
          // No bloquear la funcionalidad principal si MQTT falla
          console.log("Continuando sin conexión MQTT. Los datos en tiempo real no estarán disponibles.");
        },
        useSSL: window.location.protocol === "https:",
        keepAliveInterval: 60
      });
    } catch (e) {
      console.error("Error inicializando cliente MQTT:", e);
      // No bloquear la funcionalidad principal si MQTT falla
      console.log("Continuando sin conexión MQTT. Los datos en tiempo real no estarán disponibles.");
    }
  }
  
  // Modificar la función subscribeToTopic para manejar el caso donde MQTT no está conectado
  function subscribeToTopic(topic) {
    if (mqttClient && mqttClient.isConnected && mqttClient.isConnected()) {
      mqttClient.subscribe(topic);
      currentSubscriptions.push(topic);
      console.log(`Suscrito a ${topic}`);
    } else {
      console.log(`No se pudo suscribir a ${topic} - Cliente MQTT no conectado`);
    }
  }
  
  function onConnect() {
    console.log("MQTT Conectado");
  }
  
  function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
      console.log("Conexión MQTT perdida: " + responseObject.errorMessage);
      // Try to reconnect after a delay
      setTimeout(initMQTTClient, 5000);
    }
  }
  
  function onMessageArrived(message) {
    const topic = message.destinationName;
    const payload = message.payloadString;
    
    // Parse the topic to get station and sensor
    const topicParts = topic.split('/');
    if (topicParts.length >= 2) {
      const stationName = topicParts[0];
      const sensorName = topicParts[1];
      const sensorId = `${stationName}-${sensorName}`;
      
      try {
        const value = parseFloat(payload);
        updateSensorData(sensorId, value);
      } catch (e) {
        console.error("Error analizando valor del sensor:", e);
      }
    }
  }
  
  function loadSensors(stationId) {
    // Unsubscribe from previous topics
    unsubscribeFromAllTopics();
    
    // Clear previous charts
    for (const chartId in charts) {
      if (charts[chartId]) {
        charts[chartId].destroy();
        delete charts[chartId]; // Eliminar la propiedad en lugar de reasignar el objeto
      }
    }
    
    // Limpiar datos de sensores sin reasignar el objeto
    for (const sensorId in sensorData) {
      delete sensorData[sensorId];
    }
    
    // Show loading indicator
    $('#sensors-container').html('<div class="text-center"><i class="fa fa-spinner fa-spin fa-3x"></i><p>Cargando sensores...</p></div>');
    
    console.log(`Obteniendo sensores para la estación ID: ${stationId}`);
    
    // Construir la URL completa para depuración
    const apiUrl = `/api/stations/${stationId}/sensors/`;
    console.log("URL de API:", apiUrl);
    console.log("URL completa:", window.location.origin + apiUrl);
    
    // Fetch sensors for the selected station
    $.ajax({
      url: apiUrl,
      method: 'GET',
      success: function(response) {
        console.log('Respuesta de API:', response);
        
        if (response.sensors && response.sensors.length > 0) {
          const stationName = response.station_name;
          let html = '';
          
          // Create a card for each sensor
          response.sensors.forEach(sensor => {
            console.log('Procesando sensor:', sensor);
            const sensorId = `${stationName}-${sensor.name}`;
            html += `
              <div class="col-md-6 col-lg-4">
                <div class="panel">
                  <div class="panel-heading">
                    <h3 class="panel-title">${sensor.name}</h3>
                  </div>
                  <div class="panel-body">
                    <div class="sensor-value text-center">
                      <h2 id="value-${sensorId}">--</h2>
                      <p>${sensor.unit || ''}</p>
                    </div>
                    <div class="sensor-chart">
                      <canvas id="chart-${sensorId}" height="200"></canvas>
                    </div>
                  </div>
                </div>
              </div>
            `;
            
            // Subscribe to the sensor's MQTT topic
            const topic = `${stationName}/${sensor.name}/`;
            subscribeToTopic(topic);
            
            // Initialize data for this sensor
            sensorData[sensorId] = {
              labels: Array(20).fill(''),
              values: Array(20).fill(null)
            };
          });
          
          $('#sensors-container').html(html);
          
          // Initialize charts
          response.sensors.forEach(sensor => {
            const sensorId = `${stationName}-${sensor.name}`;
            initChart(sensorId);
          });
        } else {
          console.log('No se encontraron sensores o array de sensores vacío');
          $('#sensors-container').html('<div class="text-center"><h3 class="text-muted">No hay sensores disponibles para esta estación</h3></div>');
        }
      },
      error: function(error) {
        console.error("Error cargando sensores:", error);
        console.error("Estado del error:", error.status);
        console.error("Texto del error:", error.statusText);
        console.error("Respuesta del error:", error.responseText);
        $('#sensors-container').html(`<div class="text-center"><h3 class="text-danger">Error al cargar los sensores</h3><p>Error ${error.status}: ${error.statusText || 'Error desconocido'}</p></div>`);
      }
    });
  }
  
  function initChart(sensorId) {
    try {
      const canvas = document.getElementById(`chart-${sensorId}`);
      if (!canvas) {
        console.error(`Canvas para el sensor ${sensorId} no encontrado`);
        return;
      }
      
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        console.error(`No se pudo obtener el contexto 2D para el sensor ${sensorId}`);
        return;
      }
      
      charts[sensorId] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: sensorData[sensorId].labels,
          datasets: [{
            label: 'Valor',
            data: sensorData[sensorId].values,
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderWidth: 2,
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: false
            }
          },
          animation: {
            duration: 500
          }
        }
      });
    } catch (error) {
      console.error(`Error al inicializar el gráfico para ${sensorId}:`, error);
    }
  }
  
  function updateSensorData(sensorId, value) {
    // Update the displayed value
    $(`#value-${sensorId}`).text(value.toFixed(2));
    
    // Update chart data
    if (sensorData[sensorId]) {
      // Add new data point
      const now = new Date();
      const timeStr = now.getHours() + ':' + now.getMinutes() + ':' + now.getSeconds();
      
      sensorData[sensorId].labels.push(timeStr);
      sensorData[sensorId].values.push(value);
      
      // Remove oldest data point if we have more than 20
      if (sensorData[sensorId].labels.length > 20) {
        sensorData[sensorId].labels.shift();
        sensorData[sensorId].values.shift();
      }
      
      // Update chart
      if (charts[sensorId]) {
        charts[sensorId].data.labels = sensorData[sensorId].labels;
        charts[sensorId].data.datasets[0].data = sensorData[sensorId].values;
        charts[sensorId].update();
      }
    }
  }
  
  function unsubscribeFromAllTopics() {
    if (mqttClient && mqttClient.isConnected()) {
      currentSubscriptions.forEach(topic => {
        mqttClient.unsubscribe(topic);
        console.log(`Desuscrito de ${topic}`);
      });
      currentSubscriptions = [];
    }
  }
</script>
{% endblock %}