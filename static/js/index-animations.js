// KIF Realty – Home page motion layer (pairs with css/index-animations.css)
(function () {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    const root = document.documentElement;

    // ---------- Count-up for the "Why choose" stats ----------
    function animateCount(el) {
        const target = +el.dataset.target || 0;
        if (reduceMotion) { el.textContent = target; return; }
        const duration = 1800;
        const start = performance.now();
        function tick(now) {
            const p = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(target * eased);
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    if (!('IntersectionObserver' in window)) {
        document.querySelectorAll('.kif-count').forEach(animateCount);
        return;
    }

    // ---------- Scroll progress bar ----------
    const progress = document.createElement('div');
    progress.className = 'scroll-progress';
    document.body.appendChild(progress);

    // ---------- Scroll reveal ----------
    const revealGroups = [
        // [selector, extra class, stagger (s)]
        ['.featured-properties .heading', '', 0],
        ['.services-left', 'from-left', 0],
        ['.service-card-1', 'from-right', 0.12],
        ['.location-head', '', 0],
        ['.location-head + .section-title', '', 0],
        ['.day-card', '', 0.08],
        ['.why-choose-kif-left', 'from-left', 0],
        ['.why-choose-kif-right .intro', 'from-right', 0],
        ['.kif-feature', 'from-right', 0.15],
        ['.section-title-new', '', 0],
        ['.calculator-card', 'zoom', 0],
        ['.cta-overlay', 'zoom', 0],
    ];

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const el = entry.target;
            revealObserver.unobserve(el);
            el.classList.add('r-in');
        });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

    function markReveal(el, extra, delay) {
        if (el.classList.contains('reveal')) return;
        el.classList.add('reveal');
        if (extra) el.classList.add(extra);
        if (delay) el.style.setProperty('--d', delay + 's');
        el.addEventListener('animationend', function done(e) {
            if (e.target !== el) return;
            el.classList.remove('r-in');
            el.classList.add('r-done');
            el.style.removeProperty('--d');
            el.removeEventListener('animationend', done);
        });
        revealObserver.observe(el);
    }

    if (!reduceMotion) {
        root.classList.add('anim-ready');
        revealGroups.forEach(([selector, extra, stagger]) => {
            document.querySelectorAll(selector).forEach((el, i) => {
                markReveal(el, extra, stagger ? +(i % 4 * stagger).toFixed(2) : 0);
            });
        });
    }

    // Counters still need to fire on view even without the reveal animation
    const countObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            countObserver.unobserve(entry.target);
            if (!entry.target.dataset.counted) {
                entry.target.dataset.counted = '1';
                animateCount(entry.target);
            }
        });
    }, { threshold: 0.6 });
    document.querySelectorAll('.kif-count').forEach((c) => countObserver.observe(c));

    // ---------- Heading underlines ----------
    const lineObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('drawn');
                lineObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.6 });
    document.querySelectorAll('.heading-left h2, .location-head, .section-title-new h2, .why-choose-kif-left h2')
        .forEach((h) => lineObserver.observe(h));

    // ---------- Cursor spotlight + subtle tilt ----------
    function bindPointerFx(card, tilt) {
        if (card.dataset.fx) return;
        card.dataset.fx = '1';
        card.addEventListener('pointermove', (e) => {
            const r = card.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width;
            const y = (e.clientY - r.top) / r.height;
            card.style.setProperty('--mx', (x * 100).toFixed(1) + '%');
            card.style.setProperty('--my', (y * 100).toFixed(1) + '%');
            if (tilt) {
                card.style.setProperty('--ry', ((x - 0.5) * 8).toFixed(2) + 'deg');
                card.style.setProperty('--rx', ((0.5 - y) * 8).toFixed(2) + 'deg');
            }
        });
        card.addEventListener('pointerleave', () => {
            card.style.setProperty('--rx', '0deg');
            card.style.setProperty('--ry', '0deg');
        });
    }

    if (canHover && !reduceMotion) {
        document.querySelectorAll('.service-card-1').forEach((c) => bindPointerFx(c, false));
    }

    // Property cards are rendered later by the API call, so watch the grid
    const grid = document.querySelector('.featured-properties .properties-grid');
    if (grid) {
        const enhanceCards = () => {
            grid.querySelectorAll('.property-card').forEach((card, i) => {
                if (!reduceMotion) markReveal(card, '', +(i % 4 * 0.1).toFixed(2));
                if (canHover && !reduceMotion) bindPointerFx(card, true);
            });
        };
        new MutationObserver(enhanceCards).observe(grid, { childList: true });
        enhanceCards();
    }

    // ---------- Calculator results "bump" when they change ----------
    ['monthly-payment', 'display-rate', 'total-roi-display', 'annual-roi-display'].forEach((id) => {
        const el = document.getElementById(id);
        if (!el || reduceMotion) return;
        let last = el.textContent;
        new MutationObserver(() => {
            if (el.textContent === last) return;
            last = el.textContent;
            el.classList.add('bump'); // no restart mid-bump, so slider drags stay smooth
        }).observe(el, { childList: true, characterData: true, subtree: true });
        el.addEventListener('animationend', () => el.classList.remove('bump'));
    });

    // ---------- Scroll-driven: progress bar + hero parallax ----------
    const hero = document.querySelector('.hero');
    const heroContent = document.querySelector('.hero-content-container');
    let ticking = false;

    function onScroll() {
        const y = window.scrollY;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        progress.style.transform = 'scaleX(' + (max > 0 ? y / max : 0) + ')';

        if (hero && heroContent && !reduceMotion) {
            const h = hero.offsetHeight;
            const cy = Math.min(y, h);
            heroContent.style.transform = 'translate3d(0,' + (cy * 0.35).toFixed(1) + 'px,0)';
            heroContent.style.opacity = Math.max(0, 1 - (cy / h) * 1.2).toFixed(3);
        }
        ticking = false;
    }

    window.addEventListener('scroll', () => {
        if (!ticking) {
            requestAnimationFrame(onScroll);
            ticking = true;
        }
    }, { passive: true });
    onScroll();
})();
