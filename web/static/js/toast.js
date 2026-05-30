// Minimal toast helper — window.toast(msg, type, ttl)
// type: 'info' | 'success' | 'error' | 'warn'
(function () {
    let host = null;
    function ensure() {
        if (host) return host;
        host = document.createElement('div');
        host.id = 'toast-host';
        host.setAttribute('aria-live', 'polite');
        host.setAttribute('aria-atomic', 'true');
        document.body.appendChild(host);
        return host;
    }

    window.toast = function (msg, type, ttl) {
        type = type || 'info';
        ttl = ttl || (type === 'error' ? 4500 : 3000);
        const h = ensure();
        const t = document.createElement('div');
        t.className = 'toast toast-' + type;
        t.textContent = String(msg);
        h.appendChild(t);
        // Force reflow then add is-in (slide+fade)
        requestAnimationFrame(() => {
            requestAnimationFrame(() => t.classList.add('is-in'));
        });
        setTimeout(() => {
            t.classList.remove('is-in');
            setTimeout(() => { if (t.parentNode) t.parentNode.removeChild(t); }, 220);
        }, ttl);
        return t;
    };
})();
