document.addEventListener("DOMContentLoaded", () => {
    const fetchBtn = document.getElementById('fetch-top-earners');
    if (fetchBtn) {
        fetchBtn.addEventListener('click', fetchTopEarners);
    }
});

async function fetchTopEarners() {
    const tableBody = document.getElementById('table-body');
    const fetchBtn = document.getElementById('fetch-top-earners');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressPercentage = document.getElementById('progress-percentage');

    resetUI();

    try {
        // Llamada inicial para iniciar análisis
        let response = await fetch('/api/top-earners');
        if (!response.ok) throw new Error('Error al iniciar el análisis');

        progressStatus.textContent = 'Analizando wallets...';
        progressPercentage.textContent = '0%';
        progressBar.style.width = '10%';

        // Polling para verificar si ya hay resultados
        const checkResults = async () => {
            response = await fetch('/api/top-earners');
            const data = await response.json();

            if (Array.isArray(data) && data.length > 0) {
                renderTable(data);
                showCompletion({ total_wallets: data.length, processing_time: "Calculando..." });
            } else {
                // Actualiza visualmente el progreso cada intento
                const currentWidth = parseInt(progressBar.style.width) || 10;
                if (currentWidth < 90) {
                    progressBar.style.width = `${currentWidth + 10}%`;
                    progressPercentage.textContent = `${currentWidth + 10}%`;
                }
                setTimeout(checkResults, 2000); // Esperar 2s y volver a intentar
            }
        };

        await checkResults();

    } catch (error) {
        showError(error.message);
    }

    // Funciones auxiliares

    function resetUI() {
        tableBody.innerHTML = '';
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = `
            <span class="flex items-center justify-center">
                <i class="fas fa-cog fa-spin mr-2"></i>
                Preparando análisis...
            </span>
        `;
        progressContainer.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressBar.className = 'bg-[#1a1a00] h-2.5 rounded-full transition-all duration-300';
        progressPercentage.textContent = '0%';
        progressStatus.textContent = 'Conectando con el servidor...';
    }

    function showCompletion(data) {
        progressBar.style.width = '100%';
        progressPercentage.textContent = '100%';
        progressStatus.innerHTML = `✅ Análisis completado!<br>
            <span class="text-sm">${data.total_wallets} wallets procesadas</span>`;

        const timeInfo = document.createElement('div');
        timeInfo.className = 'text-sm text-green-600 mt-2 text-center font-medium';
        timeInfo.textContent = `Tiempo total: ${data.processing_time}`;
        progressContainer.appendChild(timeInfo);

        restoreButton();
    }

    function showError(message) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="py-8 text-center text-red-500">
                    <i class="fas fa-exclamation-circle mr-2"></i>
                    ${message}
                </td>
            </tr>
        `;
        progressStatus.textContent = 'Error en el análisis';
        progressBar.classList.remove('bg-[#1a1a00]');
        progressBar.classList.add('bg-red-500');

        restoreButton();
    }

    function restoreButton() {
        const fetchBtn = document.getElementById('fetch-top-earners');
        if (fetchBtn) {
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = `
                <span class="flex items-center justify-center">
                    <i class="fas fa-redo mr-2"></i>
                    Volver a analizar
                </span>
            `;
        }
    }

    function renderTable(items) {
        tableBody.innerHTML = '';

        items.forEach((item, index) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 transition';
            row.innerHTML = `
                <td class="px-4 py-3 border-b font-medium">${index + 1}</td>
                <td class="px-4 py-3 border-b font-mono">
                    <span class="wallet-address" title="${item.wallet}">
                        ${item.wallet.slice(0, 6)}...${item.wallet.slice(-4)}
                    </span>
                    <button class="copy-btn ml-2 text-gray-400 hover:text-[#1a1a00]" 
                            data-wallet="${item.wallet}" 
                            title="Copiar dirección">
                        <i class="fas fa-copy"></i>
                    </button>
                </td>
                <td class="px-4 py-3 border-b text-center">
                    ${item['Rank leaderboard']?.toLocaleString() || 'N/A'}
                </td>
                <td class="px-4 py-3 border-b text-center">
                    ${item['PP total']?.toLocaleString() || '0'}
                </td>
                <td class="px-4 py-3 border-b font-medium text-center">
                    <span class="text-[#1a1a00]">${item.Ganancia?.toLocaleString() || '0'}</span>
                    <span class="text-xs text-gray-500 ml-1">PP</span>
                </td>
            `;
            tableBody.appendChild(row);
        });

        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const wallet = e.currentTarget.getAttribute('data-wallet');
                navigator.clipboard.writeText(wallet);

                const icon = e.currentTarget.querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-check';
                    setTimeout(() => {
                        icon.className = 'fas fa-copy';
                    }, 2000);
                }
            });
        });
    }
}
