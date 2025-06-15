// Check for authentication token
const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = '/login';
}

// API base URL
const API_URL = '/api';
//const API_URL = 'https://trading.theinvestmaster.in/api';
// State
let currentPositionToClose = null;

// DOM Elements
const connectionStatus = document.getElementById('connectionStatus');
const accountInfo = document.getElementById('accountInfo');
const autoTradingToggle = document.getElementById('autoTradingToggle');
const positionsBody = document.getElementById('positionsBody');
const historyBody = document.getElementById('historyBody');
const cancelModal = document.getElementById('cancelModal');
const confirmCancelBtn = document.getElementById('confirmCancel');
const closeModalBtn = document.getElementById('closeModal');

// Authenticated fetch wrapper
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const authOptions = {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        }
    };

    const response = await fetch(url, authOptions);
    
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return;
    }
    
    return response;
}

// Logout function
function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
});

async function initializeApp() {
    await checkAccountStatus();
    await loadSettings();
    await loadPositions();
    await loadTradeHistory();
    
    // Refresh data every 5 seconds
    setInterval(() => {
        checkAccountStatus();
        loadPositions();
    }, 5000);
}

function setupEventListeners() {
    autoTradingToggle.addEventListener('change', saveSettings);
    confirmCancelBtn.addEventListener('click', confirmCancelOrder);
    closeModalBtn.addEventListener('click', closeCancelModal);
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === cancelModal) {
            closeCancelModal();
        }
    });
}

// API Functions
async function checkAccountStatus() {
    try {
        const response = await fetchWithAuth(`${API_URL}/account/status`);
        if (!response) return; // Handle auth redirect
        
        const data = await response.json();
        
        if (data.connected) {
            connectionStatus.classList.add('connected');
            connectionStatus.classList.remove('disconnected');
            accountInfo.textContent = `Balance: $${data.balance?.toFixed(2) || '0.00'} | Available: $${data.available_balance?.toFixed(2) || '0.00'}`;
        } else {
            connectionStatus.classList.add('disconnected');
            connectionStatus.classList.remove('connected');
            accountInfo.textContent = 'Disconnected';
        }
    } catch (error) {
        console.error('Error checking account status:', error);
        connectionStatus.classList.add('disconnected');
        accountInfo.textContent = 'Connection Error';
    }
}

async function loadSettings() {
    try {
        const response = await fetchWithAuth(`${API_URL}/settings`);
        if (!response) return; // Handle auth redirect
        
        const data = await response.json();
        
        if (!data.error) {
            autoTradingToggle.checked = data.auto_trading_enabled;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveSettings() {
    try {
        const settings = {
            auto_trading_enabled: autoTradingToggle.checked
        };
        
        const response = await fetchWithAuth(`${API_URL}/settings`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response) return; // Handle auth redirect
        
        const data = await response.json();
        if (data.success) {
            showNotification('Auto trading ' + (autoTradingToggle.checked ? 'enabled' : 'disabled'), 'success');
        } else {
            showNotification('Failed to update settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

async function loadPositions() {
    try {
        const response = await fetchWithAuth(`${API_URL}/positions`);
        if (!response) return; // Handle auth redirect
        
        const positions = await response.json();
        updatePositionsTable(positions);
    } catch (error) {
        console.error('Error loading positions:', error);
    }
}

function updatePositionsTable(positions) {
    if (positions.length === 0) {
        positionsBody.innerHTML = '<tr><td colspan="9" class="empty-message">No open positions</td></tr>';
        return;
    }
    
    const rows = positions.map(pos => {
        const pnlClass = pos.pnl >= 0 ? 'profit' : 'loss';
        return `
            <tr>
                <td>${pos.symbol}</td>
                <td>${pos.side}</td>
                <td>${pos.size}</td>
                <td>${pos.leverage || '-'}x</td>
                <td>${pos.entry_price.toFixed(4)}</td>
                <td>${pos.current_price.toFixed(4)}</td>
                <td class="${pnlClass}">${pos.pnl.toFixed(2)}</td>
                <td class="${pnlClass}">${pos.pnl_percentage.toFixed(2)}%</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="showCloseModal('${pos.symbol}', '${pos.side}', ${pos.size})">
                        Close
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    positionsBody.innerHTML = rows;
}



async function loadTradeHistory() {
    try {
        const response = await fetchWithAuth(`${API_URL}/trades?limit=50`);
        if (!response) return; // Handle auth redirect
        
        const trades = await response.json();
        
        if (trades.length === 0) {
            historyBody.innerHTML = '<tr><td colspan="7" class="empty-message">No trade history</td></tr>';
            return;
        }
        
        const rows = trades.map(trade => {
            const statusClass = trade.status === 'filled' ? 'profit' : 
                              trade.status === 'cancelled' ? 'loss' : '';
            
            // Parse as UTC explicitly by adding 'Z' to indicate UTC
            const utcDate = new Date(trade.created_at + 'Z');
            
            // Now convert to IST string
            const istString = utcDate.toLocaleString('en-IN', {
                timeZone: 'Asia/Kolkata',
                year: 'numeric',
                month: 'numeric',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
            
            return `
                <tr>
                    <td>${istString} IST</td>
                    <td>${trade.symbol}</td>
                    <td>${trade.side}</td>
                    <td>${trade.quantity}</td>
                    <td>${trade.entry_price ? `$${trade.entry_price.toFixed(4)}` : '-'}</td>
                    <td class="${statusClass}">${trade.status.toUpperCase()}</td>
                    <td>${trade.reason || '-'}</td>
                </tr>
            `;
        }).join('');
        
        historyBody.innerHTML = rows;
    } catch (error) {
        console.error('Error loading trade history:', error);
        historyBody.innerHTML = '<tr><td colspan="7" class="empty-message">Error loading trade history</td></tr>';
    }
}








// Show close modal function
function showCloseModal(symbol, side, size) {
    currentPositionToClose = { symbol, side, size };
    cancelModal.style.display = 'block';
}

// Close modal function
function closeCancelModal() {
    cancelModal.style.display = 'none';
    currentPositionToClose = null;
}

// Confirm close position
async function confirmCancelOrder() {
    if (!currentPositionToClose) return;
    
    try {
        const { symbol, side, size } = currentPositionToClose;
        const response = await fetchWithAuth(`${API_URL}/positions/${symbol}/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ side, size })
        });
        
        if (!response) return; // Handle auth redirect
        
        const data = await response.json();
        if (data.success) {
            showNotification('Position closed successfully', 'success');
            await loadPositions();
            await loadTradeHistory();
        } else {
            showNotification(`Failed to close position: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Error closing position:', error);
        showNotification('Error closing position', 'error');
    } finally {
        closeCancelModal();
    }
}

// Notification Function
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#238636' : type === 'error' ? '#da3633' : '#1f6feb'};
        color: white;
        border-radius: 6px;
        z-index: 2000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .btn-sm {
        padding: 4px 8px;
        font-size: 12px;
    }
`;
document.head.appendChild(style);

