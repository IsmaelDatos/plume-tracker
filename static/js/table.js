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

    // Reset UI
    resetUI();

    try {
        const eventSource = new EventSource('/api/top-earners-stream');

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleSSEEvent(data);
            } catch (e) {
                console.error("Error parsing SSE data:", e);
                showError('Error procesando datos del servidor');
                eventSource.close();
            }
        };

        eventSource.onerror = () => {
            if (eventSource.readyState === EventSource.CLOSED) {
                return;
            }
            showError('Error en la conexión. Intenta recargar la página.');
            eventSource.close();
        };

    } catch (error) {
        showError(error.message);
    }

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

    function handleSSEEvent(data) {
        console.log("Evento recibido:", data);
        
        if (data.type === 'progress') {
            const percent = Math.round(data.current * 100 / data.total);
            progressBar.style.width = `${percent}%`;
            progressPercentage.textContent = `${percent}%`;
            progressStatus.textContent = data.message || `Procesando ${data.current} de ${data.total}`;
        }
        
        if (data.type === 'complete') {
            eventSource.close();
            renderTable(data.results);
            showCompletion(data);
        }

        if (data.type === 'error') {
            eventSource.close();
            showError(data.message);
        }
    }

    function showCompletion(data) {
        progressStatus.innerHTML = `✅ Análisis completado!<br>
            <span class="text-sm">${data.total_wallets} wallets procesadas</span>`;
        progressPercentage.textContent = '100%';

        const timeInfo = document.createElement('div');
        timeInfo.className = 'text-sm text-green-600 mt-2 text-center font-medium';
        timeInfo.textContent = `Tiempo total: ${data.processing_time}`;
        progressContainer.appendChild(timeInfo);

        restoreButton();
    }

    function showError(message) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="3" class="py-8 text-center text-red-500">
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
        fetchBtn.disabled = false;
        fetchBtn.innerHTML = `
            <span class="flex items-center justify-center">
                <i class="fas fa-redo mr-2"></i>
                Volver a analizar
            </span>
        `;
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
                <td class="px-4 py-3 border-b font-medium">
                    <span class="text-[#1a1a00]">${item.Ganancia.toLocaleString()}</span>
                    <span class="text-xs text-gray-500 ml-1">PP</span>
                </td>
            `;
            tableBody.appendChild(row);
        });

        // Funcionalidad de copiar dirección
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const wallet = e.currentTarget.getAttribute('data-wallet');
                navigator.clipboard.writeText(wallet);

                const icon = e.currentTarget.querySelector('i');
                icon.className = 'fas fa-check';
                setTimeout(() => {
                    icon.className = 'fas fa-copy';
                }, 2000);
            });
        });
    }
}