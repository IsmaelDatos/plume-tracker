function copyWallet(wallet) {
  navigator.clipboard.writeText(wallet);
  const buttons = document.querySelectorAll(`button[onclick="copyWallet('${wallet}')"]`);
  buttons.forEach(btn => {
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = 'fas fa-check text-green-500';
      setTimeout(() => {
        icon.className = 'fas fa-copy';
      }, 2000);
    }
  });
  
  const notification = document.createElement('div');
  notification.className = 'fixed bottom-4 right-4 bg-[#1a1a00] text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-fade-in-out';
  notification.textContent = 'Wallet address copied!';
  document.body.appendChild(notification);
  setTimeout(() => {
    notification.remove();
  }, 2000);
}