document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById('wallet-search');
  const clearBtn = document.getElementById('clear-btn');
  const form = document.getElementById('search-form');

  clearBtn.addEventListener('click', () => {
    input.value = '';
    input.focus();
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const wallet = input.value.trim();
    if (wallet) {
      alert('Buscando wallet: ' + wallet);
      // Aquí se podría implementar búsqueda en el backend si deseas
    }
  });
});
