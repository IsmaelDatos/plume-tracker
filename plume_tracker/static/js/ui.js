document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById('wallet-search');
  const clearBtn = document.getElementById('clear-btn');
  const form = document.getElementById('search-form');

  clearBtn.addEventListener('click', () => {
    input.value = '';
    input.focus();
  });

  form.addEventListener('submit', (e) => {
    const wallet = input.value.trim();
    if (!wallet) {
      e.preventDefault();
      alert('Please enter a wallet address');
      return;
    }
    if (!/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
      e.preventDefault();
      alert('Please enter a valid Ethereum wallet address (starting with 0x)');
      return;
    }
    alert('Buscando wallet: ' + wallet);
  });
});
