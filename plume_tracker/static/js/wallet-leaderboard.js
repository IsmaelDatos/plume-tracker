document.addEventListener('DOMContentLoaded', () => {
  const loadBtn = document.getElementById('load-more-leaderboard');
  const lessBtn = document.getElementById('load-less-leaderboard');
  
  if (!loadBtn) return;

  const tbody = document.getElementById('leaderboard-body');
  if (!tbody) {
    console.warn('No leaderboard tbody found');
    return;
  }

  // Guardamos las filas añadidas dinámicamente
  let addedRows = [];

  const formatInt = (v) => {
    const n = Number(v || 0);
    return isNaN(n) ? '0' : Math.round(n).toLocaleString();
  };

  const formatFloat = (v, decimals = 2) => {
    const n = Number(v || 0);
    return isNaN(n) ? '0.00' : n.toLocaleString(undefined, { 
      minimumFractionDigits: decimals, 
      maximumFractionDigits: decimals 
    });
  };

  const formatCurrency = (v) => {
    const n = Number(v || 0);
    return isNaN(n) ? '$0.00' : '$' + n.toLocaleString(undefined, { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
  };

  // Función: construir una fila de tabla
  const buildRow = (item, wallet, target_totalxp) => {
    const isTarget = item.walletAddress && (item.walletAddress.toLowerCase() === (wallet || '').toLowerCase());
    const tr = document.createElement('tr');
    tr.className = isTarget ? 'bg-gray-100 font-medium added-row' : 'hover:bg-gray-50 added-row';

    // Calcular pointsDifference si no viene del API
    let pointsDifference = item.pointsDifference;
    if (pointsDifference === undefined && target_totalxp) {
      pointsDifference = item.totalXp - Number(target_totalxp);
    }

    let pdHtml = '<span class="text-gray-500">-</span>';
    if (!isTarget && pointsDifference !== null && pointsDifference !== undefined) {
      const pd = Number(pointsDifference) || 0;
      const pdClass = pd > 0 ? 'text-green-600' : 'text-red-600';
      const sign = pd > 0 ? '+' : '';
      pdHtml = `<span class="${pdClass}">${sign}${Math.round(pd).toLocaleString()}</span>`;
    }

    tr.innerHTML = `
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
        ${item.xpRank || 0}
        ${isTarget ? '<span class="ml-1 text-[#FF3200]">(YOU)</span>' : ''}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm font-mono">
        ${item.walletAddress.slice(0, 6)}...${item.walletAddress.slice(-4)}
        <button onclick="copyWallet('${item.walletAddress}')" class="copy-btn ml-2 text-gray-400 hover:text-[#FF3200]">
          <i class="fas fa-copy"></i>
        </button>
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
        ${formatInt(item.totalXp)}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
        ${formatCurrency(item.TVL)}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
        ${formatInt(item.userSelfXp)}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
        ${formatInt(item.referralBonusXp)}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
        ${formatFloat(item.currentPlumeStakingTotalTokens, 2)}
      </td>
      <td class="px-4 py-3 whitespace-nowrap text-sm text-right">
        ${pdHtml}
      </td>
    `;
    return tr;
  };

  // Mostrar más
  loadBtn.addEventListener('click', async () => {
    loadBtn.disabled = true;
    const originalText = loadBtn.textContent;
    loadBtn.textContent = 'Loading...';

    try {
      const wallet = loadBtn.dataset.wallet || '';
      let offset = parseInt(loadBtn.dataset.offset || '0', 10);
      const count = parseInt(loadBtn.dataset.count || '10', 10);
      const target_totalxp = loadBtn.dataset.targetTotalxp || 0;

      const resp = await fetch(`/api/leaderboard/more?wallet=${encodeURIComponent(wallet)}&offset=${offset}&count=${count}&target_totalxp=${encodeURIComponent(target_totalxp)}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const js = await resp.json();
      const rows = js.leaderboard || [];

      if (rows.length === 0) {
        loadBtn.textContent = 'No more results';
        loadBtn.disabled = true;
        return;
      }

      // Añadir filas y guardarlas
      rows.forEach(item => {
        const row = buildRow(item, wallet, target_totalxp);
        tbody.appendChild(row);
        addedRows.push(row);
      });

      // Actualizar offset
      loadBtn.dataset.offset = (offset + count).toString();

      // Mostrar botón "Show less" si hay filas añadidas
      if (addedRows.length > 0 && lessBtn) {
        lessBtn.classList.remove('hidden');
      }

      // Si recibimos menos filas de las solicitadas, deshabilitar "Show more"
      if (rows.length < count) {
        loadBtn.textContent = 'No more results';
        loadBtn.disabled = true;
      } else {
        loadBtn.textContent = originalText;
        loadBtn.disabled = false;
      }

    } catch (err) {
      console.error('Error loading more leaderboard:', err);
      loadBtn.textContent = 'Error';
      setTimeout(() => {
        loadBtn.textContent = 'Show more';
        loadBtn.disabled = false;
      }, 2000);
    }
  });

  // Mostrar menos (solo si el botón existe)
if (lessBtn) {
    lessBtn.addEventListener('click', () => {
      // Eliminar filas añadidas
      addedRows.forEach(r => {
        if (r.parentNode) {
          r.parentNode.removeChild(r);
        }
      });
      addedRows = [];

      // RESTAURAR OFFSET AL VALOR ORIGINAL
      loadBtn.dataset.offset = loadBtn.dataset.originalOffset;

      // Ocultar botón "Show less"
      lessBtn.classList.add('hidden');

      // Restaurar estado del botón "Show more"
      loadBtn.textContent = 'Show more';
      loadBtn.disabled = false;
    });
  }
});