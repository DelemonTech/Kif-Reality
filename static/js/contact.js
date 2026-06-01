document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const submitBtn = contactForm.querySelector('.submit-btn');
    
    // Form validation
    function validateForm() {
        const required = ['firstName', 'lastName', 'email', 'phone'];
        let valid = true;
        
        required.forEach(function(fieldName) {
            const field = document.getElementById(fieldName);
            const value = field.value.trim();
            
            if (!value) {
                showFieldError(field, 'This field is required');
                valid = false;
            } else {
                clearFieldError(field);
                
                // Email validation
                if (fieldName === 'email' && !isValidEmail(value)) {
                    showFieldError(field, 'Please enter a valid email address');
                    valid = false;
                }
                
                // Phone validation
                if (fieldName === 'phone' && !isValidPhone(value)) {
                    showFieldError(field, 'Please enter a valid phone number');
                    valid = false;
                }
            }
        });
        
        return valid;
    }
    
    function showFieldError(field, message) {
        clearFieldError(field);
        field.classList.add('error');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }
    
    function clearFieldError(field) {
        field.classList.remove('error');
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    function isValidPhone(phone) {
        const phoneRegex = /^[\+]?[\d\s\-\(\)]{8,}$/;
        return phoneRegex.test(phone);
    }
    
    // Form submission handling
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        // Show loading state
        submitBtn.disabled = true;
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        
        // Collect form data
        const formData = new FormData(contactForm);
        
        // Submit via fetch API for better UX
        fetch(contactForm.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => {
            if (response.redirected) {
                // If redirected, follow the redirect
                window.location.href = response.url;
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                showSuccessMessage(data.message);
                contactForm.reset();
            } else if (data && data.message) {
                showErrorMessage(data.message);
            }
        })
        .catch(error => {
            console.error('Form submission error:', error);
            // Fallback to normal form submission
            contactForm.submit();
        })
        .finally(() => {
            // Reset button state
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        });
    });
    
    function showSuccessMessage(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="close-alert">&times;</button>
        `;
        
        insertMessage(alertDiv);
    }
    
    function showErrorMessage(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-error';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="close-alert">&times;</button>
        `;
        
        insertMessage(alertDiv);
    }
    
    function insertMessage(alertDiv) {
        let messagesContainer = document.querySelector('.messages-container');
        if (!messagesContainer) {
            messagesContainer = document.createElement('div');
            messagesContainer.className = 'messages-container';
            document.querySelector('.page-header').insertAdjacentElement('afterend', messagesContainer);
        }
        
        messagesContainer.appendChild(alertDiv);
        
        // Add close functionality
        const closeBtn = alertDiv.querySelector('.close-alert');
        closeBtn.addEventListener('click', function() {
            alertDiv.remove();
        });
        
        // Auto-hide after 5 seconds
        setTimeout(function() {
            alertDiv.style.opacity = '0';
            setTimeout(function() {
                alertDiv.remove();
            }, 300);
        }, 5000);
        
        // Scroll to message
        alertDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // Real-time validation
    const inputs = contactForm.querySelectorAll('input[required]');
    inputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value.trim()) {
                clearFieldError(this);
                
                if (this.type === 'email' && !isValidEmail(this.value)) {
                    showFieldError(this, 'Please enter a valid email address');
                } else if (this.id === 'phone' && !isValidPhone(this.value)) {
                    showFieldError(this, 'Please enter a valid phone number');
                }
            }
        });
    });
    
    // FAQ Toggle functionality
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach(function(question) {
        question.addEventListener('click', function() {
            const faqItem = this.parentElement;
            const answer = faqItem.querySelector('.faq-answer');
            const icon = this.querySelector('i');
            
            // Toggle active class
            faqItem.classList.toggle('active');
            
            // Rotate icon
            if (faqItem.classList.contains('active')) {
                icon.style.transform = 'rotate(180deg)';
                answer.style.maxHeight = answer.scrollHeight + 'px';
            } else {
                icon.style.transform = 'rotate(0deg)';
                answer.style.maxHeight = '0';
            }
        });
    });
    
    // Phone number formatting
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            
            // Add country code if not present
            if (value.length > 0 && !value.startsWith('971')) {
                if (value.startsWith('0')) {
                    value = '971' + value.substring(1);
                } else if (value.length === 9) {
                    value = '971' + value;
                }
            }
            
            // Format the number
            if (value.length > 3) {
                if (value.length <= 5) {
                    value = value.replace(/(\d{3})(\d{1,2})/, '+$1 $2');
                } else if (value.length <= 8) {
                    value = value.replace(/(\d{3})(\d{2})(\d{1,3})/, '+$1 $2 $3');
                } else {
                    value = value.replace(/(\d{3})(\d{2})(\d{3})(\d{1,4})/, '+$1 $2 $3 $4');
                }
            } else if (value.length > 0) {
                value = '+' + value;
            }
            
            e.target.value = value;
        });
    }
});