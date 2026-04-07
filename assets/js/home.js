function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  var isDark;
  if (current) isDark = current === 'dark';
  else isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  var next = isDark ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

const items = document.querySelectorAll('.reveal');
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
  items.forEach((item) => io.observe(item));
} else {
  items.forEach((item) => item.classList.add('visible'));
}

document.querySelectorAll('[data-proof-carousel]').forEach((carousel) => {
  const track = carousel.querySelector('[data-proof-track]');
  const slides = Array.from(carousel.querySelectorAll('[data-proof-slide]'));
  const dots = Array.from(carousel.querySelectorAll('[data-proof-dot]'));
  const prev = carousel.querySelector('[data-proof-prev]');
  const next = carousel.querySelector('[data-proof-next]');
  let activeIndex = 0;

  function setActive(index) {
    activeIndex = index;
    dots.forEach((dot, dotIndex) => {
      const isActive = dotIndex === index;
      dot.classList.toggle('is-active', isActive);
      dot.setAttribute('aria-current', isActive ? 'true' : 'false');
      dot.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    if (prev) prev.disabled = index === 0;
    if (next) next.disabled = index === slides.length - 1;
  }

  function goTo(index) {
    const safeIndex = Math.max(0, Math.min(index, slides.length - 1));
    slides[safeIndex].scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
  }

  dots.forEach((dot, index) => {
    dot.addEventListener('click', () => goTo(index));
  });

  if (prev) prev.addEventListener('click', () => goTo(activeIndex - 1));
  if (next) next.addEventListener('click', () => goTo(activeIndex + 1));

  const slideObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const index = slides.indexOf(entry.target);
        if (index !== -1) setActive(index);
      }
    });
  }, {
    root: track,
    threshold: 0.68
  });

  slides.forEach((slide) => slideObserver.observe(slide));
  setActive(0);
});

document.querySelectorAll('.hero-video').forEach((video) => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const playFromStart = () => {
    video.currentTime = 0;
    video.play().catch(() => {});
  };
  video.addEventListener('click', playFromStart);
  if (reduceMotion) return;
  if (document.readyState === 'complete') playFromStart();
  else window.addEventListener('load', playFromStart, { once: true });
});

