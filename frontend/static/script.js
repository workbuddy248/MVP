// AI Test Automation Platform - Frontend JavaScript

class TestAutomationApp {
    constructor() {
        this.ws = null;
        this.currentExecutionId = null;
        this.isConnected = false;
        this.isSubmitting = false; // Add flag to prevent duplicate submissions
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkBackendStatus();
        this.connectWebSocket();
        this.updateWelcomeTime();
    }
    
    setupEventListeners() {
        // Form submission
        document.getElementById('testForm').addEventListener('submit', (e) => {
            e.preventDefault();
            if (!this.isSubmitting) {  // Prevent double submission
                this.startTest();
            }
        });
        
        // Form validation - check required fields
        const requiredFields = ['instructions', 'url', 'username', 'password'];
        requiredFields.forEach(fieldId => {
            document.getElementById(fieldId).addEventListener('input', () => {
                this.validateForm();
            });
        });
        
        // Control buttons
        document.getElementById('pauseBtn').addEventListener('click', () => {
            this.controlTest('pause');
        });
        
        document.getElementById('resumeBtn').addEventListener('click', () => {
            this.controlTest('resume');
        });
        
        document.getElementById('stopBtn').addEventListener('click', () => {
            this.controlTest('stop');
        });
        
        // Initial form validation
        this.validateForm();
    }
    
    async checkBackendStatus() {
        try {
            const response = await fetch('/health');
            if (response.ok) {
                const data = await response.json();
                this.updateStatus('backendStatus', 'connected', 'Connected');
                this.updateStatus('azureStatus', 
                    data.azure_client_available ? 'connected' : 'disconnected',
                    data.azure_client_available ? 'Available' : 'Not Available'
                );
            } else {
                this.updateStatus('backendStatus', 'disconnected', 'Error');
            }
        } catch (error) {
            this.updateStatus('backendStatus', 'disconnected', 'Offline');
            this.addUpdate('error', 'Backend connection failed. Please start the backend server.');
        }
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateStatus('wsStatus', 'connected', 'Connected');
                this.addUpdate('success', 'WebSocket connection established');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.log('WebSocket keepalive:', event.data);
                }
            };
            
            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateStatus('wsStatus', 'disconnected', 'Disconnected');
                this.addUpdate('warning', 'WebSocket connection lost. Reconnecting...');
                
                // Reconnect after 3 seconds
                setTimeout(() => {
                    this.connectWebSocket();
                }, 3000);
            };
            
            this.ws.onerror = (error) => {
                this.addUpdate('error', 'WebSocket connection error');
            };
            
        } catch (error) {
            this.updateStatus('wsStatus', 'disconnected', 'Failed');
            this.addUpdate('error', 'Failed to establish WebSocket connection');
        }
    }
    
    async startTest() {
        // Prevent duplicate submissions
        if (this.isSubmitting) {
            console.log('Test submission already in progress, ignoring duplicate request');
            return;
        }
        
        this.isSubmitting = true;
        
        const instructions = document.getElementById('instructions').value.trim();
        const url = document.getElementById('url').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        // Enhance instructions with credentials if not already mentioned
        let enhancedInstructions = instructions;
        if (username && password) {
            // Check if instructions already mention login credentials
            const hasCredentials = instructions.toLowerCase().includes('username') || 
                                 instructions.toLowerCase().includes('user') ||
                                 instructions.toLowerCase().includes('login');
            
            if (!hasCredentials) {
                enhancedInstructions = `${instructions}. Use username "${username}" and password "${password}" for authentication.`;
            } else if (!instructions.toLowerCase().includes(username.toLowerCase())) {
                // Instructions mention login but not specific credentials
                enhancedInstructions = instructions.replace(
                    /(login|sign in|authenticate)/gi, 
                    `$1 with username "${username}" and password "${password}"`
                );
            }
        }
        
        const formData = {
            instructions: enhancedInstructions,
            url: url,
            username: username,
            password: password
        };
        
        try {
            this.addUpdate('info', 'Starting test execution...');
            this.setFormState(false);
            
            const response = await fetch('/api/test/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentExecutionId = data.execution_id;
                
                this.updateStatusCard('running', data.execution_id, 'Test execution started');
                this.addUpdate('success', `Test started with ID: ${data.execution_id}`);
                this.addUpdate('info', `Enhanced instructions: ${enhancedInstructions}`);
                this.enableControlButtons();
                
            } else {
                const error = await response.json();
                this.addUpdate('error', `Failed to start test: ${error.detail || 'Unknown error'}`);
                this.setFormState(true);
            }
            
        } catch (error) {
            this.addUpdate('error', `Network error: ${error.message}`);
            this.setFormState(true);
        } finally {
            this.isSubmitting = false; // Reset flag
        }
    }
    
    validateForm() {
        const instructions = document.getElementById('instructions').value.trim();
        const url = document.getElementById('url').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        const startBtn = document.getElementById('startBtn');
        const isValid = instructions && url && username && password;
        
        startBtn.disabled = !isValid;
        startBtn.style.opacity = isValid ? '1' : '0.5';
        startBtn.style.cursor = isValid ? 'pointer' : 'not-allowed';
        
        // Update placeholder text if needed
        if (!isValid) {
            startBtn.title = 'Please fill all required fields';
        } else {
            startBtn.title = '';
        }
    }
    
    async controlTest(action) {
        if (!this.currentExecutionId) return;
        
        try {
            const response = await fetch(`/api/test/${this.currentExecutionId}/control`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.addUpdate('info', `Test ${action}d successfully`);
                this.updateControlButtons(data.status);
            } else {
                this.addUpdate('error', `Failed to ${action} test`);
            }
            
        } catch (error) {
            this.addUpdate('error', `Network error: ${error.message}`);
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'progress_update':
                this.updateProgress(data.step, data.progress);
                this.addUpdate('info', `${data.step} (${data.progress}%)`);
                break;
                
            case 'status_update':
                this.updateControlButtons(data.status);
                break;
                
            case 'execution_complete':
                this.handleExecutionComplete(data);
                break;
                
            case 'execution_failed':
                this.handleExecutionFailed(data);
                break;
                
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }
    
    updateProgress(step, progress) {
        document.getElementById('currentStep').textContent = step;
        document.getElementById('progressFill').style.width = `${progress}%`;
        document.getElementById('progressText').textContent = `${progress}%`;
    }
    
    updateStatusCard(status, executionId, step) {
        const statusBadge = document.getElementById('statusBadge');
        const executionIdElement = document.getElementById('executionId');
        const currentStep = document.getElementById('currentStep');
        
        statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusBadge.className = `status-badge ${status}`;
        
        if (executionId) {
            executionIdElement.textContent = executionId;
        }
        
        if (step) {
            currentStep.textContent = step;
        }
    }
    
    handleExecutionComplete(data) {
        this.updateStatusCard('completed', data.execution_id, 'Execution completed successfully');
        this.addUpdate('success', 'Test execution completed successfully');
        this.showResults(data.results);
        this.resetForm();
    }
    
    handleExecutionFailed(data) {
        this.updateStatusCard('failed', data.execution_id, 'Execution failed');
        this.addUpdate('error', `Test execution failed: ${data.error}`);
        this.resetForm();
    }
    
    showResults(results) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsContainer = document.getElementById('resultsContainer');
        
        // Create results HTML
        const resultsHtml = `
            <div class="result-summary">
                <div class="result-metric success">
                    <span class="value">${results.summary?.passed || 0}</span>
                    <span class="label">Passed</span>
                </div>
                <div class="result-metric danger">
                    <span class="value">${results.summary?.failed || 0}</span>
                    <span class="label">Failed</span>
                </div>
                <div class="result-metric info">
                    <span class="value">${results.summary?.total_tests || 0}</span>
                    <span class="label">Total Tests</span>
                </div>
                <div class="result-metric info">
                    <span class="value">${results.summary?.success_rate || '0%'}</span>
                    <span class="label">Success Rate</span>
                </div>
            </div>
            
            <div class="result-details">
                <h3>📊 Summary</h3>
                <p>${results.summary?.summary || 'Test execution completed'}</p>
                
                ${results.insights ? `
                <h3>💡 Insights</h3>
                <ul>
                    ${results.insights.map(insight => `<li>${insight}</li>`).join('')}
                </ul>
                ` : ''}
                
                ${results.recommendations ? `
                <h3>🎯 Recommendations</h3>
                <ul>
                    ${results.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
                ` : ''}
            </div>
        `;
        
        resultsContainer.innerHTML = resultsHtml;
        resultsSection.style.display = 'block';
    }
    
    addUpdate(type, message) {
        const container = document.getElementById('updatesContainer');
        const timestamp = new Date().toLocaleTimeString();
        
        const updateElement = document.createElement('div');
        updateElement.className = `update-item ${type}`;
        updateElement.innerHTML = `
            <i class="fas ${this.getIconForType(type)}"></i>
            <span>${message}</span>
            <small>${timestamp}</small>
        `;
        
        container.insertBefore(updateElement, container.firstChild);
        
        // Limit to 50 updates
        while (container.children.length > 50) {
            container.removeChild(container.lastChild);
        }
    }
    
    getIconForType(type) {
        const icons = {
            info: 'fa-info-circle',
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            error: 'fa-times-circle'
        };
        return icons[type] || 'fa-info-circle';
    }
    
    updateStatus(elementId, status, text) {
        const element = document.getElementById(elementId);
        element.textContent = text;
        element.className = `status-${status}`;
    }
    
    setFormState(enabled) {
        const formElements = document.querySelectorAll('#testForm input, #testForm textarea, #startBtn');
        formElements.forEach(element => {
            element.disabled = !enabled;
        });
    }
    
    enableControlButtons() {
        document.getElementById('pauseBtn').disabled = false;
        document.getElementById('stopBtn').disabled = false;
    }
    
    updateControlButtons(status) {
        const pauseBtn = document.getElementById('pauseBtn');
        const resumeBtn = document.getElementById('resumeBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        switch (status) {
            case 'running':
                pauseBtn.disabled = false;
                resumeBtn.disabled = true;
                stopBtn.disabled = false;
                break;
            case 'paused':
                pauseBtn.disabled = true;
                resumeBtn.disabled = false;
                stopBtn.disabled = false;
                break;
            case 'stopped':
            case 'completed':
            case 'failed':
                pauseBtn.disabled = true;
                resumeBtn.disabled = true;
                stopBtn.disabled = true;
                break;
        }
    }
    
    resetForm() {
        this.currentExecutionId = null;
        this.setFormState(true);
        this.updateControlButtons('stopped');
        this.updateProgress('Ready to start test execution', 0);
    }
    
    updateWelcomeTime() {
        const welcomeTime = document.getElementById('welcomeTime');
        if (welcomeTime) {
            welcomeTime.textContent = new Date().toLocaleString();
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TestAutomationApp();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        // Refresh status when page becomes visible
        setTimeout(() => {
            if (window.testApp) {
                window.testApp.checkBackendStatus();
            }
        }, 1000);
    }
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    if (window.testApp) {
        window.testApp.addUpdate('error', 'A JavaScript error occurred. Check console for details.');
    }
});

// Store app instance globally for debugging
window.testApp = null;
document.addEventListener('DOMContentLoaded', () => {
    window.testApp = new TestAutomationApp();
});
