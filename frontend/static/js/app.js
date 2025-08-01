// AI Test Automation Platform - Frontend JavaScript

class TestAutomationPlatform {
    constructor() {
        this.currentExecutionId = null;
        this.websocket = null;
        this.isConnected = false;
        this.init();
    }

    init() {
        console.log('🚀 Initializing AI Test Automation Platform...');
        this.bindEvents();
        this.checkSystemStatus();
        this.setupWebSocket();
        this.loadSavedData();
        this.validateForm();
    }

    bindEvents() {
        // Form validation on input
        const form = document.getElementById('testForm');
        if (form) {
            form.addEventListener('input', () => this.validateForm());
            form.addEventListener('change', () => this.validateForm());
        }

        // Button events
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const resumeBtn = document.getElementById('resumeBtn');
        const stopBtn = document.getElementById('stopBtn');

        if (startBtn) startBtn.addEventListener('click', () => this.startTest());
        if (pauseBtn) pauseBtn.addEventListener('click', () => this.pauseTest());
        if (resumeBtn) resumeBtn.addEventListener('click', () => this.resumeTest());
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopTest());

        // Auto-save form data
        if (form) {
            form.addEventListener('input', () => this.saveFormData());
        }
    }

    validateForm() {
        const instructions = this.getFieldValue('instructions');
        const url = this.getFieldValue('url');
        const username = this.getFieldValue('username');
        const password = this.getFieldValue('password');

        const isValid = instructions && url && username && password;
        const startBtn = document.getElementById('startBtn');

        if (startBtn) {
            startBtn.disabled = !isValid || this.currentExecutionId;
            
            if (!isValid) {
                startBtn.style.opacity = '0.6';
                startBtn.style.cursor = 'not-allowed';
                startBtn.title = 'Please fill all required fields';
            } else if (this.currentExecutionId) {
                startBtn.style.opacity = '0.6';
                startBtn.style.cursor = 'not-allowed';
                startBtn.title = 'Test execution in progress';
            } else {
                startBtn.style.opacity = '1';
                startBtn.style.cursor = 'pointer';
                startBtn.title = 'Start test execution';
            }
        }

        return isValid;
    }

    getFieldValue(fieldId) {
        const field = document.getElementById(fieldId);
        return field ? field.value.trim() : '';
    }

    async startTest() {
        console.log('🎯 Starting test execution...');
        
        if (!this.validateForm() || this.currentExecutionId) {
            console.log('❌ Cannot start test - validation failed or execution in progress');
            return;
        }

        const formData = {
            instructions: this.getFieldValue('instructions'),
            url: this.getFieldValue('url'),
            username: this.getFieldValue('username'),
            password: this.getFieldValue('password')
        };

        try {
            this.updateStatus('Starting test execution...', 'running');
            this.updateButtons('running');

            const response = await fetch('/api/test/start', {
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
            
            if (result.execution_id) {
                this.currentExecutionId = result.execution_id;
                this.addUpdate(`Test execution started with ID: ${result.execution_id}`, 'info');
                this.updateStatus('Test execution in progress...', 'running');
                console.log('✅ Test started successfully:', result);
            } else {
                throw new Error('No execution ID received');
            }

        } catch (error) {
            console.error('❌ Failed to start test:', error);
            this.addUpdate(`Failed to start test: ${error.message}`, 'error');
            this.updateStatus('Ready to start test execution', 'ready');
            this.updateButtons('ready');
            this.currentExecutionId = null;
        }
    }

    async pauseTest() {
        if (!this.currentExecutionId) return;

        try {
            const response = await fetch(`/api/test/${this.currentExecutionId}/pause`, {
                method: 'POST'
            });

            if (response.ok) {
                this.addUpdate('Test execution paused', 'warning');
                this.updateButtons('paused');
            }
        } catch (error) {
            console.error('Failed to pause test:', error);
            this.addUpdate(`Failed to pause test: ${error.message}`, 'error');
        }
    }

    async resumeTest() {
        if (!this.currentExecutionId) return;

        try {
            const response = await fetch(`/api/test/${this.currentExecutionId}/resume`, {
                method: 'POST'
            });

            if (response.ok) {
                this.addUpdate('Test execution resumed', 'info');
                this.updateButtons('running');
            }
        } catch (error) {
            console.error('Failed to resume test:', error);
            this.addUpdate(`Failed to resume test: ${error.message}`, 'error');
        }
    }

    async stopTest() {
        if (!this.currentExecutionId) return;

        try {
            const response = await fetch(`/api/test/${this.currentExecutionId}/stop`, {
                method: 'POST'
            });

            if (response.ok) {
                this.addUpdate('Test execution stopped', 'warning');
                this.updateStatus('Test execution stopped', 'ready');
                this.updateButtons('ready');
                this.currentExecutionId = null;
            }
        } catch (error) {
            console.error('Failed to stop test:', error);
            this.addUpdate(`Failed to stop test: ${error.message}`, 'error');
        }
    }

    updateStatus(text, status = 'ready') {
        const statusBadge = document.getElementById('executionStatus');
        const statusText = document.getElementById('executionText');

        if (statusBadge) {
            statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusBadge.className = `status-badge ${status}`;
        }

        if (statusText) {
            statusText.textContent = text;
        }
    }

    updateButtons(state) {
        const startBtn = document.getElementById('startBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        const resumeBtn = document.getElementById('resumeBtn');
        const stopBtn = document.getElementById('stopBtn');

        // Reset all buttons
        [startBtn, pauseBtn, resumeBtn, stopBtn].forEach(btn => {
            if (btn) btn.disabled = true;
        });

        switch (state) {
            case 'ready':
                if (startBtn) {
                    startBtn.disabled = !this.validateForm();
                    startBtn.textContent = ' Start Test';
                    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Test';
                }
                if (pauseBtn) pauseBtn.style.display = 'inline-flex';
                if (resumeBtn) resumeBtn.style.display = 'none';
                break;

            case 'running':
                if (pauseBtn) {
                    pauseBtn.disabled = false;
                    pauseBtn.style.display = 'inline-flex';
                }
                if (resumeBtn) resumeBtn.style.display = 'none';
                if (stopBtn) stopBtn.disabled = false;
                break;

            case 'paused':
                if (pauseBtn) pauseBtn.style.display = 'none';
                if (resumeBtn) {
                    resumeBtn.disabled = false;
                    resumeBtn.style.display = 'inline-flex';
                }
                if (stopBtn) stopBtn.disabled = false;
                break;
        }
    }

    addUpdate(message, type = 'info') {
        const container = document.getElementById('updatesContainer');
        if (!container) return;

        const updateItem = document.createElement('div');
        updateItem.className = `update-item ${type}`;

        const icon = this.getUpdateIcon(type);
        updateItem.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
        `;

        // Add to top of updates
        container.insertBefore(updateItem, container.firstChild);

        // Keep only last 10 updates
        while (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }

        // Auto-scroll to top
        container.scrollTop = 0;
    }

    getUpdateIcon(type) {
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle'
        };
        return icons[type] || icons.info;
    }

    async checkSystemStatus() {
        console.log('🔍 Checking system status...');
        
        // Check Backend
        try {
            const response = await fetch('/health');
            if (response.ok) {
                const data = await response.json();
                this.updateSystemStatus('backendStatus', 'ready', 'Ready');
                
                // Check Azure AI from health response
                if (data.azure_client_available) {
                    this.updateSystemStatus('azureStatus', 'ready', 'Ready');
                } else {
                    this.updateSystemStatus('azureStatus', 'error', 'Not Available');
                }
            } else {
                this.updateSystemStatus('backendStatus', 'error', 'Error');
                this.updateSystemStatus('azureStatus', 'error', 'Error');
            }
        } catch (error) {
            console.error('Backend health check failed:', error);
            this.updateSystemStatus('backendStatus', 'error', 'Disconnected');
            this.updateSystemStatus('azureStatus', 'error', 'Disconnected');
        }
    }

    updateSystemStatus(elementId, status, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.className = `status-indicator ${status}`;
            element.textContent = text;
        }
    }

    setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('🔌 WebSocket connected');
                this.isConnected = true;
                this.updateSystemStatus('websocketStatus', 'connected', 'Connected');
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.websocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;
                this.updateSystemStatus('websocketStatus', 'disconnected', 'Disconnected');
                
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.setupWebSocket(), 5000);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateSystemStatus('websocketStatus', 'error', 'Error');
            };

        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
            this.updateSystemStatus('websocketStatus', 'error', 'Failed');
        }
    }

    handleWebSocketMessage(data) {
        console.log('📨 WebSocket message:', data);

        if (data.type === 'status_update') {
            this.addUpdate(data.message, data.level || 'info');
            
            if (data.progress !== undefined) {
                this.updateProgress(data.progress);
            }

            if (data.status) {
                this.updateStatus(data.message, data.status);
                
                if (data.status === 'completed' || data.status === 'failed') {
                    this.updateButtons('ready');
                    this.currentExecutionId = null;
                }
            }
        } else if (data.type === 'progress_update') {
            // Handle progress updates from test execution
            this.addUpdate(data.step, 'info');
            this.updateProgress(data.progress);
            this.updateStatus(data.step, 'running');
        } else if (data.type === 'execution_complete') {
            // Handle test execution completion
            this.addUpdate('Test execution completed successfully!', 'success');
            this.updateProgress(100);
            this.updateStatus('Completed', 'completed');
            this.updateButtons('ready');
            this.currentExecutionId = null;
            
            // Show results if available
            if (data.results) {
                console.log('📊 Test Results:', data.results);
            }
        } else if (data.type === 'execution_failed') {
            // Handle test execution failure
            this.addUpdate(`Test execution failed: ${data.error}`, 'error');
            this.updateStatus('Failed', 'failed');
            this.updateButtons('ready');
            this.currentExecutionId = null;
        }
    }

    updateProgress(progress) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }

        if (progressText) {
            progressText.textContent = `${progress}%`;
        }
    }

    saveFormData() {
        const formData = {
            instructions: this.getFieldValue('instructions'),
            url: this.getFieldValue('url'),
            username: this.getFieldValue('username'),
            timestamp: new Date().toISOString()
        };

        try {
            localStorage.setItem('ai_test_automation_form_data', JSON.stringify(formData));
        } catch (error) {
            console.warn('Failed to save form data:', error);
        }
    }

    loadSavedData() {
        try {
            const savedData = localStorage.getItem('ai_test_automation_form_data');
            if (savedData) {
                const formData = JSON.parse(savedData);
                
                ['instructions', 'url', 'username'].forEach(fieldId => {
                    const field = document.getElementById(fieldId);
                    if (field && formData[fieldId]) {
                        field.value = formData[fieldId];
                    }
                });

                this.validateForm();
                console.log('✅ Form data loaded from localStorage');
            }
        } catch (error) {
            console.warn('Failed to load saved form data:', error);
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 AI Test Automation Platform starting...');
    new TestAutomationPlatform();
});
