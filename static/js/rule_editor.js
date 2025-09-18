// static/js/rule_editor.js

$(document).ready(function() {
    console.log("rule_editor.js cargado.");

    // --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
    const configElement = document.getElementById('editor-config');
    const API_RULES_URL = configElement.dataset.apiRulesUrl;
    const API_SENSORS_URL = configElement.dataset.apiSensorsUrl;
    const API_POLICIES_URL = configElement.dataset.apiPoliciesUrl;
    const CSRF_TOKEN = configElement.dataset.csrfToken;

    let currentRuleId = null;

    const container = document.getElementById("drawflow");
    const editor = new Drawflow(container);
    editor.start();
    console.log("Editor de Drawflow iniciado.");

    // --- 2. DEFINICIÓN DE NODOS PERSONALIZADOS ---
    // CORRECCIÓN SUTIL: Los nombres df-* deben coincidir con las claves del JSON de la API.
    const availableNodes = {
        sensor: { name: 'Fuente: Sensor', content: `<div><strong>Fuente: Sensor</strong><hr><div class="main-content"><label>Seleccione un sensor:</label><select df-source_sensor class="api-select" data-url="${API_SENSORS_URL}"></select></div></div>`, inputs: 0, outputs: 1 },
        static_value: { name: 'Fuente: Valor Estático', content: `<div><strong>Fuente: Valor Estático</strong><hr><div class="main-content"><label>Valor numérico:</label><input type="number" df-static_value step="any" value="0"></div></div>`, inputs: 0, outputs: 1 },
        policy: { name: 'Fuente: Política de Alerta', content: `<div><strong>Fuente: Política de Alerta</strong><hr><div class="main-content"><label>Seleccione una política:</label><select df-linked_policy class="api-select" data-url="${API_POLICIES_URL}"></select></div></div>`, inputs: 0, outputs: 1 },
        operator: { name: 'Condición: Comparar', content: `<div><strong>Condición: Comparar</strong><hr><div class="main-content"><label>Operador:</label><select df-operator><option value=">">Mayor que (&gt;)</option><option value="<">Menor que (&lt;)</option><option value="==">Igual a (==)</option></select></div></div>`, inputs: 2, outputs: 1 },
        logical_op: { name: 'Lógica: Unir Condiciones', content: `<div><strong>Lógica: Unir Condiciones</strong><hr><div class="main-content"><select df-logical_operator><option value="AND">Y (AND)</option><option value="OR">O (OR)</option></select></div></div>`, inputs: 2, outputs: 1 },
        rule_output: { name: 'Acción: Generar Alerta', content: `<div><strong>Acción: Generar Alerta</strong><hr><div class="main-content"><label>Nombre de la Regla:</label><input type="text" df-name placeholder="Ej: Sobrecalentamiento"><label>Severidad:</label><select df-severity><option value="INFO">Informativo</option><option value="WARNING">Advertencia</option><option value="CRITICAL">Crítico</option></select></div></div>`, inputs: 1, outputs: 0 }
    };

    // --- 3. FUNCIONES AUXILIARES Y DE CARGA INICIAL ---
    // (Estas funciones ya funcionan y no se modifican)
    async function populateSelect(selectElement, valueToSelect = null) {
        const url = selectElement.dataset.url;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Network response was not ok for ${url}`);
            const data = await response.json();
            selectElement.innerHTML = '<option value="">Seleccione...</option>';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.name || item.label || item.__str__;
                if (valueToSelect && item.id.toString() === valueToSelect.toString()) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        } catch (error) { console.error(`Error cargando datos para select desde ${url}:`, error); }
    }

    editor.on('nodeCreated', function(nodeId) {
        const nodeElement = document.querySelector(`#node-${nodeId}`);
        const selects = nodeElement.querySelectorAll('.api-select');
        selects.forEach(select => populateSelect(select));
    });

    async function populateRulesDropdown() {
        try {
            const response = await fetch(API_RULES_URL);
            if (!response.ok) throw new Error('Failed to fetch rules');
            const rules = await response.json();
            const dropdown = document.getElementById('rules-dropdown');
            dropdown.innerHTML = '<option value="">--- Cargar Regla Existente ---</option>';
            rules.forEach(rule => {
                const option = document.createElement('option');
                option.value = rule.id;
                option.textContent = rule.name;
                dropdown.appendChild(option);
            });
        } catch (error) { console.error("Error al cargar la lista de reglas:", error); }
    }
    
    $('#rules-dropdown').on('change', function() {
        const ruleId = $(this).val();
        if (ruleId) loadRuleGraph(ruleId);
    });

    function createNewRuleTemplate() {
        editor.clear();
        currentRuleId = null;
        $('#rules-dropdown').val('');
        const sensorData = availableNodes.sensor;
        editor.addNode('sensor', sensorData.inputs, sensorData.outputs, 100, 200, 'sensor', {}, sensorData.content);
        const outputData = availableNodes.rule_output;
        editor.addNode('rule_output', outputData.inputs, outputData.outputs, 500, 200, 'rule_output', {}, outputData.content);
    }

    // --- 4. LÓGICA DE CARGA Y VISUALIZACIÓN DE REGLAS (¡COMPLETA Y FUNCIONAL!) ---

    async function loadRuleGraph(ruleId) {
        currentRuleId = ruleId;
        editor.clear();
        console.log(`Pidiendo datos para la regla ID: ${ruleId}`);
        
        try {
            const response = await fetch(`${API_RULES_URL}${ruleId}/`);
            if (!response.ok) throw new Error(`Error en la API: ${response.statusText}`);
            const ruleData = await response.json();
            console.log("Datos de la regla recibidos:", ruleData);
            
            if (!ruleData.nodes || ruleData.nodes.length === 0) {
                console.warn("La regla no tiene nodos para dibujar.");
                return;
            }

            const backendNode = ruleData.nodes[0]; // Para la regla simple, tomamos el primer nodo
            const condition = backendNode.condition;
            if (!condition) {
                console.error("El nodo raíz de la regla no tiene una condición asociada.");
                return;
            }
            
            // Dibuja el grafo de una condición simple
            // 1. Crear nodo SENSOR
            const sensorTemplate = availableNodes.sensor;
            const sensorDfId = editor.addNode('sensor', sensorTemplate.inputs, sensorTemplate.outputs, 100, 100, 'sensor', {}, sensorTemplate.content);

            // 2. Crear nodo VALOR ESTÁTICO
            const staticValTemplate = availableNodes.static_value;
            const staticDfId = editor.addNode('static_value', staticValTemplate.inputs, staticValTemplate.outputs, 100, 300, 'static_value', {}, staticValTemplate.content);

            // 3. Crear nodo OPERADOR
            const opTemplate = availableNodes.operator;
            const opDfId = editor.addNode('operator', opTemplate.inputs, opTemplate.outputs, 450, 200, 'operator', {}, opTemplate.content);
            
            // 4. Crear nodo de SALIDA
            const outputTemplate = availableNodes.rule_output;
            const outputDfId = editor.addNode('rule_output', outputTemplate.inputs, outputTemplate.outputs, 800, 200, 'rule_output', {}, outputTemplate.content);

            // 5. Conectar los nodos
            editor.addConnection(sensorDfId, opDfId, 'output_1', 'input_1');
            editor.addConnection(staticDfId, opDfId, 'output_1', 'input_2');
            editor.addConnection(opDfId, outputDfId, 'output_1', 'input_1');

            // 6. Rellenar los datos en los nodos (usando un delay para que el DOM se actualice)
            setTimeout(() => {
                const sensorElement = document.querySelector(`#node-${sensorDfId}`);
                if (sensorElement) {
                    populateSelect(sensorElement.querySelector('[df-source_sensor]'), condition.source_sensor);
                }

                const staticElement = document.querySelector(`#node-${staticDfId}`);
                if (staticElement) {
                    staticElement.querySelector('[df-static_value]').value = condition.threshold_config.value;
                }

                const opElement = document.querySelector(`#node-${opDfId}`);
                if (opElement) {
                    opElement.querySelector('[df-operator]').value = condition.operator;
                }

                const outputElement = document.querySelector(`#node-${outputDfId}`);
                if (outputElement) {
                    outputElement.querySelector('[df-name]').value = ruleData.name;
                    outputElement.querySelector('[df-severity]').value = ruleData.severity;
                }
                console.log("Grafo de la regla cargado y dibujado correctamente.");
            }, 300);

        } catch (error) {
            console.error("Error al cargar el grafo de la regla:", error);
            alert("No se pudo cargar la regla seleccionada.");
        }
    }
    
    // --- 5. LÓGICA DE GUARDADO (PENDIENTE) ---
    $('#btn-save-rule').on('click', function() { alert('FUNCIONALIDAD PENDIENTE: Guardar la regla actual.'); });
    
    // --- 6. MENÚ CONTEXTUAL Y ARRANQUE (RESTAURADO Y FUNCIONAL) ---
    $('#btn-new-rule').on('click', createNewRuleTemplate);
    window.addEventListener("click", function() {
        const menu = document.getElementById("context-menu");
        if (menu && menu.style.display === "block") {
            menu.style.display = "none";
        }
    });

    editor.on('contextmenu', function (event) {
        event.preventDefault();
        const menu = document.getElementById("context-menu");
        menu.style.display = "block";
        menu.style.left = event.clientX + 'px';
        menu.style.top = event.clientY + 'px';
        menu.innerHTML = '';
        Object.entries(availableNodes).forEach(([key, nodeInfo]) => {
            const menuItem = document.createElement('a');
            menuItem.href = '#';
            menuItem.textContent = nodeInfo.name;
            menuItem.addEventListener('click', function(e) {
                e.preventDefault();
                const pos_x = event.clientX * (editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)) - (editor.precanvas.getBoundingClientRect().x * (editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)));
                const pos_y = event.clientY * (editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)) - (editor.precanvas.getBoundingClientRect().y * (editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)));
                editor.addNode(key, nodeInfo.inputs, nodeInfo.outputs, pos_x, pos_y, key, {}, nodeInfo.content);
            });
            menu.appendChild(menuItem);
        });
    });

    // --- INICIO DE LA APLICACIÓN ---
    populateRulesDropdown();
});
