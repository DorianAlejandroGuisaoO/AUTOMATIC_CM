// ============================================
// AUTOMATIC CM - Main JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🤖 Automatic CM cargado correctamente');
    
    // Auto-ocultar mensajes después de 5 segundos
    autoHideAlerts();
    
    // Agregar animaciones de entrada
    addEntryAnimations();
    
    // Inicializar tooltips
    initTooltips();
});

// ============================================
// AUTO-HIDE ALERTS
// ============================================
function autoHideAlerts() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert, index) => {
        // Agregar delay progresivo
        alert.style.animationDelay = `${index * 0.1}s`;
        
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
            
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 5000 + (index * 100));
    });
}

// ============================================
// MOSTRAR MENSAJES DINÁMICOS
// ============================================
function showMessage(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    const messagesContainer = document.querySelector('.messages-container') || createMessagesContainer(container);
    
    messagesContainer.appendChild(alertDiv);
    
    // Auto-ocultar después de 5 segundos
    setTimeout(() => {
        alertDiv.style.opacity = '0';
        alertDiv.style.transform = 'translateX(100px)';
        setTimeout(() => alertDiv.remove(), 500);
    }, 5000);
}

function createMessagesContainer(container) {
    const messagesContainer = document.createElement('div');
    messagesContainer.className = 'messages-container';
    container.insertBefore(messagesContainer, container.firstChild);
    return messagesContainer;
}

// ============================================
// ANIMACIONES DE ENTRADA
// ============================================
function addEntryAnimations() {
    const cards = document.querySelectorAll('.post-card, .comment-card');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
}

// ============================================
// TOOLTIPS
// ============================================
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
            tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
            
            this._tooltip = tooltip;
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
                this._tooltip = null;
            }
        });
    });
}

// ============================================
// LOADING SPINNER
// ============================================
function showLoading(button) {
    const originalContent = button.innerHTML;
    button.setAttribute('data-original-content', originalContent);
    button.disabled = true;
    button.innerHTML = '<span class="spinner"></span> Cargando...';
    return originalContent;
}

function hideLoading(button) {
    const originalContent = button.getAttribute('data-original-content');
    button.disabled = false;
    button.innerHTML = originalContent;
}

// ============================================
// UTILIDADES GLOBALES
// ============================================
window.showMessage = showMessage;
window.showLoading = showLoading;
window.hideLoading = hideLoading;