document.addEventListener('DOMContentLoaded', () => {
  const moreBtn = document.getElementById('load-more-assets');
  const lessBtn = document.getElementById('load-less-assets');
  if (!moreBtn || !lessBtn) return;

  const rows = Array.from(document.querySelectorAll('.asset-row'));
  let visible = 6;
  const increment = 6;

  const updateVisibility = () => {
    rows.forEach((row, i) => {
      if (i < visible) row.classList.remove('hidden');
      else row.classList.add('hidden');
    });

    // Control de botones
    if (visible >= rows.length) {
      moreBtn.textContent = 'There are no more assets';
      moreBtn.disabled = true;
      lessBtn.classList.remove('hidden'); // mostrar "menos"
    } else {
      moreBtn.textContent = 'Show more';
      moreBtn.disabled = false;
      lessBtn.classList.remove('hidden');
    }

    // Si estamos en estado inicial (solo los 6 primeros)
    if (visible <= 6) {
      lessBtn.classList.add('hidden');
      moreBtn.textContent = 'Show more';
      moreBtn.disabled = false;
    }
  };

  // Acción: mostrar más
  moreBtn.addEventListener('click', () => {
    visible += increment;
    if (visible > rows.length) visible = rows.length;
    updateVisibility();
  });

  // Acción: mostrar menos
  lessBtn.addEventListener('click', () => {
    // Volver a las 6 primeras filas
    visible = 6;
    updateVisibility();
  });

  // Estado inicial
  updateVisibility();
});
