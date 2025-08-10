document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById('search-form');
    const input = document.getElementById('wallet-search');
    const clearBtn = document.getElementById('clear-btn');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const wallet = input.value.trim();
        if (/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
            window.location.href = `/wallet/${wallet}`;
        }
    });
    clearBtn.addEventListener('click', () => {
        input.value = '';
        input.focus();
    });
});