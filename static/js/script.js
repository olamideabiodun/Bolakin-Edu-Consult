// Script for Bolakin Educational Consult website with enhanced animations

// Handle preloader
window.addEventListener('load', function() {
    // Hide preloader after everything is loaded
    setTimeout(() => {
        const preloader = document.querySelector('.preloader');
        preloader.classList.add('loaded');
        
        // Enable scrolling on body
        document.body.style.overflow = 'auto';
    }, 800);
});

document.addEventListener('DOMContentLoaded', function() {
    // Initialize AOS (Animate On Scroll) with smoother settings
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
    
    // Smooth scrolling for anchor links with improved easing
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const target = document.querySelector(targetId);
            if (target) {
                // Calculate scroll distance for custom easing
                const startPosition = window.pageYOffset;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - 80;
                const distance = targetPosition - startPosition;
                const duration = 1000; // ms
                let start = null;
                
                // Custom easing function for smoother scrolling
                function ease(t) {
                    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                }
                
                function step(timestamp) {
                    if (!start) start = timestamp;
                    const progress = timestamp - start;
                    const percentage = Math.min(progress / duration, 1);
                    const easePercentage = ease(percentage);
                    
                    window.scrollTo(0, startPosition + distance * easePercentage);
                    
                    if (progress < duration) {
                        window.requestAnimationFrame(step);
                    }
                }
                
                window.requestAnimationFrame(step);
            }
        });
    });
    
    // Improved scroll to top button functionality with smoother animation
    const scrollToTopBtn = document.querySelector('.scroll-to-top a');
    
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
    
    // Add responsive navigation for mobile
    const createMobileMenu = () => {
        if (window.innerWidth <= 768) {
            const nav = document.querySelector('nav ul');
            const navItems = document.querySelectorAll('nav ul li');
            
            // Create hamburger menu if not already created
            if (!document.querySelector('.hamburger-menu')) {
                const hamburger = document.createElement('div');
                hamburger.classList.add('hamburger-menu');
                hamburger.innerHTML = '<span></span><span></span><span></span>';
                
                document.querySelector('header .container').appendChild(hamburger);
                
                hamburger.addEventListener('click', function() {
                    this.classList.toggle('active');
                    nav.classList.toggle('active');
                });
                
                // Hide menu when clicking a link
                navItems.forEach(item => {
                    item.addEventListener('click', function() {
                        hamburger.classList.remove('active');
                        nav.classList.remove('active');
                    });
                });
            }
        }
    };
    
    createMobileMenu();
    window.addEventListener('resize', createMobileMenu);
    
    // Add lazy loading for images to improve performance
    const lazyLoadImages = () => {
        const images = document.querySelectorAll('img[data-src]');
        
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
    };
    
    lazyLoadImages();
    
    console.log('Bolakin Educational Consult website loaded successfully with enhanced animations!');
});