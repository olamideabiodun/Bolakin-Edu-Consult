// Script for Bolakin Educational Consult website with enhanced animations

document.addEventListener('DOMContentLoaded', function() {
    // Hide preloader immediately after DOMContentLoaded
    const preloader = document.querySelector('.preloader');
    if (preloader) {
        // For cases where the page loads quickly
        preloader.classList.add('loaded');
        setTimeout(() => {
            preloader.style.display = 'none';
        }, 500);
    }
    
    // Also handle the window.load event (for all resources like images)
    window.addEventListener('load', function() {
        if (preloader) {
            preloader.classList.add('loaded');
            setTimeout(() => {
                preloader.style.display = 'none';
            }, 500);
        }
    });
    
    // Initialize AOS (Animate On Scroll)
    AOS.init({
        duration: 1000,
        easing: 'ease-in-out',
        once: false,
        mirror: false,
        offset: 120,
        delay: 100
    });
    
    // Header scroll effect
    const header = document.querySelector('header');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
    
    // Mobile menu functionality
    const createMobileMenu = () => {
        const headerContainer = document.querySelector('header .container');
        
        // Create hamburger menu if it doesn't exist
        if (!document.querySelector('.hamburger-menu')) {
            // Create hamburger icon
            const hamburger = document.createElement('div');
            hamburger.className = 'hamburger-menu';
            hamburger.innerHTML = '<span></span><span></span><span></span>';
            
            // Add hamburger to header
            headerContainer.appendChild(hamburger);
            
            // Get navigation element and add mobile class
            const nav = document.querySelector('nav');
            const navLinks = document.querySelector('nav ul');
            navLinks.className = 'nav-links';
            
            // Add mobile navigation styles if not already in CSS
            const style = document.createElement('style');
            style.textContent = `
                @media (max-width: 768px) {
                    .hamburger-menu {
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                        width: 30px;
                        height: 21px;
                        cursor: pointer;
                        z-index: 1000;
                        position: relative;
                    }
                    
                    .hamburger-menu span {
                        display: block;
                        height: 3px;
                        width: 100%;
                        background-color: white;
                        border-radius: 3px;
                        transition: all 0.3s ease;
                    }
                    
                    .hamburger-menu.active span:nth-child(1) {
                        transform: translateY(9px) rotate(45deg);
                    }
                    
                    .hamburger-menu.active span:nth-child(2) {
                        opacity: 0;
                    }
                    
                    .hamburger-menu.active span:nth-child(3) {
                        transform: translateY(-9px) rotate(-45deg);
                    }
                    
                    nav {
                        position: relative;
                    }
                    
                    .nav-links {
                        position: fixed;
                        top: 0;
                        right: -280px;
                        background-color: #000;
                        width: 280px;
                        height: 100vh;
                        padding: 80px 20px 30px;
                        flex-direction: column;
                        z-index: 999;
                        transition: right 0.3s ease;
                        overflow-y: auto;
                    }
                    
                    .nav-links.active {
                        right: 0;
                        box-shadow: -5px 0 15px rgba(0, 0, 0, 0.1);
                    }
                    
                    .nav-links li {
                        margin: 15px 0;
                    }
                    
                    .nav-links li a {
                        display: block;
                        padding: 10px 0;
                    }
                    
                    .nav-links .book-btn {
                        margin-top: 15px;
                        text-align: center;
                    }
                    
                    body.menu-open {
                        overflow: hidden;
                    }
                }
            `;
            document.head.appendChild(style);
            
            // Toggle navigation on hamburger click
            hamburger.addEventListener('click', function() {
                this.classList.toggle('active');
                navLinks.classList.toggle('active');
                document.body.classList.toggle('menu-open');
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', function(e) {
                if (navLinks.classList.contains('active') && 
                    !navLinks.contains(e.target) && 
                    !hamburger.contains(e.target)) {
                    navLinks.classList.remove('active');
                    hamburger.classList.remove('active');
                    document.body.classList.remove('menu-open');
                }
            });
            
            // Close menu when clicking on links
            const menuLinks = navLinks.querySelectorAll('a');
            menuLinks.forEach(link => {
                link.addEventListener('click', function() {
                    navLinks.classList.remove('active');
                    hamburger.classList.remove('active');
                    document.body.classList.remove('menu-open');
                });
            });
        }
    };
    
    // Initialize mobile menu
    createMobileMenu();
    
    // Update mobile menu on window resize
    window.addEventListener('resize', function() {
        createMobileMenu();
    });
    
    // Improved scroll to top button functionality with smoother animation
    const scrollToTopBtn = document.querySelector('.scroll-to-top a');
    
    if (scrollToTopBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollToTopBtn.style.opacity = '1';
                scrollToTopBtn.style.visibility = 'visible';
            } else {
                scrollToTopBtn.style.opacity = '0';
                scrollToTopBtn.style.visibility = 'hidden';
            }
        });
        
        scrollToTopBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Smooth scroll to top with custom easing
            const startPosition = window.pageYOffset;
            const duration = 1000; // ms
            let start = null;
            
            function ease(t) {
                return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
            }
            
            function step(timestamp) {
                if (!start) start = timestamp;
                const progress = timestamp - start;
                const percentage = Math.min(progress / duration, 1);
                const easePercentage = ease(percentage);
                
                window.scrollTo(0, startPosition * (1 - easePercentage));
                
                if (progress < duration) {
                    window.requestAnimationFrame(step);
                }
            }
            
            window.requestAnimationFrame(step);
        });
    }
    
    // Subtle hover effects for buttons and cards
    // Country buttons with gentler effects
    const countryBtns = document.querySelectorAll('.country-btn');
    
    countryBtns.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.boxShadow = '0 8px 15px rgba(0, 0, 0, 0.08)';
            this.style.transition = 'all 0.5s ease';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
            this.style.transition = 'all 0.5s ease';
        });
    });
    
    // Add smooth parallax effect to sections
    window.addEventListener('scroll', function() {
        const hero = document.querySelector('.hero');
        const scrollPosition = window.pageYOffset;
        
        if (hero) {
            hero.style.backgroundPosition = `center ${scrollPosition * 0.2}px`;
        }
        
        // Parallax for feature section
        const features = document.querySelector('.features');
        if (features) {
            const featurePos = features.getBoundingClientRect().top;
            features.style.backgroundPosition = `center ${featurePos * 0.2}px`;
        }
    });
    
    // Add hover effect to destination flags with smoother animation
    const destinationItems = document.querySelectorAll('.destinations li');
    
    destinationItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.backgroundColor = 'rgba(255, 153, 51, 0.08)';
            this.style.transition = 'all 0.5s ease';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.backgroundColor = 'rgba(255, 153, 51, 0.03)';
            this.style.transition = 'all 0.5s ease';
        });
    });
    
    // Add gentle fade-in animation to main heading
    const headings = document.querySelectorAll('.hero h1, .hero h2');
    
    headings.forEach((heading, index) => {
        heading.classList.add('animate-fade-in');
        heading.style.animationDelay = `${index * 0.3}s`;
    });
    
    // Add gentle slide-up animation to hero paragraph
    const heroParagraph = document.querySelector('.hero p');
    if (heroParagraph) {
        heroParagraph.classList.add('animate-slide-up');
        heroParagraph.style.animationDelay = '0.6s';
    }
    
    // Add subtle pulse animation to CTA buttons
    const ctaButtons = document.querySelectorAll('.cta-button, .contact-btn');
    ctaButtons.forEach(btn => {
        btn.classList.add('animate-pulse');
    });
    
    // Add smooth animations to service and benefit cards on hover
    const cards = document.querySelectorAll('.service-card, .benefit-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 15px 40px rgba(0, 0, 0, 0.06)';
            this.style.transition = 'all 0.5s ease-in-out';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.03)';
            this.style.transition = 'all 0.5s ease-in-out';
        });
    });
    
    // Add lazy loading for images to improve performance
    const lazyLoadImages = () => {
        const images = document.querySelectorAll('img[data-src]');
        
        if (images.length > 0) {
            if ('IntersectionObserver' in window) {
                images.forEach(img => {
                    const observer = new IntersectionObserver(entries => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                img.src = img.dataset.src;
                                observer.disconnect();
                            }
                        });
                    }, { rootMargin: '0px 0px 100px 0px' });
                    
                    observer.observe(img);
                });
            } else {
                // Fallback for browsers that don't support IntersectionObserver
                images.forEach(img => {
                    img.src = img.dataset.src;
                });
            }
        }
    };
    
    lazyLoadImages();
    
    // Handle subscription success notification
    const subscriptionStatus = new URLSearchParams(window.location.search).get('subscription');
    if (subscriptionStatus === 'success') {
        // Create notification if not already imported through subscription.js
        if (typeof showNotification !== 'function') {
            // Basic notification implementation
            const notification = document.createElement('div');
            notification.className = 'notification success show';
            notification.innerHTML = `
                <div class="notification-content">
                    <i class="fas fa-check-circle"></i>
                    <p>Thank you for subscribing to our newsletter!</p>
                    <button class="close-notification"><i class="fas fa-times"></i></button>
                </div>
            `;
            document.body.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }, 5000);
            
            // Close on button click
            const closeBtn = notification.querySelector('.close-notification');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 300);
                });
            }
            
            // Remove query parameter from URL
            const newUrl = window.location.pathname + window.location.hash;
            history.replaceState(null, '', newUrl);
        }
    }
    
    console.log('Bolakin Educational Consult website loaded successfully with enhanced animations!');
});