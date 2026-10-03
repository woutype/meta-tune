// Code that is used on every page

const toastArea = document.getElementById('toast-area');

function hideToast(toast) {
    setTimeout(() => {
        toast.classList.add('leaving');
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

// Shows a small message at the top (type is 'success' or 'error')
function showToast(text, type) {
    const iconPath = type === 'success' ? toastArea.dataset.successIcon : toastArea.dataset.errorIcon;
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = '<span class="toast-icon"><img src="' + iconPath + '" alt=""></span><span></span>';
    toast.lastChild.textContent = text;
    toastArea.appendChild(toast);
    hideToast(toast);
}

// The glow of the cards follows the mouse
document.querySelectorAll('.spotlight').forEach((card) => {
    card.addEventListener('mousemove', (event) => {
        const box = card.getBoundingClientRect();
        card.style.setProperty('--mx', (event.clientX - box.left) + 'px');
        card.style.setProperty('--my', (event.clientY - box.top) + 'px');
    });
});

// Hide the messages that came from the server
document.querySelectorAll('.toast').forEach(hideToast);
