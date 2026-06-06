
function goToPage(pageNumber) {
    const form = document.querySelector("form");

    // Remove any existing 'page' input
    const existing = form.querySelector("input[name='page']");
    if (existing) existing.remove();

    // Only append 'page' input if not page 1
    if (pageNumber !== '1') {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "page";
        input.value = pageNumber;
        form.appendChild(input);
    }

    form.submit();
}

// Enhanced interactions
document.addEventListener('DOMContentLoaded', function () {
    // Parallax effect for header
    window.addEventListener('scroll', function () {
        const scrolled = window.pageYOffset;
        const header = document.querySelector('.properties-header');
        const rate = scrolled * -0.5;

        if (header && scrolled < header.offsetHeight) {
            header.style.transform = `translateY(${rate}px)`;
        }
    });

    // Property card hover effects
    const propertyCards = document.querySelectorAll('.property-card');
    propertyCards.forEach((card, index) => {
        card.addEventListener('mouseenter', function () {
            this.style.transform = 'translateY(-15px) scale(1.02)';

            const image = this.querySelector('.property-image');
            if (image) {
                image.style.transform = 'scale(1.1)';
            }
        });

        card.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0) scale(1)';

            const image = this.querySelector('.property-image');
            if (image) {
                image.style.transform = 'scale(1)';
            }
        });

        // Staggered animation on load
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 200 + (index * 100));
    });

    // Form input enhancements
    const inputs = document.querySelectorAll('.form-control, .form-select');
    inputs.forEach(input => {
        input.addEventListener('focus', function () {
            this.parentElement.style.transform = 'scale(1.02)';
            this.parentElement.style.zIndex = '10';
        });

        input.addEventListener('blur', function () {
            this.parentElement.style.transform = 'scale(1)';
            this.parentElement.style.zIndex = '1';
        });
    });

    // Button click effects
    const buttons = document.querySelectorAll('.btn-primary-custom, .btn-outline-primary, .filter-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            // Create ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255, 255, 255, 0.5)';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'ripple 0.6s linear';
            ripple.style.pointerEvents = 'none';

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });

    // Smooth animations for elements coming into view
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                entry.target.style.animationPlayState = 'running';
            }
        });
    }, observerOptions);

    // Observe all property cards and sections
    document.querySelectorAll('.property-card, .filters-section, .pagination-section').forEach(element => {
        observer.observe(element);
    });
});

// Add CSS for ripple animation
const style = document.createElement('style');
style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
document.head.appendChild(style);