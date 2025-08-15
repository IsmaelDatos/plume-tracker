document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('donation-modal');
  const closeBtn = document.getElementById('close-modal');
  setTimeout(() => {
    modal.classList.remove('hidden');
  }, 1500);
  closeBtn.addEventListener('click', () => {
    modal.classList.add('hidden');
  });
});