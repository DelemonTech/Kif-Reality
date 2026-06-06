// static/js/main.js

// Global variables
let searchTimeout;
const API_BASE_URL = '/api';

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    initializeNavigation();
    initializeAnimations();
    initializeSearch();
    initializePropertyFilters();
    initializeContactForm();
    initializeLazyLoading();
}

// Navigation functionality
function initializeNavigation() {
    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(255, 255, 255, 0.98)';
            navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.15)';
        } else {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        }
    });

    // Mobile menu auto-close
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        link.addEventListener('click', function() {
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse.classList.contains('show')) {
                const bsCollapse = new bootstrap.Collapse(navbarCollapse);
                bsCollapse.hide();
            }
        });
    });
}

// Animation functionality
function initializeAnimations() {
    // Intersection Observer for fade-up animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Stagger animations for multiple elements
                const delay = Array.from(entry.target.parentElement.children)
                    .indexOf(entry.target) * 100;
                setTimeout(() => {
                    entry.target.style.transform = 'translateY(0)';
                    entry.target.style.opacity = '1';
                }, delay);
            }
        });
    }, observerOptions);

    // Observe all elements with animation class
    document.querySelectorAll('.animate-fade-up').forEach(el => {
        observer.observe(el);
    });

    // Counter animation for statistics
    animateCounters();
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    if (!searchInput) return;

    // Create search suggestions container
    const suggestionsContainer = createSearchSuggestions(searchInput);

    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (query.length < 2) {
            hideSuggestions(suggestionsContainer);
            return;
        }

        searchTimeout = setTimeout(() => {
            fetchSearchSuggestions(query, suggestionsContainer);
        }, 300);
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target)) {
            hideSuggestions(suggestionsContainer);
        }
    });
}

// Property filters functionality
function initializePropertyFilters() {
    const filterForm = document.querySelector('form[method="GET"]');
    if (!filterForm) return;

    // Auto-submit filters on change
    const filterInputs = filterForm.querySelectorAll('select, input[type="number"]');
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Add loading state
            const submitBtn = filterForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Filtering...';
                submitBtn.disabled = true;
            }

            // Submit form
            setTimeout(() => {
                filterForm.submit();
            }, 500);
        });
    });

    // Price range validation
    const minPriceInput = filterForm.querySelector('input[name="min_price"]');
    const maxPriceInput = filterForm.querySelector('input[name="max_price"]');

    if (minPriceInput && maxPriceInput) {
        function validatePriceRange() {
            const minPrice = parseInt(minPriceInput.value) || 0;
            const maxPrice = parseInt(maxPriceInput.value) || Infinity;

            if (minPrice > maxPrice) {
                maxPriceInput.setCustomValidity('Maximum price must be greater than minimum price');
            } else {
                maxPriceInput.setCustomValidity('');
            }
        }

        minPriceInput.addEventListener('input', validatePriceRange);
        maxPriceInput.addEventListener('input', validatePriceRange);
    }
}

// Contact form functionality
function initializeContactForm() {
    const contactForm = document.querySelector('form[method="POST"]');
    if (!contactForm) return;

    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sending...';
        submitBtn.disabled = true;

        // Simulate form submission delay
        setTimeout(() => {
            this.submit();
        }, 1000);
    });

    // Real-time form validation
    const requiredFields = contactForm.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            validateField(this);
        });

        field.addEventListener('input', function() {
            if (this.classList.contains('is-invalid')) {
                validateField(this);
            }
        });
    });
}

// Lazy loading for images
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for browsers without IntersectionObserver
        images.forEach(img => {
            img.src = img.dataset.src;
            img.classList.remove('lazy');
        });
    }
}

// Utility Functions
function createSearchSuggestions(searchInput) {
    const container = document.createElement('div');
    container.className = 'search-suggestion';
    container.style.display = 'none';
    
    searchInput.parentElement.style.position = 'relative';
    searchInput.parentElement.appendChild(container);
    
    return container;
}

function fetchSearchSuggestions(query, container) {
    fetch(`${API_BASE_URL}/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.properties.length > 0) {
                showSuggestions(data.properties.slice(0, 5), container);
            } else {
                hideSuggestions(container);
            }
        })
        .catch(error => {
            console.error('Search error:', error);
            hideSuggestions(container);
        });
}

function showSuggestions(properties, container) {
    container.innerHTML = '';
    
    properties.forEach(property => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = `
            <strong>${property.title || 'Property'}</strong><br>
            <small class="text-muted">${property.location || 'Location not specified'}</small>
        `;
        
        item.addEventListener('click', function() {
            window.location.href = `#property-${property.id}`;
        });
        
        container.appendChild(item);
    });
    
    container.style.display = 'block';
}

function hideSuggestions(container) {
    container.style.display = 'none';
}

function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    let message = '';

    // Check if required field is empty
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        message = 'This field is required';
    }

    // Email validation
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            message = 'Please enter a valid email address';
        }
    }

    // Phone validation
    if (field.type === 'tel' && value) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        if (!phoneRegex.test(value.replace(/\s+/g, ''))) {
            isValid = false;
            message = 'Please enter a valid phone number';
        }
    }

    // Update field validation state
    if (isValid) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        removeFieldError(field);
    } else {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        showFieldError(field, message);
    }

    return isValid;
}

function showFieldError(field, message) {
    removeFieldError(field);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    field.parentElement.appendChild(errorDiv);
}

function removeFieldError(field) {
    const existingError = field.parentElement.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

function animateCounters() {
    const counters = document.querySelectorAll('[data-count]');
    
    counters.forEach(counter => {
        const target = parseInt(counter.dataset.count);
        const duration = 2000; // 2 seconds
        const step = target / (duration / 16); // 60fps
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            
            counter.textContent = Math.floor(current).toLocaleString();
        }, 16);
    });
}

// Newsletter subscription functionality
function subscribeNewsletter() {
    const emailInput = document.getElementById('newsletter-email');
    const email = emailInput.value.trim();
    
    if (!email) {
        showNotification('Please enter your email address', 'warning');
        return;
    }

    if (!isValidEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }

    // Show loading state
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Subscribing...';
    button.disabled = true;

    fetch('/api/newsletter/subscribe/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({email: email})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Thank you for subscribing to our newsletter!', 'success');
            emailInput.value = '';
        } else {
            showNotification(data.error || 'An error occurred. Please try again.', 'error');
        }
    })
    .catch(error => {
        showNotification('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Property modal functionality
function showPropertyModal(propertyId) {
    const modal = document.getElementById('propertyModal');
    if (!modal) return;

    // Show loading state
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading property details...</p>
        </div>
    `;

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    // Fetch property details
    fetchPropertyDetails(propertyId)
        .then(property => {
            renderPropertyModal(property, modalBody);
        })
        .catch(error => {
            modalBody.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Unable to load property details. Please try again.
                </div>
            `;
        });
}

function fetchPropertyDetails(propertyId) {
    return fetch(`/api/property/${propertyId}/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Property not found');
            }
            return response.json();
        });
}

function renderPropertyModal(property, container) {
    container.innerHTML = `
        <div class="property-gallery mb-4">
            ${property.images && property.images.length > 0 
                ? `<img src="${property.images[0].url}" alt="${property.title}" class="img-fluid rounded">`
                : `<img src="https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" alt="Property" class="img-fluid rounded">`
            }
        </div>
        
        <div class="row">
            <div class="col-md-8">
                <h3>${property.title || 'Beautiful Property'}</h3>
                <p class="text-muted mb-3">
                    <i class="fas fa-map-marker-alt me-2"></i>
                    ${property.location || 'Location not specified'}
                </p>
                <p>${property.description || 'No description available.'}</p>
                
                <div class="row mt-4">
                    ${property.bedrooms ? `
                        <div class="col-sm-3 text-center">
                            <i class="fas fa-bed fa-2x text-primary mb-2"></i>
                            <p class="mb-0"><strong>${property.bedrooms}</strong><br>Bedrooms</p>
                        </div>
                    ` : ''}
                    ${property.bathrooms ? `
                        <div class="col-sm-3 text-center">
                            <i class="fas fa-bath fa-2x text-primary mb-2"></i>
                            <p class="mb-0"><strong>${property.bathrooms}</strong><br>Bathrooms</p>
                        </div>
                    ` : ''}
                    ${property.area ? `
                        <div class="col-sm-3 text-center">
                            <i class="fas fa-ruler-combined fa-2x text-primary mb-2"></i>
                            <p class="mb-0"><strong>${property.area}</strong><br>Sq Ft</p>
                        </div>
                    ` : ''}
                    ${property.parking ? `
                        <div class="col-sm-3 text-center">
                            <i class="fas fa-car fa-2x text-primary mb-2"></i>
                            <p class="mb-0"><strong>${property.parking}</strong><br>Parking</p>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card bg-light">
                    <div class="card-body">
                        <h4 class="text-primary mb-3">
                            ${property.price ? `₹${parseInt(property.price).toLocaleString()}` : 'Contact for Price'}
                        </h4>
                        
                        <div class="d-grid gap-2">
                            <a href="tel:+919876543210" class="btn btn-primary">
                                <i class="fas fa-phone me-2"></i>Call Now
                            </a>
                            <a href="/contact/" class="btn btn-outline-primary">
                                <i class="fas fa-envelope me-2"></i>Send Inquiry
                            </a>
                            <button class="btn btn-outline-secondary" onclick="scheduleViewing('${property.id}')">
                                <i class="fas fa-calendar me-2"></i>Schedule Viewing
                            </button>
                        </div>
                        
                        <hr>
                        
                        <h6>Quick Contact</h6>
                        <form onsubmit="sendQuickInquiry(event, '${property.id}')">
                            <div class="mb-2">
                                <input type="text" class="form-control form-control-sm" placeholder="Your Name" required>
                            </div>
                            <div class="mb-2">
                                <input type="email" class="form-control form-control-sm" placeholder="Your Email" required>
                            </div>
                            <div class="mb-2">
                                <input type="tel" class="form-control form-control-sm" placeholder="Your Phone" required>
                            </div>
                            <button type="submit" class="btn btn-sm btn-primary w-100">Send Inquiry</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function scheduleViewing(propertyId) {
    showNotification('Feature coming soon! Please contact us directly to schedule a viewing.', 'info');
}

function sendQuickInquiry(event, propertyId) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    // Show loading state
    const button = form.querySelector('button[type="submit"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Sending...';
    button.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        showNotification('Inquiry sent successfully! We will contact you soon.', 'success');
        form.reset();
        button.innerHTML = originalText;
        button.disabled = false;
    }, 1500);
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Utility functions
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Property comparison functionality
let comparisonList = JSON.parse(localStorage.getItem('propertyComparison') || '[]');

function addToComparison(propertyId) {
    if (comparisonList.includes(propertyId)) {
        showNotification('Property already in comparison list', 'warning');
        return;
    }
    
    if (comparisonList.length >= 3) {
        showNotification('You can compare maximum 3 properties', 'warning');
        return;
    }
    
    comparisonList.push(propertyId);
    localStorage.setItem('propertyComparison', JSON.stringify(comparisonList));
    updateComparisonUI();
    showNotification('Property added to comparison', 'success');
}

function removeFromComparison(propertyId) {
    comparisonList = comparisonList.filter(id => id !== propertyId);
    localStorage.setItem('propertyComparison', JSON.stringify(comparisonList));
    updateComparisonUI();
    showNotification('Property removed from comparison', 'info');
}

function updateComparisonUI() {
    const comparisonBadge = document.querySelector('#comparison-badge');
    if (comparisonBadge) {
        comparisonBadge.textContent = comparisonList.length;
        comparisonBadge.style.display = comparisonList.length > 0 ? 'inline' : 'none';
    }
}

// Initialize comparison UI on page load
document.addEventListener('DOMContentLoaded', function() {
    updateComparisonUI();
});

// Smooth scroll for anchor links
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

// Back to top button
function createBackToTopButton() {
    const button = document.createElement('button');
    button.innerHTML = '<i class="fas fa-arrow-up"></i>';
    button.className = 'btn btn-primary rounded-circle position-fixed';
    button.style.bottom = '20px';
    button.style.right = '20px';
    button.style.width = '50px';
    button.style.height = '50px';
    button.style.zIndex = '9999';
    button.style.display = 'none';
    button.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    
    document.body.appendChild(button);
    
    window.addEventListener('scroll', () => {
        button.style.display = window.pageYOffset > 300 ? 'block' : 'none';
    });
}

// Initialize back to top button
document.addEventListener('DOMContentLoaded', createBackToTopButton);