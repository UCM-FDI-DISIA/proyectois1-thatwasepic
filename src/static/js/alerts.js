// Mostrar alerta en el contenedor especificado.
function mostrarAlerta(mensaje, tipo, contenedor) {
    const alertClass = tipo === 'success' ? 'alert-success' : 'alert-danger';
    const icon = tipo === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle';
    
    const notificacion = document.createElement('div');
    notificacion.className = `alert ${alertClass} alert-dismissible fade show`;
    notificacion.innerHTML = `
        <i class="fas ${icon} me-2"></i>${mensaje}
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
    `;
    
    contenedor.innerHTML = '';
    contenedor.appendChild(notificacion);
    
    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        if (notificacion.parentElement) {
            notificacion.remove();
        }
    }, 5000);
}