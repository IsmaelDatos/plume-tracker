document.addEventListener("DOMContentLoaded", () => {
    const fetchBtn = document.getElementById('fetch-top-earners');
    if (fetchBtn) {
        fetchBtn.addEventListener('click', startTopEarnersStream);
    }
});

function startTopEarnersStream() {
    const tableBody = document.getElementById('table-body');
    const fetchBtn = document.getElementById('fetch-top-earners');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressPercentage = document.getElementById('progress-percentage');

    resetUI();
    
    let fakeProgress = 0;
    const fakeProgressInterval = setInterval(() => {
        if (fakeProgress < 80) {
            fakeProgress += Math.random() * 2;
            if (fakeProgress > 80) fakeProgress = 80;
            
            progressBar.style.width = `${fakeProgress}%`;
            progressPercentage.textContent = `${Math.round(fakeProgress)}%`;
            progressStatus.textContent = `Preparando datos... ${Math.round(fakeProgress)}%`;
        } else if (fakeProgress < 95) {
            fakeProgress += Math.random() * 0.3;
            if (fakeProgress > 95) fakeProgress = 95;
            
            progressBar.style.width = `${fakeProgress}%`;
            progressPercentage.textContent = `${Math.round(fakeProgress)}%`;
            progressStatus.textContent = `Finalizando preparación... ${Math.round(fakeProgress)}%`;
        }
    }, 1500);

    const evtSource = new EventSource('/api/top-earners/stream');

    evtSource.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);

            if (msg.type === "progress") {
                clearInterval(fakeProgressInterval);
                const realProgress = 90 + (msg.progress * 0.1);
                progressBar.style.width = `${realProgress}%`;
                progressPercentage.textContent = `${Math.round(realProgress)}%`;
                progressStatus.textContent = `Procesando ${msg.completed}/${msg.total} wallets...`;
            }

            if (msg.type === "completed") {
                clearInterval(fakeProgressInterval);
                renderTable(msg.data);
                progressBar.style.width = "100%";
                progressPercentage.textContent = "100%";
                progressStatus.textContent = "✅ Análisis completado!";
                restoreButton();
                evtSource.close();
            }

            if (msg.type === "error") {
                clearInterval(fakeProgressInterval);
                showError(msg.message);
                evtSource.close();
            }

        } catch (e) {
            console.error("Error SSE:", e);
            clearInterval(fakeProgressInterval);
        }
    };

    function resetUI() {
        tableBody.innerHTML = '';
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = `<span class="flex items-center justify-center">
            <i class="fas fa-cog fa-spin mr-2"></i>
            Preparando análisis...
        </span>`;
        progressContainer.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressStatus.textContent = 'Conectando con el servidor...';
    }

    function restoreButton() {
        fetchBtn.disabled = false;
        fetchBtn.innerHTML = `<span class="flex items-center justify-center">
            <i class="fas fa-redo mr-2"></i>
            Volver a analizar
        </span>`;
    }

    function showError(message) {
        tableBody.innerHTML = `<tr>
            <td colspan="4" class="py-8 text-center text-red-500">
                <i class="fas fa-exclamation-circle mr-2"></i>
                ${message}
            </td>
        </tr>`;
        progressStatus.textContent = 'Error en el análisis';
        progressBar.classList.remove('bg-[#1a1a00]');
        progressBar.classList.add('bg-red-500');
        restoreButton();
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
                    <button onclick="copyWallet('${item.wallet}')" class="copy-btn ml-2 text-gray-400 hover:text-[#1a1a00]">
                        <i class="fas fa-copy"></i>
                    </button>
                </td>
                <td class="px-4 py-3 border-b text-center">${item['Rank leaderboard']}</td>
                <td class="px-4 py-3 border-b text-center">${item['Ganancia']}</td>
            `;
            tableBody.appendChild(row);
        });
    }
};

// Esta función debe estar en el ámbito global, no dentro del DOMContentLoaded
function copyWallet(wallet) {
    navigator.clipboard.writeText(wallet);
    const buttons = document.querySelectorAll(`button[onclick="copyWallet('${wallet}')"]`);
    buttons.forEach(btn => {
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-check text-green-500';
            setTimeout(() => {
                icon.className = 'fas fa-copy';
                icon.classList.remove('text-green-500');
            }, 2000);
        }
    });
}