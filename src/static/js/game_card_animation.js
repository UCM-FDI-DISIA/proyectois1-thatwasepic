// Efectos interactivos para el dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Efecto de escaneo para las cards
    const cards = document.querySelectorAll('.animated-card');
    
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.transition = 'all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            card.style.opacity = '1';
            card.style.transform = 'scale(1) rotateY(0deg)';
        }, index * 150);
    });
});