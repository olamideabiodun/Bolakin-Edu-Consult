// Admission Form JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const openFormBtn = document.getElementById('openAdmissionForm');
    const modal = document.getElementById('admissionFormModal');
    const closeBtn = document.querySelector('.close-btn');
    const admissionForm = document.getElementById('admissionForm');
    
    if (!openFormBtn || !modal || !closeBtn || !admissionForm) {
        console.warn('Admission form elements not found on this page');
        return; // Exit function if elements don't exist
    }
    
    // File Upload Elements
    const fileInputs = [
        { input: document.getElementById('idUpload'), info: document.getElementById('idUploadInfo') },
        { input: document.getElementById('transcriptUpload'), info: document.getElementById('transcriptUploadInfo') },
        { input: document.getElementById('photoUpload'), info: document.getElementById('photoUploadInfo') }
    ];
    
    // Open Modal
    openFormBtn.addEventListener('click', function() {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent body scrolling
        setTimeout(() => {
            modal.classList.add('active');
        }, 10);
    });
    
    // Close Modal
    function closeModal() {
        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Enable body scrolling
        }, 300);
    }
    
    closeBtn.addEventListener('click', closeModal);
    
    // Close when clicking outside the modal content
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
    
    // File Input Handlers
    fileInputs.forEach(({input, info}) => {
        if (input && info) {
            input.addEventListener('change', function() {
                if (input.files.length > 0) {
                    const fileName = input.files[0].name;
                    const fileSize = (input.files[0].size / 1024).toFixed(2); // Convert to KB
                    info.textContent = `${fileName} (${fileSize} KB)`;
                } else {
                    info.textContent = 'No file chosen';
                }
            });
        }
    });
    
    // Form Validation
    function validateForm() {
        let isValid = true;
        const requiredFields = admissionForm.querySelectorAll('[required]');
        
        // Remove existing error messages
        const existingErrors = admissionForm.querySelectorAll('.error-message');
        existingErrors.forEach(error => error.remove());
        
        // Reset field styles
        const formControls = admissionForm.querySelectorAll('input, select, textarea');
        formControls.forEach(control => control.classList.remove('error'));
        
        // Check required fields
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
                
                // Create error message
                const errorMessage = document.createElement('div');
                errorMessage.className = 'error-message';
                errorMessage.textContent = 'This field is required';
                
                // For file inputs, append to the parent container
                if (field.type === 'file') {
                    field.closest('.upload-container').appendChild(errorMessage);
                } else {
                    // For other inputs, append after the input
                    field.parentNode.appendChild(errorMessage);
                }
            }
        });
        
        // Email validation
        const emailField = document.getElementById('email');
        if (emailField && emailField.value && !validateEmail(emailField.value)) {
            isValid = false;
            emailField.classList.add('error');
            
            const errorMessage = document.createElement('div');
            errorMessage.className = 'error-message';
            errorMessage.textContent = 'Please enter a valid email address';
            emailField.parentNode.appendChild(errorMessage);
        }
        
        return isValid;
    }
    
    // Email validation function
    function validateEmail(email) {
        const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(String(email).toLowerCase());
    }
    
    // Form Submission
    admissionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            // Scroll to the first error
            const firstError = admissionForm.querySelector('.error');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
        
        // Create FormData object
        const formData = new FormData(admissionForm);
        
        // Submit form data to the server
        fetch('/submit-admission', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Show success message
                showMessage('success', 'Your application has been submitted successfully! We will contact you via email.');
                // Reset form
                admissionForm.reset();
                // Reset file info
                fileInputs.forEach(({info}) => {
                    if (info) info.textContent = 'No file chosen';
                });
                // Close modal after a delay
                setTimeout(closeModal, 3000);
            } else {
                showMessage('error', data.message || 'There was an error submitting your application. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('error', 'There was an error submitting your application. Please try again later.');
        });
    });
    
    // Display message function
    function showMessage(type, message) {
        // Remove any existing message
        const existingMessage = document.querySelector('.form-message');
        if (existingMessage) existingMessage.remove();
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.className = `form-message ${type}`;
        messageElement.textContent = message;
        
        // Append to form footer
        const formFooter = document.querySelector('.form-footer');
        if (formFooter) {
            formFooter.prepend(messageElement);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                messageElement.remove();
            }, 5000);
        }
    }
});