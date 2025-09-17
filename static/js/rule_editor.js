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
    const availableNodes = {
        sensor: {
            name: 'Fuente: Sensor',
            content: `<div><strong>Fuente: Sensor</strong><hr><div class="main-content"><label>Seleccione un sensor:</label><select df-source_sensor_id class="api-select" data-url="${API_SENSORS_URL}"></select></div></div>`,
            inputs: 0, outputs: 1,
        },
        static_value: {
            name: 'Fuente: Valor Estático',
            content: `<div><strong>Fuente: Valor Estático</strong><hr><div class="main-content"><label>Valor numérico:</label><input type="number" df-static_value step="any" value="0"></div></div>`,
            inputs: 0, outputs: 1,
        },
        policy: {
            name: 'Fuente: Política de Alerta',
            content: `<div><strong>Fuente: Política de Alerta</strong><hr><div class="main-content"><label>Seleccione una política:</label><select df-linked_policy_id class="api-select" data-url="${API_POLICIES_URL}"></select></div></div>`,
            inputs: 0, outputs: 1,
        },
        operator: {
            name: 'Condición: Comparar',
            content: `<div><strong>Condición: Comparar</strong><hr><div class="main-content"><label>Operador:</label><select df-operator><option value=">">Mayor que (&gt;)</option><option value="<">Menor que (&lt;)</option><option value="==">Igual a (==)</option></select></div></div>`,
            inputs: 2, outputs: 1,
        },
        logical_op: {
            name: 'Lógica: Unir Condiciones',
            content: `<div><strong>Lógica: Unir Condiciones</strong><hr><div class="main-content"><select df-logical_operator><option value="AND">Y (AND)</option><option value="OR">O (OR)</option></select></div></div>`,
            inputs: 2, outputs: 1,
        },
        rule_output: {
            name: 'Acción: Generar Alerta',
            content: `<div><strong>Acción: Generar Alerta</strong><hr><div class="main-content"><label>Nombre de la Regla:</label><input type="text" df-name placeholder="Ej: Sobrecalentamiento"><label>Severidad:</label><select df-severity><option value="INFO">Informativo</option><option value="WARNING">Advertencia</option><option value="CRITICAL">Crítico</option></select></div></div>`,
            inputs: 1, outputs: 0,
        }
    };

    // --- 3. FUNCIONES AUXILIARES Y DE CARGA ---

    async function populateSelect(selectElement) {
        const url = selectElement.dataset.url;
        try {
            const response = await fetch(url);
            const data = await response.json();
            selectElement.innerHTML = '<option value="">Seleccione...</option>';
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.name || item.__str__;
                selectElement.appendChild(option);
            });
        } catch (error) { console.error(`Error cargando datos para select desde ${url}:`, error); }
    }

    editor.on('nodeCreated', function(nodeId) {
        const nodeElement = document.querySelector(`#node-${nodeId}`);
        const selects = nodeElement.querySelectorAll('.api-select');
        selects.forEach(populateSelect);
    });

    async function populateRulesDropdown() {
        try {
            const response = await fetch(API_RULES_URL);
            const rules = await response.json();
            const dropdown = document.getElementById('rules-dropdown');
            dropdown.innerHTML = '<option value="">--- Cargar Regla Existente ---</option>';
            rules.forEach(rule => {
                const option = document.createElement('option');
                option.value = rule.id;
                option.textContent = `${rule.name} (ID: ${rule.id})`;
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
        
        // CORRECCIÓN: Usamos el método addNode directamente con el contenido HTML
        const sensorData = availableNodes.sensor;
        editor.addNode('sensor', sensorData.inputs, sensorData.outputs, 100, 200, 'sensor', {}, sensorData.content);
        
        const outputData = availableNodes.rule_output;
        editor.addNode('rule_output', outputData.inputs, outputData.outputs, 500, 200, 'rule_output', {}, outputData.content);
    }
    
    // --- 4. LÓGICA DE GUARDADO Y CARGA (PENDIENTE) ---

    async function loadRuleGraph(ruleId) {
        currentRuleId = ruleId;
        console.log(`Cargando regla con ID: ${ruleId}`);
        alert(`FUNCIONALIDAD PENDIENTE: Cargar y dibujar la regla ${ruleId}.`);
        editor.clear();
    }

    $('#btn-save-rule').on('click', function() {
        alert('FUNCIONALIDAD PENDIENTE: Guardar la regla actual.');
        const drawflowData = editor.export();
        console.log("Datos exportados de Drawflow:", drawflowData);
    });
    
    $('#btn-new-rule').on('click', createNewRuleTemplate);

    // --- 5. LÓGICA DEL MENÚ CONTEXTUAL (CORREGIDA Y COMPLETA) ---
    
    // Cerramos el menú si se hace clic en cualquier otro lado
    window.addEventListener("click", function() {
        const menu = document.getElementById("context-menu");
        if (menu.style.display === "block") {
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
                // Obtenemos la posición relativa al contenedor de Drawflow
                const pos_x = event.clientX * (editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)) - (editor.precanvas.getBoundingClientRect().x * (editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)));
                const pos_y = event.clientY * (editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)) - (editor.precanvas.getBoundingClientRect().y * (editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)));
                
                // Añadimos el nodo con su contenido HTML
                editor.addNode(key, nodeInfo.inputs, nodeInfo.outputs, pos_x, pos_y, key, {}, nodeInfo.content);
            });
            menu.appendChild(menuItem);
        });
    });

    // --- INICIO DE LA APLICACIÓN ---
    populateRulesDropdown();
});