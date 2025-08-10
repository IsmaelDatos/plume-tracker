// Versión mejorada con más control de errores
console.log("Script s2_calculator.js cargado");

function calculateAirdrop() {
    try {
        console.log("Ejecutando calculateAirdrop");
        
        const userPp = parseFloat(document.getElementById('user-pp').value) || 0;
        const plumePrice = parseFloat(document.getElementById('plume-price').value) || 0;
        const plumePerPpText = document.querySelector('.font-mono').textContent;
        const plumePerPp = parseFloat(plumePerPpText) || 0;
        
        console.log("Valores obtenidos:", {
            userPp,
            plumePrice,
            plumePerPp,
            plumePerPpText
        });

        const plumeEstimate = userPp * plumePerPp;
        const usdEstimate = plumeEstimate * plumePrice;
        
        document.getElementById('estimated-plume').textContent = plumeEstimate.toFixed(6);
        document.getElementById('estimated-usd').textContent = `$${usdEstimate.toFixed(2)}`;
        
        console.log("Cálculo completado", {
            plumeEstimate,
            usdEstimate
        });
    } catch (error) {
        console.error("Error en calculateAirdrop:", error);
    }
}

document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM completamente cargado");
    
    const calculateBtn = document.getElementById('calculate-btn');
    console.log("Botón encontrado:", calculateBtn);
    
    if (calculateBtn) {
        calculateBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("Click en botón detectado");
            calculateAirdrop();
        });
        document.getElementById('user-pp').addEventListener('input', calculateAirdrop);
        document.getElementById('plume-price').addEventListener('input', calculateAirdrop);
        calculateAirdrop();
    } else {
        console.error("No se encontró el botón calculate-btn");
    }
});

window.calculateAirdrop = calculateAirdrop;