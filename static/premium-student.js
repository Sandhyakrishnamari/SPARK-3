function showSparkToast(message, type = 'success') {
  let container = document.querySelector('.spark-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'spark-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `spark-toast ${type}`;
  const icon = type === 'success' ? '✨' : '⚠️';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.35s ease';
    setTimeout(() => toast.remove(), 350);
  }, 3400);
}

// Sparkle Particle Burst Effect
function spawnSparkles(x, y) {
  const particles = ['✨', '⭐', '💫', '🎉', '✦'];
  for (let i = 0; i < 6; i++) {
    const p = document.createElement('span');
    p.className = 'sparkle-particle';
    p.innerText = particles[Math.floor(Math.random() * particles.length)];
    p.style.left = `${x}px`;
    p.style.top = `${y}px`;
    const angle = (Math.PI * 2 * i) / 6 + (Math.random() * 0.5 - 0.25);
    const distance = 35 + Math.random() * 35;
    const dx = Math.cos(angle) * distance;
    const dy = Math.sin(angle) * distance - 20;
    p.style.setProperty('--dx', `${dx}px`);
    p.style.setProperty('--dy', `${dy}px`);
    document.body.appendChild(p);
    setTimeout(() => p.remove(), 850);
  }
}

// Click Ripple FX
function createSparkRipple(e, element) {
  const rect = element.getBoundingClientRect();
  const circle = document.createElement('span');
  const diameter = Math.max(rect.width, rect.height);
  const radius = diameter / 2;

  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${e.clientX - rect.left - radius}px`;
  circle.style.top = `${e.clientY - rect.top - radius}px`;
  circle.classList.add('spark-ripple');

  const existingRipple = element.querySelector('.spark-ripple');
  if (existingRipple) existingRipple.remove();

  element.appendChild(circle);
  setTimeout(() => circle.remove(), 550);
}

document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-format .add-btn icons for rotating hover animation
  document.querySelectorAll('.add-btn, .btn-interactive').forEach((btn) => {
    if (!btn.querySelector('.btn-icon')) {
      const text = btn.innerHTML.trim();
      if (text.startsWith('+')) {
        btn.innerHTML = `<span class="btn-icon">+</span> ${text.substring(1).trim()}`;
      }
    }
  });

  // 2. Button Micro-interactions: Click Scale, Ripple & Sparkle Particle Bursts
  document.querySelectorAll('button, .add-btn, .save-button, .download-lor-btn, .btn-interactive').forEach((button) => {
    button.addEventListener('click', (e) => {
      if (button.disabled) return;
      
      // Ripple effect
      createSparkRipple(e, button);

      // Micro press scale animation
      button.animate(
        [{ transform: 'scale(1)' }, { transform: 'scale(.95)' }, { transform: 'scale(1)' }],
        { duration: 200, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' }
      );

      // Trigger sparkle burst on primary action buttons
      if (button.classList.contains('add-btn') || button.classList.contains('save-button') || button.classList.contains('download-lor-btn') || button.type === 'submit') {
        spawnSparkles(e.clientX, e.clientY);
      }
    });
  });

  // 3. Subtle 3D Tilt Effect on Cards
  document.querySelectorAll('.card, .stat-card, .essay-item, .recommender-card').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      card.style.transform = `perspective(1000px) rotateX(${-y / 45}deg) rotateY(${x / 45}deg) translateY(-4px) scale(1.008)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale(1)';
    });
  });

  // 4. Modal Keydown & Backdrop Click Dismissals
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('[id$="Modal"], #recordModal').forEach((modal) => {
      if (getComputedStyle(modal).display !== 'none') modal.style.display = 'none';
    });
  });

  document.querySelectorAll('[id$="Modal"], #recordModal').forEach((modal) => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  });
});
