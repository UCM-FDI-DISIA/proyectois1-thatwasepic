// Efectos de giro y traslación hacia arriba
document.addEventListener('DOMContentLoaded', function() {
    const elems = document.querySelectorAll('.animated-rotate, .animated-translateY');
    
    elems.forEach((elem, index) => {
        if (elem.classList.contains('animated-rotate')) {
            setTimeout(() => {
                elem.style.transition = 'all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
                elem.style.opacity = '1';
                elem.style.scale = '1'; // Requiere CSS Transforms Module Level 2
                elem.style.rotate = 'Y 0deg'; // Requiere CSS Transforms Module Level 2
            }, index * 150);
        }
        else if (elem.classList.contains('animated-translateY')) {
            setTimeout(() => {
                elem.style.transition = 'all 0.6s ease';
                elem.style.opacity = '1';
                elem.style.translate = '0 0'; // Requiere CSS Transforms Module Level 2
            }, index * 150);
        }
    });
});