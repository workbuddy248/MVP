// E2E Testing Agent Frontend JavaScript

class TestingAgent {
    constructor() {
        this.currentExecutionId = null;
        this.websocket = null;
        this.workflows = [];
        this.currentWorkflow = null;
        this.workflowMode = true;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupWebSocket();
        this.loadWorkflows();
        this.loadSavedData();
    }

    bindEvents() {
        // Form submission
        document.getElementById('executeBtn').addEventListener('click', () => this.executeTest());
        
        // Control buttons
        document.getElementById('pauseBtn').addEventListener('click', () => this.pauseExecution());
        document.getElementById('resumeBtn').addEventListener('click', () => this.resumeExecution());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopExecution());
        
        // Mode toggle
        document.addEventListener('change', (e) => {
            if (e.target.name === 'testMode') {
                this.switchMode(e.target.value);
            }
        });
        
        // Workflow selection
        document.getElementById('workflowSelect').addEventListener('change', (e) => {
            this.loadWorkflowTemplate(e.target.value);
        });
        
        // Form validation
        document.getElementById('testForm').addEventListener('input', () => this.validateForm());
        
        // Auto-save form data
        document.getElementById('testForm').addEventListener('input', () => this.saveFormData());
        
        // Initial form validation
        this.validateForm();
    }

    async loadWorkflows() {
        try {
            const response = await fetch('/api/workflow-templates');
            if (response.ok) {
                const data = await response.json();
                this.workflows = data.templates || [];
                this.populateWorkflowDropdown();
            } else {
                console.warn('Failed to load workflows:', response.statusText);
                this.showMessage('Failed to load workflow templates', 'warning');
            }
        } catch (error) {
            console.error('Error loading workflows:', error);
            this.showMessage('Error loading workflow templates', 'error');
        }
    }

    populateWorkflowDropdown() {
        const select = document.getElementById('workflowSelect');
        
        // Clear existing options except the first one
        select.innerHTML = '<option value="">-- Select a workflow --</option>';
        
        // Add workflow options
        this.workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.workflow_id;
            option.textContent = `${workflow.workflow_name} - ${workflow.description}`;
            select.appendChild(option);
        });
    }

    switchMode(mode) {
        this.workflowMode = mode === 'workflow';
        
        const workflowSection = document.getElementById('workflowSection');
        const freeformSection = document.getElementById('freeformSection');
        
        if (this.workflowMode) {
            workflowSection.style.display = 'block';
            freeformSection.style.display = 'none';
            document.getElementById('clusterIpLabel').textContent = 'Target URL';
            document.getElementById('baseUrlLabel').textContent = 'Base URL';
            document.getElementById('clusterIp').placeholder = 'https://catalyst.cisco.com';
        } else {
            workflowSection.style.display = 'none';
            freeformSection.style.display = 'block';
            document.getElementById('clusterIpLabel').textContent = 'Cluster IP';
            document.getElementById('baseUrlLabel').textContent = 'Base URL';
            document.getElementById('clusterIp').placeholder = '192.168.1.100';
        }
        
        this.validateForm();
    }

    async loadWorkflowTemplate(workflowId) {
        if (!workflowId) {
            this.clearTemplateFields();
            return;
        }

        try {
            const response = await fetch(`/api/workflow-template/${workflowId}`);
            if (response.ok) {
                this.currentWorkflow = await response.json();
                this.renderTemplateFields();
                this.renderDependencyQuestions();
                this.validateForm();
            } else {
                console.error('Failed to load workflow template:', response.statusText);
                this.showMessage('Failed to load workflow template', 'error');
            }
        } catch (error) {
            console.error('Error loading workflow template:', error);
            this.showMessage('Error loading workflow template', 'error');
        }
    }

    clearTemplateFields() {
        const container = document.getElementById('templateFields');
        container.innerHTML = '';
        container.classList.add('empty');
        
        const dependencyContainer = document.getElementById('dependencyQuestions');
        dependencyContainer.style.display = 'none';
        dependencyContainer.innerHTML = '<h3><i class="fas fa-question-circle"></i> Workflow Dependencies</h3>';
    }

    renderTemplateFields() {
        const container = document.getElementById('templateFields');
        container.innerHTML = '';
        container.classList.remove('empty');
        
        if (!this.currentWorkflow || !this.currentWorkflow.fields) {
            return;
        }

        this.currentWorkflow.fields.forEach(field => {
            const fieldElement = this.createTemplateField(field);
            container.appendChild(fieldElement);
        });
    }

    createTemplateField(field) {
        const div = document.createElement('div');
        div.className = 'template-field';
        
        const label = document.createElement('label');
        label.setAttribute('for', `template_${field.field_id}`);
        label.innerHTML = `<i class="fas fa-${this.getFieldIcon(field.type)}"></i> ${field.label}`;
        if (field.required) {
            label.innerHTML += ' <span class="required">*</span>';
        }
        
        let input;
        switch (field.type) {
            case 'textarea':
                input = document.createElement('textarea');
                input.rows = 3;
                break;
            case 'select':
            case 'dropdown':
                input = document.createElement('select');
                if (field.options) {
                    field.options.forEach(option => {
                        const optionElement = document.createElement('option');
                        optionElement.value = option.value || option;
                        optionElement.textContent = option.label || option;
                        input.appendChild(optionElement);
                    });
                }
                break;
            case 'checkbox':
            case 'boolean':
                const checkboxContainer = document.createElement('div');
                checkboxContainer.className = 'checkbox-label';
                
                input = document.createElement('input');
                input.type = 'checkbox';
                input.checked = field.default_value === true || field.default_value === 'true';
                
                const customCheckbox = document.createElement('span');
                customCheckbox.className = 'checkbox-custom';
                
                const checkboxLabel = document.createElement('span');
                checkboxLabel.textContent = field.description || field.label;
                
                checkboxContainer.appendChild(input);
                checkboxContainer.appendChild(customCheckbox);
                checkboxContainer.appendChild(checkboxLabel);
                
                div.appendChild(label);
                div.appendChild(checkboxContainer);
                
                input.id = `template_${field.field_id}`;
                input.name = `template_${field.field_id}`;
                input.setAttribute('data-field-id', field.field_id);
                
                return div;
            default:
                input = document.createElement('input');
                input.type = field.type === 'password' ? 'password' : 
                           field.type === 'number' ? 'number' : 
                           field.type === 'url' ? 'url' : 'text';
        }
        
        input.id = `template_${field.field_id}`;
        input.name = `template_${field.field_id}`;
        input.placeholder = field.placeholder || field.description || '';
        input.value = field.default_value || '';
        input.required = field.required;
        input.setAttribute('data-field-id', field.field_id);
        
        // Add validation attributes
        if (field.validation) {
            if (field.validation.min_length) input.minLength = field.validation.min_length;
            if (field.validation.max_length) input.maxLength = field.validation.max_length;
            if (field.validation.min) input.min = field.validation.min;
            if (field.validation.max) input.max = field.validation.max;
            if (field.validation.pattern) input.pattern = field.validation.pattern;
        }
        
        div.appendChild(label);
        div.appendChild(input);
        
        if (field.description) {
            const helpText = document.createElement('div');
            helpText.className = 'help-text';
            helpText.innerHTML = `<i class="fas fa-info-circle"></i> ${field.description}`;
            div.appendChild(helpText);
        }
        
        return div;
    }

    getFieldIcon(type) {
        const icons = {
            'text': 'font',
            'textarea': 'align-left',
            'password': 'lock',
            'number': 'hashtag',
            'url': 'link',
            'select': 'list',
            'dropdown': 'chevron-down',
            'checkbox': 'check-square',
            'boolean': 'toggle-on'
        };
        return icons[type] || 'edit';
    }

    renderDependencyQuestions() {
        const container = document.getElementById('dependencyQuestions');
        
        if (!this.currentWorkflow || !this.currentWorkflow.dependency_questions || this.currentWorkflow.dependency_questions.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        
        // Clear existing content except title
        const title = container.querySelector('h3');
        container.innerHTML = '';
        container.appendChild(title);
        
        this.currentWorkflow.dependency_questions.forEach(question => {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'dependency-question';
            
            const label = document.createElement('label');
            label.textContent = question.question;
            
            let input;
            if (question.type === 'boolean') {
                const checkboxContainer = document.createElement('div');
                checkboxContainer.className = 'checkbox-label';
                
                input = document.createElement('input');
                input.type = 'checkbox';
                input.checked = question.default || false;
                
                const customCheckbox = document.createElement('span');
                customCheckbox.className = 'checkbox-custom';
                
                const checkboxLabel = document.createElement('span');
                checkboxLabel.textContent = 'Yes';
                
                checkboxContainer.appendChild(input);
                checkboxContainer.appendChild(customCheckbox);
                checkboxContainer.appendChild(checkboxLabel);
                
                questionDiv.appendChild(label);
                questionDiv.appendChild(checkboxContainer);
            } else {
                input = document.createElement('input');
                input.type = 'text';
                input.value = question.default || '';
                
                questionDiv.appendChild(label);
                questionDiv.appendChild(input);
            }
            
            input.id = `dependency_${question.field}`;
            input.name = `dependency_${question.field}`;
            input.setAttribute('data-dependency-field', question.field);
            
            container.appendChild(questionDiv);
        });
    }

    validateForm() {
        if (this.workflowMode) {
            return this.validateWorkflowForm();
        } else {
            return this.validateFreeformForm();
        }
    }

    validateWorkflowForm() {
        const workflowSelect = document.getElementById('workflowSelect').value;
        const clusterIp = document.getElementById('clusterIp').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        let templateFieldsValid = true;
        if (this.currentWorkflow && this.currentWorkflow.fields) {
            templateFieldsValid = this.currentWorkflow.fields.every(field => {
                if (!field.required) return true;
                const input = document.getElementById(`template_${field.field_id}`);
                return input && input.value && input.value.trim();
            });
        }
        
        const isValid = workflowSelect && clusterIp && username && password && templateFieldsValid;
        
        document.getElementById('executeBtn').disabled = !isValid || this.currentExecutionId;
        
        return isValid;
    }

    validateFreeformForm() {
        const instructions = document.getElementById('instructions').value.trim();
        const clusterIp = document.getElementById('clusterIp').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        const isValid = instructions && clusterIp && username && password;
        
        document.getElementById('executeBtn').disabled = !isValid || this.currentExecutionId;
        
        return isValid;
    }

    saveFormData() {
        const formData = {
            instructions: document.getElementById('instructions').value,
            clusterIp: document.getElementById('clusterIp').value,
            baseUrl: document.getElementById('baseUrl').value,
            username: document.getElementById('username').value,
            headless: document.getElementById('headless').checked
        };
        
        localStorage.setItem('e2e_agent_form_data', JSON.stringify(formData));
    }

    loadSavedData() {
        const savedData = localStorage.getItem('e2e_agent_form_data');
        if (savedData) {
            try {
                const formData = JSON.parse(savedData);
                
                document.getElementById('instructions').value = formData.instructions || '';
                document.getElementById('clusterIp').value = formData.clusterIp || '';
                document.getElementById('baseUrl').value = formData.baseUrl || '';
                document.getElementById('username').value = formData.username || '';
                document.getElementById('headless').checked = formData.headless !== false;
                
                this.validateForm();
            } catch (e) {
                console.warn('Failed to load saved form data:', e);
            }
        }
    }

    async executeTest() {
        if (!this.validateForm()) {
            this.showMessage('Please fill in all required fields', 'error');
            return;
        }

        this.showLoading(true);

        try {
            if (this.workflowMode) {
                await this.executeWorkflow();
            } else {
                await this.executeFreeform();
            }
        } catch (error) {
            console.error('Error executing test:', error);
            this.showMessage(`Failed to start test execution: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async executeWorkflow() {
        const workflowId = document.getElementById('workflowSelect').value;
        
        // Collect template field values
        const fieldValues = {};
        if (this.currentWorkflow && this.currentWorkflow.fields) {
            this.currentWorkflow.fields.forEach(field => {
                const input = document.getElementById(`template_${field.field_id}`);
                if (input) {
                    if (field.type === 'checkbox' || field.type === 'boolean') {
                        fieldValues[field.field_id] = input.checked;
                    } else {
                        fieldValues[field.field_id] = input.value;
                    }
                }
            });
        }
        
        // Add global fields
        fieldValues.target_url = document.getElementById('clusterIp').value.trim();
        fieldValues.username = document.getElementById('username').value.trim();
        fieldValues.password = document.getElementById('password').value;
        if (document.getElementById('baseUrl').value.trim()) {
            fieldValues.base_url = document.getElementById('baseUrl').value.trim();
        }
        
        // Collect dependency responses
        const dependencyResponses = {};
        if (this.currentWorkflow && this.currentWorkflow.dependency_questions) {
            this.currentWorkflow.dependency_questions.forEach(question => {
                const input = document.getElementById(`dependency_${question.field}`);
                if (input) {
                    if (question.type === 'boolean') {
                        dependencyResponses[question.field] = input.checked;
                    } else {
                        dependencyResponses[question.field] = input.value;
                    }
                }
            });
        }

        const requestData = {
            template_id: workflowId,
            field_values: fieldValues,
            execution_options: {
                dependency_responses: dependencyResponses,
                headless: document.getElementById('headless').checked
            }
        };

        const response = await fetch('/api/submit-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        this.currentExecutionId = result.execution_id;
        
        this.setupWebSocketForExecution(this.currentExecutionId);
        this.updateUI('running');
        this.showStatusSection(true);
        
        document.getElementById('executionId').textContent = this.currentExecutionId;
        
        this.showMessage('Workflow execution started successfully!', 'success');
    }

    async executeFreeform() {
        const formData = {
            instructions: document.getElementById('instructions').value.trim(),
            cluster_ip: document.getElementById('clusterIp').value.trim(),
            base_url: document.getElementById('baseUrl').value.trim() || null,
            username: document.getElementById('username').value.trim(),
            password: document.getElementById('password').value,
            headless: document.getElementById('headless').checked
        };

        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        this.currentExecutionId = result.execution_id;
        
        this.setupWebSocketForExecution(this.currentExecutionId);
        this.updateUI('running');
        this.showStatusSection(true);
        
        document.getElementById('executionId').textContent = this.currentExecutionId;
        
        this.showMessage('Test execution started successfully!', 'success');
    }

    async pauseExecution() {
        if (!this.currentExecutionId) return;

        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    execution_id: this.currentExecutionId,
                    action: 'pause'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.updateUI('paused');
            this.showMessage('Test execution paused', 'info');
            
        } catch (error) {
            console.error('Error pausing execution:', error);
            this.showMessage(`Failed to pause execution: ${error.message}`, 'error');
        }
    }

    async resumeExecution() {
        if (!this.currentExecutionId) return;

        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    execution_id: this.currentExecutionId,
                    action: 'resume'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.updateUI('running');
            this.showMessage('Test execution resumed', 'success');
            
        } catch (error) {
            console.error('Error resuming execution:', error);
            this.showMessage(`Failed to resume execution: ${error.message}`, 'error');
        }
    }

    async stopExecution() {
        if (!this.currentExecutionId) return;

        if (!confirm('Are you sure you want to stop the current execution?')) {
            return;
        }

        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    execution_id: this.currentExecutionId,
                    action: 'stop'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.updateUI('stopped');
            this.showMessage('Test execution stopped', 'info');
            
        } catch (error) {
            console.error('Error stopping execution:', error);
            this.showMessage(`Failed to stop execution: ${error.message}`, 'error');
        }
    }

    setupWebSocket() {
        // General WebSocket setup if needed
    }

    setupWebSocketForExecution(executionId) {
        if (this.websocket) {
            this.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${executionId}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected for execution:', executionId);
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'status_update') {
                    this.handleStatusUpdate(data);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleStatusUpdate(data) {
        const status = data.status;
        const progress = data.progress;
        const currentStep = data.current_step;
        
        // Update progress bar
        document.getElementById('progressFill').style.width = `${progress}%`;
        document.getElementById('progressPercent').textContent = `${progress}%`;
        document.getElementById('currentStep').textContent = currentStep;
        
        // Update status badge
        this.updateStatusBadge(status);
        
        // Update UI based on status
        this.updateUI(status);
        
        // If execution is complete, fetch results
        if (status === 'completed' || status === 'failed') {
            this.currentExecutionId = null;
            this.fetchExecutionResults(data.execution_id);
        }
    }

    updateStatusBadge(status) {
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');
        
        // Remove all status classes
        statusBadge.className = 'status-badge';
        
        // Add appropriate class and update text
        switch (status) {
            case 'initializing':
                statusBadge.classList.add('initializing');
                statusText.innerHTML = '<i class="fas fa-clock"></i> Initializing...';
                break;
            case 'running':
                statusBadge.classList.add('running');
                statusText.innerHTML = '<i class="fas fa-play"></i> Running';
                break;
            case 'paused':
                statusBadge.classList.add('paused');
                statusText.innerHTML = '<i class="fas fa-pause"></i> Paused';
                break;
            case 'completed':
                statusBadge.classList.add('completed');
                statusText.innerHTML = '<i class="fas fa-check"></i> Completed';
                break;
            case 'failed':
                statusBadge.classList.add('failed');
                statusText.innerHTML = '<i class="fas fa-times"></i> Failed';
                break;
            case 'stopped':
                statusBadge.classList.add('failed');
                statusText.innerHTML = '<i class="fas fa-stop"></i> Stopped';
                break;
        }
    }

    updateUI(status) {
        const executeBtn = document.getElementById('executeBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const resumeBtn = document.getElementById('resumeBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        // Reset all buttons
        executeBtn.disabled = true;
        pauseBtn.disabled = true;
        pauseBtn.style.display = 'inline-flex';
        resumeBtn.disabled = true;
        resumeBtn.style.display = 'none';
        stopBtn.disabled = true;
        
        switch (status) {
            case 'running':
                pauseBtn.disabled = false;
                stopBtn.disabled = false;
                break;
            case 'paused':
                resumeBtn.disabled = false;
                resumeBtn.style.display = 'inline-flex';
                pauseBtn.style.display = 'none';
                stopBtn.disabled = false;
                break;
            case 'completed':
            case 'failed':
            case 'stopped':
                executeBtn.disabled = false;
                this.currentExecutionId = null;
                if (this.websocket) {
                    this.websocket.close();
                    this.websocket = null;
                }
                break;
        }
    }

    async fetchExecutionResults(executionId) {
        try {
            const response = await fetch(`/api/status/${executionId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.results) {
                this.displayResults(data.results);
            }
            
        } catch (error) {
            console.error('Error fetching results:', error);
            this.showMessage(`Failed to fetch execution results: ${error.message}`, 'error');
        }
    }

    displayResults(results) {
        const resultsPanel = document.getElementById('resultsPanel');
        const resultsSection = document.getElementById('resultsSection');
        
        // Clear previous results
        resultsPanel.innerHTML = '';
        
        // Display overall status
        const overallStatus = results.status || 'unknown';
        const statusClass = overallStatus === 'completed' ? 'result-success' : 'result-error';
        const statusIcon = overallStatus === 'completed' ? 'fa-check-circle' : 'fa-times-circle';
        
        const overallDiv = document.createElement('div');
        overallDiv.className = `result-item ${statusClass}`;
        overallDiv.innerHTML = `
            <div class="result-header">
                <i class="fas ${statusIcon}"></i>
                Overall Status: ${overallStatus.toUpperCase()}
            </div>
        `;
        resultsPanel.appendChild(overallDiv);
        
        // Display agent results
        if (results.agent_results) {
            const agentDiv = document.createElement('div');
            agentDiv.innerHTML = '<h3 style="margin-bottom: 15px;"><i class="fas fa-robot"></i> Agent Results</h3>';
            
            for (const [agentName, agentResult] of Object.entries(results.agent_results)) {
                const agentStatusClass = agentResult.success ? 'result-success' : 'result-error';
                const agentIcon = agentResult.success ? 'fa-check' : 'fa-times';
                
                const agentItemDiv = document.createElement('div');
                agentItemDiv.className = `result-item ${agentStatusClass}`;
                agentItemDiv.innerHTML = `
                    <div class="result-header">
                        <i class="fas ${agentIcon}"></i>
                        ${agentName.replace('_', ' ').toUpperCase()}
                    </div>
                    ${agentResult.error ? `<div class="result-content">${agentResult.error}</div>` : ''}
                `;
                agentDiv.appendChild(agentItemDiv);
            }
            
            resultsPanel.appendChild(agentDiv);
        }
        
        // Display test results
        if (results.test_results) {
            const testDiv = document.createElement('div');
            testDiv.innerHTML = '<h3 style="margin-bottom: 15px; margin-top: 25px;"><i class="fas fa-vial"></i> Test Results</h3>';
            
            const testResults = results.test_results;
            if (testResults.summary) {
                const summary = testResults.summary;
                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'result-item';
                summaryDiv.innerHTML = `
                    <div class="result-header">
                        <i class="fas fa-chart-bar"></i>
                        Test Summary
                    </div>
                    <div class="result-content">
                        <p><strong>Total Steps:</strong> ${summary.total_steps}</p>
                        <p><strong>Passed:</strong> <span style="color: var(--success-color);">${summary.passed}</span></p>
                        <p><strong>Failed:</strong> <span style="color: var(--danger-color);">${summary.failed}</span></p>
                        <p><strong>Success Rate:</strong> ${summary.success_rate}%</p>
                    </div>
                `;
                testDiv.appendChild(summaryDiv);
            }
            
            resultsPanel.appendChild(testDiv);
        }
        
        // Display error if present
        if (results.error) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'result-item result-error';
            errorDiv.innerHTML = `
                <div class="result-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    Error Details
                </div>
                <div class="result-content">
                    ${results.error}
                </div>
            `;
            resultsPanel.appendChild(errorDiv);
        }
        
        // Show results section
        resultsSection.style.display = 'block';
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    showStatusSection(show) {
        const statusSection = document.getElementById('statusSection');
        statusSection.style.display = show ? 'block' : 'none';
    }

    showLoading(show) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }

    showMessage(message, type = 'info') {
        const messageContainer = document.getElementById('messageContainer');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const icon = type === 'success' ? 'fa-check-circle' : 
                     type === 'error' ? 'fa-times-circle' : 'fa-info-circle';
        
        messageDiv.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;
        
        messageContainer.appendChild(messageDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
        
        // Remove on click
        messageDiv.addEventListener('click', () => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TestingAgent();
});
