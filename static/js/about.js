
// Enhanced navbar scroll effect
window.addEventListener('scroll', function () {
    const navbar = document.getElementById('navbar');

    if (window.scrollY > 100) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Smooth scroll for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Timeline animation
const timelineItems = document.querySelectorAll('.timeline-item');
timelineItems.forEach((item, index) => {
    const delay = index * 200;
    setTimeout(() => {
        item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
    }, 500 + delay);

    item.style.opacity = '0';
    item.style.transform = index % 2 === 0 ? 'translateX(-50px)' : 'translateX(50px)';
    item.style.transition = 'all 0.8s ease';
});

// Parallax effect for backgrounds
window.addEventListener('scroll', function () {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll('.page-header, .timeline-bg');

    parallaxElements.forEach(element => {
        const rate = scrolled * -0.5;
        element.style.transform = `translateY(${rate}px)`;
    });
});

// Enhanced hover effects
document.querySelectorAll('.expertise-card').forEach(card => {
    card.addEventListener('mouseenter', function () {
        this.querySelector('i').style.transform = 'scale(1.2) rotate(10deg)';
        this.querySelector('i').style.transition = 'transform 0.3s ease';
    });

    card.addEventListener('mouseleave', function () {
        this.querySelector('i').style.transform = 'scale(1) rotate(0deg)';
    });
});

// Initialize page animations
document.addEventListener('DOMContentLoaded', function () {
    // Add loading animation
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.5s ease-in-out';

    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 100);

    // Staggered animation for story content
    const storyElements = document.querySelectorAll('.story-content h2, .story-content p');
    storyElements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'all 0.6s ease';

        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 200 + (index * 150));
    });

    // Leadership cards hover effect
    document.querySelectorAll('.leader-card').forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.querySelector('.leader-image').style.transform = 'scale(1.05)';
        });

        card.addEventListener('mouseleave', function () {
            this.querySelector('.leader-image').style.transform = 'scale(1)';
        });
    });
});