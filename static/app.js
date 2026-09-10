/* =========================================================
   SPARK — GLOBAL JAVASCRIPT
   static/js/app.js
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initNotifications();
    animateCounters();
});

/* ---------------------------------------------------------
   1. MOBILE SIDEBAR DRAWER & OVERLAY
   --------------------------------------------------------- */
function initSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    
    if (overlay && sidebar) {
        overlay.addEventListener("click", function() {
            sidebar.classList.remove("open");
            overlay.classList.remove("active");
        });
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (sidebar) {
        sidebar.classList.toggle("open");
        if (overlay) {
            overlay.classList.toggle("active", sidebar.classList.contains("open"));
        }
    }
}

/* ---------------------------------------------------------
   2. NOTIFICATIONS & ALERTS
   --------------------------------------------------------- */
function initNotifications() {
    const bell = document.querySelector(".notification-badge");
    if (bell) {
        bell.addEventListener("click", function() {
            window.location.href = "/student/deadlines";
        });
    }
}

/* ---------------------------------------------------------
   3. ANIMATE COUNTERS & NUMBERS
   --------------------------------------------------------- */
function animateCounters() {
    const statNumbers = document.querySelectorAll(".stat-number");
    statNumbers.forEach(num => {
        const text = num.innerText.trim();
        const target = parseFloat(text.replace(/[^0-9.]/g, ''));
        if (isNaN(target) || target <= 0) return;
        
        let start = 0;
        const duration = 1000;
        const startTime = performance.now();
        const hasPercent = text.includes('%');
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = (progress * target).toFixed(hasPercent ? 1 : 0);
            num.innerText = current + (hasPercent ? '%' : '');
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        requestAnimationFrame(update);
    });
}

/* ---------------------------------------------------------
   4. COUNTRY TAB SWITCHING (PREREQUISITES)
   --------------------------------------------------------- */
function switchCountryTab(countryCode) {
    const tabs = document.querySelectorAll(".country-tab");
    const panels = document.querySelectorAll(".country-prereq-panel");

    tabs.forEach(tab => {
        if (tab.dataset.country === countryCode) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });

    panels.forEach(panel => {
        if (panel.id === "country-panel-" + countryCode || countryCode === "ALL") {
            panel.style.display = "block";
            panel.classList.add("content-fade-in");
        } else {
            panel.style.display = "none";
        }
    });
}

/* ---------------------------------------------------------
   5. LOGOUT CONFIRMATION
   --------------------------------------------------------- */
function logout() {
    if (confirm("Are you sure you want to sign out of SPARK?")) {
        window.location.href = "/logout";
    }
}