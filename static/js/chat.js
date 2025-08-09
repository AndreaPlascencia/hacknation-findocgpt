class FinancialChatBot {
    constructor() {
        this.socket = io();
        this.chartModal = new bootstrap.Modal(document.getElementById('chartModal'));
        this.currentChart = null;
        this.messageCount = 0;
        
        this.initializeEventListeners();
        this.setupSocketEvents();
    }

    initializeEventListeners() {
        // Form submission
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Quick action buttons
        document.querySelectorAll('.quick-action').forEach(button => {
            button.addEventListener('click', (e) => {
                const message = e.target.getAttribute('data-message') || 
                               e.target.closest('.quick-action').getAttribute('data-message');
                document.getElementById('message-input').value = message;
                this.sendMessage();
            });
        });

        // Clear chat button
        document.getElementById('clear-chat').addEventListener('click', () => {
            this.clearChat();
        });

        // Enter key handling
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    setupSocketEvents() {
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            console.log('Connected to server');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            console.log('Disconnected from server');
        });

        this.socket.on('status', (data) => {
            console.log('Status:', data.msg);
        });

        this.socket.on('response', (data) => {
            this.handleBotResponse(data);
        });

        this.socket.on('typing', (data) => {
            this.showTypingIndicator(data.typing);
        });

        this.socket.on('error', (data) => {
            this.handleError(data.message);
        });
    }

    sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (!message) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        messageInput.value = '';
        
        // Send to server
        this.socket.emit('message', { message: message });
        
        // Show typing indicator
        this.showTypingIndicator(true);
    }

    addMessage(message, sender, data = null) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message mb-3`;
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-end">
                    <div class="card bg-primary text-white" style="max-width: 80%;">
                        <div class="card-body p-3">
                            <p class="mb-0">${this.escapeHtml(message)}</p>
                            <small class="opacity-75">${new Date().toLocaleTimeString()}</small>
                        </div>
                    </div>
                </div>
            `;
        } else {
            const hasCharts = data && data.has_charts;
            const chartButton = hasCharts ? 
                `<button class="btn btn-outline-light btn-sm mt-2" onclick="chatBot.showChart(${JSON.stringify(data).replace(/"/g, '&quot;')})">
                    <i class="fas fa-chart-line me-1"></i>View Chart
                </button>` : '';
            
            messageDiv.innerHTML = `
                <div class="d-flex">
                    <div class="me-3">
                        <div class="avatar bg-success rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;">
                            <i class="fas fa-robot text-white"></i>
                        </div>
                    </div>
                    <div class="flex-grow-1">
                        <div class="card bg-secondary bg-opacity-20" style="max-width: 90%;">
                            <div class="card-body p-3">
                                <div class="message-content">${this.formatBotMessage(message, data)}</div>
                                <div class="d-flex justify-content-between align-items-center mt-2">
                                    <small class="text-muted">${new Date().toLocaleTimeString()}</small>
                                    ${chartButton}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Remove welcome message if it exists
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage && this.messageCount === 0) {
            welcomeMessage.remove();
        }

        chatMessages.appendChild(messageDiv);
        this.messageCount++;
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    formatBotMessage(message, data) {
        let formattedMessage = this.escapeHtml(message);
        
        if (data) {
            // Add KPI information
            if (data.kpis && Object.keys(data.kpis.metrics || {}).length > 0) {
                formattedMessage += '<div class="mt-3"><strong>Extracted KPIs:</strong><ul class="list-unstyled mt-2">';
                for (const [metric, values] of Object.entries(data.kpis.metrics)) {
                    if (values && values.length > 0) {
                        formattedMessage += `<li><i class="fas fa-chart-bar text-info me-2"></i>${metric}: ${values[0].value}</li>`;
                    }
                }
                formattedMessage += '</ul></div>';
            }

            // Add financial data summary
            if (data.financial_data && data.financial_data.data) {
                const summary = data.financial_data.data.summary;
                if (summary && summary.total_records > 0) {
                    formattedMessage += `<div class="mt-3">
                        <strong>Financial Data Summary:</strong>
                        <ul class="list-unstyled mt-2">
                            <li><i class="fas fa-database text-primary me-2"></i>Records: ${summary.total_records}</li>
                            <li><i class="fas fa-building text-success me-2"></i>Companies: ${summary.companies_count}</li>
                            <li><i class="fas fa-chart-line text-warning me-2"></i>Metrics: ${summary.metrics_count}</li>
                        </ul>
                    </div>`;
                }
            }

            // Add forecast information
            if (data.forecast && data.forecast.forecast_data) {
                const forecast = data.forecast.forecast_data;
                formattedMessage += `<div class="mt-3">
                    <strong>Forecast Results:</strong>
                    <ul class="list-unstyled mt-2">
                        <li><i class="fas fa-crystal-ball text-info me-2"></i>Method: ${forecast.method_used || 'Linear Regression'}</li>
                        <li><i class="fas fa-calendar text-primary me-2"></i>Periods: ${data.forecast.forecast_periods}</li>
                        <li><i class="fas fa-accuracy text-success me-2"></i>MAE: ${forecast.model_performance?.mae || 'N/A'}</li>
                    </ul>
                </div>`;
            }
        }

        return formattedMessage;
    }

    handleBotResponse(data) {
        this.showTypingIndicator(false);
        this.addMessage(data.message, 'bot', data);
    }

    handleError(message) {
        this.showTypingIndicator(false);
        this.addMessage(`Error: ${message}`, 'bot');
    }

    showTypingIndicator(show) {
        const indicator = document.getElementById('typing-indicator');
        if (show) {
            indicator.style.display = 'block';
        } else {
            indicator.style.display = 'none';
        }
        
        // Scroll to bottom when showing/hiding typing indicator
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (connected) {
            statusElement.innerHTML = '<i class="fas fa-circle text-success me-1"></i>Connected';
        } else {
            statusElement.innerHTML = '<i class="fas fa-circle text-danger me-1"></i>Disconnected';
        }
    }

    clearChat() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="card bg-primary bg-opacity-10 border-primary">
                    <div class="card-body text-center">
                        <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                        <h5>Welcome to Financial AI Assistant</h5>
                        <p class="mb-0">Ask me about financial data, KPIs, forecasts, or company analysis. 
                        I can help you with FinanceBench queries, extract key performance indicators, 
                        and provide financial forecasts.</p>
                    </div>
                </div>
            </div>
        `;
        this.messageCount = 0;
    }

    showChart(data) {
        // Prepare chart data
        let chartData = null;
        let chartTitle = 'Financial Chart';

        if (data.financial_data && data.financial_data.data && data.financial_data.data.time_series) {
            chartData = this.prepareFinancialChartData(data.financial_data.data);
            chartTitle = 'Financial Data Visualization';
        } else if (data.forecast && data.forecast.forecast_data) {
            chartData = this.prepareForecastChartData(data.forecast.forecast_data);
            chartTitle = 'Financial Forecast';
        }

        if (!chartData) {
            alert('No chart data available');
            return;
        }

        // Update modal title
        document.getElementById('chartModalLabel').textContent = chartTitle;

        // Destroy existing chart
        if (this.currentChart) {
            this.currentChart.destroy();
        }

        // Create new chart
        const ctx = document.getElementById('financial-chart').getContext('2d');
        this.currentChart = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Period'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Value'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });

        // Show modal
        this.chartModal.show();
    }

    prepareFinancialChartData(financialData) {
        const colors = ['#0d6efd', '#198754', '#dc3545', '#ffc107', '#6f42c1', '#20c997'];
        const datasets = [];
        let colorIndex = 0;

        for (const [key, series] of Object.entries(financialData.time_series)) {
            const labels = series.data_points.map(point => point.period);
            const data = series.data_points.map(point => point.value);

            datasets.push({
                label: `${series.company} - ${series.metric}`,
                data: data,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '20',
                tension: 0.3
            });
            colorIndex++;
        }

        // Use labels from first dataset
        const labels = Object.values(financialData.time_series)[0]?.data_points.map(point => point.period) || [];

        return {
            labels: labels,
            datasets: datasets
        };
    }

    prepareForecastChartData(forecastData) {
        const historicalData = forecastData.historical_values || [];
        const forecastValues = forecastData.forecast_values || [];
        const historicalDates = forecastData.historical_dates || [];
        const forecastDates = forecastData.forecast_dates || [];

        const allLabels = [...historicalDates, ...forecastDates];
        const allHistoricalData = [...historicalData, ...new Array(forecastDates.length).fill(null)];
        const allForecastData = [...new Array(historicalDates.length).fill(null), ...forecastValues];

        return {
            labels: allLabels,
            datasets: [
                {
                    label: 'Historical Data',
                    data: allHistoricalData,
                    borderColor: '#0d6efd',
                    backgroundColor: '#0d6efd20',
                    tension: 0.3
                },
                {
                    label: 'Forecast',
                    data: allForecastData,
                    borderColor: '#dc3545',
                    backgroundColor: '#dc354520',
                    borderDash: [5, 5],
                    tension: 0.3
                }
            ]
        };
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the chatbot when the page loads
const chatBot = new FinancialChatBot();
