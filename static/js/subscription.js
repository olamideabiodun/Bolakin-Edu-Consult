/* 
 * Newsletter Subscription JavaScript
 * This file handles the subscription form interaction and validation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find the subscription form
    const subscribeForm = document.getElementById('subscribeForm');
    
    if (subscribeForm) {
        // Form submit handler with AJAX
        subscribeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get the email input
            const emailInput = this.querySelector('input[name="email"]');
            const email = emailInput.value.trim();
            const csrfTokenInput = this.querySelector('input[name="csrf_token"]');
            const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';
            
            // Basic email validation
            if (!validateEmail(email)) {
                showFormMessage(subscribeForm, 'Please enter a valid email address', 'error');
                return;
            }
            
            // Show loading state
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.textContent;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subscribing...';
            submitBtn.disabled = true;
            
            // Submit form data using fetch API
            fetch('/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken 
                },
                body: new URLSearchParams({
                    'email': email,
                    'csrf_token': csrfToken
                })
            })
            .then(response => {
                if (response.redirected) {
                    // If the server redirected, follow the redirect
                    window.location.href = response.url;
                    return;
                }
                return response.json();
            })
            .then(data => {
                if (data && !data.success) {
                    // Show error message
                    showFormMessage(subscribeForm, data.message || 'Failed to subscribe. Please try again.', 'error');
                    
                    // Reset button
                    submitBtn.textContent = originalBtnText;
                    submitBtn.disabled = false;
                }
                // If successful, the page will have redirected
            })
            .catch(error => {
                console.error('Error:', error);
                showFormMessage(subscribeForm, 'An error occurred. Please try again later.', 'error');
                
                // Reset button
                submitBtn.textContent = originalBtnText;
                submitBtn.disabled = false;
            });
        });
    }
    
    // Handle subscription success notification
    const subscriptionStatus = new URLSearchParams(window.location.search).get('subscription');
    if (subscriptionStatus === 'success') {
        // Show success notification
        showNotification('Thank you for subscribing to our newsletter!', 'success');
        
        // Remove the query parameter from URL without refreshing
        const newUrl = window.location.pathname + window.location.hash;
        history.replaceState(null, '', newUrl);
    }
    
    // Validate email format
    function validateEmail(email) {
        const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(String(email).toLowerCase());
    }
    
    // Show form inline message
    function showFormMessage(form, message, type) {
        // Remove any existing message
        const existingMessage = form.querySelector('.form-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // Create and append new message
        const messageElement = document.createElement('div');
        messageElement.className = `form-message ${type}`;
        messageElement.textContent = message;
        
        // Insert after form
        form.insertAdjacentElement('afterend', messageElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageElement.classList.add('fade-out');
            setTimeout(() => messageElement.remove(), 300);
        }, 5000);
    }
    
    // Show floating notification
    function showNotification(message, type) {
        // Create the notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const content = document.createElement('div');
        content.className = 'notification-content';
        
        const icon = document.createElement('i');
        icon.className = type === 'success' ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
        
        const text = document.createElement('p');
        text.textContent = message;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'close-notification';
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        
        // Assemble the notification
        content.appendChild(icon);
        content.appendChild(text);
        content.appendChild(closeBtn);
        notification.appendChild(content);
        
        // Add to document
        document.body.appendChild(notification);
        
        // Animation timing
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);
        
        // Close on button click
        closeBtn.addEventListener('click', function() {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
    }
});