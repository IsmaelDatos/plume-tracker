console.log("wallet-analytics.js cargado correctamente ✅");

if (!window.WalletAnalyticsLoaded) {
    window.WalletAnalyticsLoaded = true;

    document.addEventListener("DOMContentLoaded", async () => {
        // === Get wallet from URL ===
        const urlParts = window.location.pathname.split('/');
        const walletAddressFromURL = urlParts.length >= 3 ? urlParts[2] : null;
        const walletAddress = walletAddressFromURL || window.walletAddress || "0xE3c55E0c1E9170d9531Fb6A5F9c6442AD46D50F4";
        
        console.log("🔍 Wallet detectada:", walletAddress);

        const apiUrl = `/api/wallet/${walletAddress}/analytics`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error(`Error HTTP ${response.status}`);

            const data = await response.json();
            console.log("📊 Datos recibidos de la API:", data);

            // === Update main metrics ===
            document.getElementById("total-fees-plume").textContent = `${data.total_plume.toFixed(2)} PLUME`;
            document.getElementById("total-fees-usd").textContent = `$${data.total_usd.toFixed(2)}`;
            document.getElementById("total-transactions").textContent = data.total_txn;

            // === Last active day ===
            const lastActiveFee = [...data.daily_fees].reverse().find(d => d.fee_plume > 0);
            const lastActiveTxn = [...data.daily_txn].reverse().find(d => d.tx_count > 0);
            const lastActiveDate = lastActiveFee?.date || lastActiveTxn?.date || "(Date)";
            
            document.getElementById("last-day-date").textContent = lastActiveDate;
            document.getElementById("last-day-fees").textContent = lastActiveFee
                ? `Fees: ${lastActiveFee.fee_plume.toFixed(2)} PLUME`
                : "Fees: -- PLUME";
            document.getElementById("last-day-txs").textContent = lastActiveTxn
                ? `Transactions: ${lastActiveTxn.tx_count}`
                : "Transactions: --";

            // === Transform arrays for Plotly ===
            const weeklyFees = data.weekly_fees.map(d => d.fee_plume);
            const weeklyTxn = data.weekly_txn.map(d => d.tx_count);
            const dailyFees = data.daily_fees.map(d => d.fee_plume);
            const dailyTxn = data.daily_txn.map(d => d.tx_count);
            const dailyLabels = data.daily_fees.map(d => d.date);
            const weeklyLabels = data.weekly_fees.map(d => d.semana_custom);

            // === Render bar charts ===
            renderBarChart("weeklyFeesChart", weeklyLabels, weeklyFees, "#ef4444", "PLUME");
            renderBarChart("weeklyTxnChart", weeklyLabels, weeklyTxn, "#3b82f6", "Transactions");
            renderBarChart("dailyFeesChart", dailyLabels, dailyFees, "#ef4444", "PLUME");
            renderBarChart("dailyTxnChart", dailyLabels, dailyTxn, "#3b82f6", "Transactions");

        } catch (err) {
            console.error("❌ Error al obtener o renderizar datos:", err);
            alert("Error cargando Wallet Analytics. Revisa la consola.");
        }
    });

    function renderBarChart(divId, labels, values, color, yAxisTitle) {
        const trace = {
            x: labels,
            y: values,
            type: 'bar',
            marker: { color: color },
            text: values.map(v => v.toFixed(2)),
            textposition: 'auto',
            hovertemplate: '%{y}<extra></extra>'
        };

        const layout = {
            margin: { t: 20, b: 40, l: 60, r: 20 },
            yaxis: { title: yAxisTitle, rangemode: 'tozero' },
            xaxis: { title: divId.includes("weekly") ? "Week" : "Date" },
            showlegend: false,
            height: 300
        };

        Plotly.newPlot(divId, [trace], layout, { responsive: true });
    }
}