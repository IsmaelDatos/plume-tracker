let cy;
let selectedNode = null;
let allNetworks = [];

async function loadNetworkData() {
    try {
        const response = await fetch('/api/network-data');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        allNetworks = await response.json();
        console.log("Loaded", allNetworks.length, "networks");
        
        if (allNetworks.length === 0) {
            console.error("No network data received");
            return;
        }
        
        initCytoscape();
        
    } catch (error) {
        console.error("Error loading network data:", error);
    }
}

function initCytoscape() {
    allNetworks.sort((a, b) => b.walletCount - a.walletCount);

    cy = cytoscape({
        container: document.getElementById('cy'),
        elements: createNetworkElements(allNetworks),
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': 'data(color)',
                    'width': 'data(size)',
                    'height': 'data(size)',
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': 'data(fontSize)',
                    'font-weight': 'bold',
                    'color': '#fff',
                    'text-outline-color': '#000',
                    'text-outline-width': '2px',
                    'border-width': '3px',
                    'border-color': '#fff',
                    'text-max-width': '60px',
                    'text-wrap': 'wrap',
                    'font-family': 'Poppins, sans-serif'
                }
            }
        ],
        layout: {
            name: "concentric",
            fit: true,
            padding: 50,
            minNodeSpacing: 50,
            concentric: node => node.data("size"),
            levelWidth: nodes => 1
        },
        minZoom: 1.0,
        maxZoom: 30.0,
        zoomingEnabled: true,
        userZoomingEnabled: true,
        panningEnabled: true,
        userPanningEnabled: true,
        wheelSensitivity: 0.05
    });

    calculateCirclePacking();
    cy.on('tap', 'node', function(event) {
        const node = event.target;
        selectNode(node);
        showInfoPanel(node.data());
    });

    cy.on('tap', function(event) {
        if (event.target === cy) hideInfoPanel();
    });

    document.getElementById('focus-largest').addEventListener('click', function() {
        const largestNode = cy.nodes().max(node => node.data('walletCount'));
        if (largestNode) {
            selectNode(largestNode);
            showInfoPanel(largestNode.data());
            cy.animate({ center: { eles: largestNode }, zoom: 2.5, duration: 800 });
        }
    });

    cy.on('mouseover', 'node', function(event){
        const node = event.target;
        const tooltip = document.createElement('div');
        tooltip.className = 'cy-tooltip';
        tooltip.innerHTML = `
            <strong style="font-size: 18px;">
                ${node.data('id').slice(0, 8)}...${node.data('id').slice(-6)}
            </strong><br>
            📊 ${node.data('walletCount').toLocaleString()} wallets<br>
            ⚠️ ${node.data('sybilPercent').toFixed(1)}% sybil risk<br>
            ⭐ ${node.data('totalXp').toLocaleString()} XP
        `;
        document.body.appendChild(tooltip);

        const updatePosition = () => {
            const pos = node.renderedPosition();
            tooltip.style.left = (pos.x + node.data('size')/2 + 15) + 'px';
            tooltip.style.top = (pos.y - tooltip.offsetHeight/2) + 'px';
        };
        updatePosition();
        node.on('position', updatePosition);
        node.tooltip = { element: tooltip, update: updatePosition };
    });

    cy.on('mouseout', 'node', function(event){
        const node = event.target;
        if (node.tooltip) {
            node.tooltip.element.remove();
            node.off('position', node.tooltip.update);
            node.tooltip = null;
        }
    });
}

function calculateCirclePacking() {
    const maxWalletCount = Math.max(...allNetworks.map(n => n.walletCount));
    const sortedNetworks = [...allNetworks].sort((a, b) => b.sybilPercent - a.sybilPercent || b.walletCount - a.walletCount);
    const nodes = cy.nodes();
    const centerX = cy.width()/2, centerY = cy.height()/2;
    const nodeSizes = sortedNetworks.map(n => 20 + (n.walletCount / maxWalletCount) * 40);
    const placed = [];

    nodes.forEach((node, index) => {
        const radius = nodeSizes[index];
        if (index === 0) { node.position({ x: centerX, y: centerY }); placed.push({ x:centerX, y:centerY, r: radius }); return; }
        let placedFlag = false, attempt = 0, circleRadius = 230;
        while (!placedFlag && attempt < 500) {
            attempt++;
            const angle = Math.random()*2*Math.PI;
            const dist = circleRadius * (0.7 + 0.4*Math.random());
            const posX = centerX + dist*Math.cos(angle);
            const posY = centerY + dist*Math.sin(angle);
            if (!placed.some(p => Math.hypot(posX - p.x, posY - p.y) < radius + p.r + 8)) {
                placedFlag = true;
                node.position({ x: posX, y: posY });
                placed.push({ x: posX, y: posY, r: radius });
            }
            if (attempt % 10 === 0) circleRadius += 10;
        }
    });
}

function createNetworkElements(networks) {
    const maxWalletCount = Math.max(...networks.map(n => n.walletCount));
    return networks.map(network => {
        const size = 40 + (network.walletCount / maxWalletCount) * 200;
        const fontSize = Math.max(10, Math.min(18, size / 6));
        return {
            data: {
                id: network.rootWalletAddress,
                label: network.rootWalletAddress.slice(0,4)+'...'+network.rootWalletAddress.slice(-4),
                walletCount: network.walletCount,
                totalXp: network.totalXp,
                sybilPercent: network.sybilPercent,
                size: size,
                color: getColorBySybilPercent(network.sybilPercent),
                fontSize: fontSize+'px'
            }
        };
    });
}

function getColorBySybilPercent(percent) {
    if (percent >= 80) return '#FF3200';
    if (percent >= 60) return '#FF5E00';
    if (percent >= 40) return '#FF8130';
    if (percent >= 20) return '#FFA05A';
    return '#FFC38B';
}

function selectNode(node) {
    if (selectedNode) selectedNode.removeClass('selected');
    selectedNode = node;
    node.addClass('selected');
}

function showInfoPanel(data) {
    const panel = document.getElementById('info-panel');
    document.getElementById('panel-wallet').textContent = data.id;
    document.getElementById('panel-wallet-count').textContent = data.walletCount.toLocaleString();
    document.getElementById('panel-total-xp').textContent = data.totalXp.toLocaleString();
    document.getElementById('panel-sybil-percent').textContent = data.sybilPercent.toFixed(1)+'%';
    document.getElementById('panel-avg-xp').textContent = Math.round(data.totalXp/data.walletCount).toLocaleString();
    panel.classList.remove('hidden');
}

function hideInfoPanel() {
    const panel = document.getElementById('info-panel');
    panel.classList.add('hidden');
    if (selectedNode) { selectedNode.removeClass('selected'); selectedNode=null; }
}

function showResult(message, type) {
    const resultDiv = document.getElementById('sybil-result');
    const resultContent = document.getElementById('result-content');
    resultContent.innerHTML = message;
    resultDiv.className = 'p-4 rounded-lg border ';
    switch(type){
        case 'error': resultDiv.className += 'bg-red-50 border-red-200 text-red-800'; break;
        case 'loading': resultDiv.className += 'bg-blue-50 border-blue-200 text-blue-800'; break;
        case 'sybil': resultDiv.className += 'bg-red-50 border-red-200 text-red-800'; break;
        case 'clean': resultDiv.className += 'bg-green-50 border-green-200 text-green-800'; break;
        case 'not-found': resultDiv.className += 'bg-yellow-50 border-yellow-200 text-yellow-800'; break;
        default: resultDiv.className += 'bg-gray-50 border-gray-200 text-gray-800';
    }
    resultDiv.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    loadNetworkData();
    document.getElementById('zoom-in').addEventListener('click', () => {
        if (cy) cy.zoom(cy.zoom() * 1.5);
    });
    
    document.getElementById('zoom-out').addEventListener('click', () => {
        if (cy) cy.zoom(cy.zoom() / 1.5);
    });
    
    document.getElementById('reset-view').addEventListener('click', () => {
        if (cy) { cy.fit(); cy.zoom(1.2); }
    });
    
    document.getElementById('sybil-check-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const walletAddress = document.getElementById('wallet-address').value.trim();
        if (!walletAddress) return showResult('Please enter a wallet address', 'error');
        if (!walletAddress.startsWith('0x') || walletAddress.length !== 42) return showResult('Invalid wallet address format. Must start with 0x and be 42 characters long.', 'error');
        
        showResult('Checking wallet status...', 'loading');
        try {
            const response = await fetch('/check-sybil', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ 'wallet_address': walletAddress })
            });
            const data = await response.json();
            if (response.ok) {
                if (data.found) {
                    const isSybil = data.sybilFlag.toLowerCase() === 'true';
                    const icon = isSybil ? '⛔' : '✅';
                    const statusText = isSybil ? 'SYBIL DETECTED' : 'NOT A SYBIL';
                    const statusClass = isSybil ? 'text-red-600' : 'text-green-600';
                    showResult(`
                        <div class="text-center">
                            <div class="text-4xl mb-2">${icon}</div>
                            <div class="text-xl font-bold ${statusClass} mb-2">${statusText}</div>
                            <div class="text-sm text-gray-600 break-all">${data.walletAddress}</div>
                            <div class="mt-3 text-sm">Sybil Flag: <span class="font-semibold">${data.sybilFlag}</span></div>
                        </div>
                    `, isSybil ? 'sybil' : 'clean');
                } else {
                    showResult(`
                        <div class="text-center">
                            <div class="text-2xl mb-2">🤔</div>
                            <div class="text-lg font-semibold text-yellow-600 mb-2">Wallet Not Found</div>
                            <div class="text-sm text-gray-600">This wallet is not in our Sybil database</div>
                        </div>
                    `, 'not-found');
                }
            } else showResult(data.error || 'Error checking wallet status', 'error');
        } catch (err) {
            showResult('Network error. Please try again.', 'error');
        }
    });
    
    document.getElementById('close-result').addEventListener('click', function() {
        document.getElementById('sybil-result').classList.add('hidden');
    });
});