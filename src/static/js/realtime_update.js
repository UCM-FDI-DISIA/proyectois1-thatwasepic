class ContainerUpdater {
    constructor(containerId, page_param = 'page') {
        this.container = document.querySelector(containerId);
        this.page_param = page_param;
    }

    getCurrentPage() {
        const params = new URLSearchParams(window.location.search);
        return parseInt(params.get(this.page_param)) || 1;
    }

    updateContainer(page = this.getCurrentPage()) {
        const url = `?${this.page_param}=${page}`;

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => {
                if (!response.ok) throw new Error('Error en la respuesta del servidor');
                return response.text();
            })
            .then(html => {
                this.container.innerHTML = html;

                // USAR this
                this.initializePagination();
            })
            .catch(error => console.error('Error actualizando contenido:', error));
    }

    initializePagination() {
        const pagLinks = this.container.querySelectorAll('.pagination a.page-link');

        pagLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();

                // aquí "this" es la instancia de la clase
                const pageMatch = link.href.match(new RegExp(this.page_param + "=(\\d+)"));
                const page = pageMatch ? parseInt(pageMatch[1]) : 1;

                this.updateContainer(page);

                window.history.replaceState({}, '', `?${this.page_param}=${page}`);
            });
        });
    }
}

// Actualización de contenido al interaccionar con botones de paginación
function addPaginationUpdate(containerInstance) {
    document.addEventListener('DOMContentLoaded', function() {
        // Inicialización inicial
        containerInstance.initializePagination();
    });
}

// Actualización de contenido al interaccionar con botones de paginación
function addAutoReload(containerInstance, timeInterval) {
    document.addEventListener('DOMContentLoaded', function() {
        const socket = window.socket;

        // Inicializar los eventos de Socket.IO
        socket.on('user_joined', (data) => {
            console.log('Usuario se unió:', data);
            containerInstance.updateContainer();
        });

        socket.on('user_left', (data) => {
            console.log('Usuario salió:', data);
            containerInstance.updateContainer();
        });

        // Actualizar periódicamente
        setInterval(() => containerInstance.updateContainer(), timeInterval);
    });
}