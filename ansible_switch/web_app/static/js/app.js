/* ──────────────────────────────────────────────────────────────────────────────
   Ansible Switch Manager Web Interface - Frontend Logic
   ────────────────────────────────────────────────────────────────────────────── */

// ─── State ───
let currentPingMode = 'switch';
let currentDiscoveryIP = null;
let discoveryRefreshInterval = null;
let discoveryAutoRefreshEnabled = true;
let pingResultsCache = {}; // Persist ping results across refreshes: { ip: '✅✅' | '❌❌' }
let currentModule = 1;

// ─── API Helper ───
async function api(endpoint, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
    };
    const response = await fetch(`/api${endpoint}`, { ...defaults, ...options });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

// ─── Navigation ───
function navigateTo(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const targetView = document.getElementById(`view-${view}`);
    if (targetView) {
        targetView.classList.add('active');
    }

    const targetBtn = document.querySelector(`.nav-btn[data-view="${view}"]`);
    if (targetBtn) {
        targetBtn.classList.add('active');
    }

    // Clear discovery interval when leaving
    if (view !== 'discovery' && discoveryRefreshInterval) {
        clearInterval(discoveryRefreshInterval);
        discoveryRefreshInterval = null;
        pingResultsCache = {};
    }

    // View-specific initialization
    if (view === 'home') loadTopology();
    if (view === 'assign') loadAssignView();
    if (view === 'ping') loadPingView();
    if (view === 'ping-all') resetPingAllView();
    if (view === 'discovery') startDiscovery();
    if (view === 'ipconfig') loadIpconfigView();
    if (view === 'traceroute') loadTracerouteView();
    if (view === 'arp') loadArpView();
    if (view === 'netstat') loadNetstatView();
}

// ─── Topology ───
async function loadTopology() {
    try {
        const [topoData, configData, moduleData] = await Promise.all([
            api('/topology'),
            api('/config-ip'),
            api('/module'),
        ]);
        currentModule = moduleData.module;
        renderTopology(topoData.switches, configData.config_ip);
        updateModuleToggleBtn(moduleData);
    } catch (err) {
        console.error('Failed to load topology:', err);
    }
}

async function toggleModule() {
    try {
        const moduleData = await api('/module', { method: 'POST' });
        currentModule = moduleData.module;
        updateModuleToggleBtn(moduleData);
        await loadTopology();
        pingResultsCache = {};
    } catch (err) {
        console.error('Failed to toggle module:', err);
    }
}

function updateModuleToggleBtn(data) {
    const btn = document.getElementById('module-toggle-btn');
    if (btn) {
        btn.textContent = `🔄 Module: ${data.module} (${data.description})`;
    }
    const label = document.getElementById('menu-module-label');
    if (label) {
        label.textContent = `Toggle architecture module (current: [${data.module}] ${data.description}) [X]`;
    }
}

function renderTopology(switches, configIp) {
    const container = document.getElementById('topology-tree');
    let html = '';
    let prevTier = null;

    if (currentModule === 2) {
        // Module 2: VLAN 1, MGMT, VLAN 2 sections
        const vlan1 = switches.filter(s => s.vlan === 1);
        const mgmt = switches.filter(s => s.vlan === 0);
        const vlan2 = switches.filter(s => s.vlan === 2);

        // VLAN 1
        html += `<div class="module-2-vlan-section">`;
        html += `<div class="module-2-vlan-label">[ VLAN 1 ]</div>`;
        prevTier = null;
        vlan1.forEach(sw => {
            if (sw.tier !== prevTier) {
                html += `<div class="tier-header">    ── Tier ${sw.tier} ──</div>`;
                prevTier = sw.tier;
            }
            const siblings = vlan1.filter(s => s.tier === sw.tier);
            const isLast = siblings[siblings.length - 1].name === sw.name;
            const connector = isLast ? '└──' : '├──';
            html += `
                <div class="tier-item">
                    <span class="tier-connector">      ${connector}</span>
                    <span class="tier-name">${sw.name}</span>
                    <span class="tier-ip">IP: ${sw.switch_ip}</span>
                    <span class="tier-role">[${sw.switch_role}]</span>
                </div>
            `;
        });
        html += `</div>`;

        // MGMT
        html += `<div class="module-2-vlan-section">`;
        html += `<div class="module-2-mgmt-label">[ MGMT ]</div>`;
        mgmt.forEach(sw => {
            html += `
                <div class="tier-item">
                    <span class="tier-connector">    └──</span>
                    <span class="tier-name">${sw.name}</span>
                    <span class="tier-ip">IP: ${sw.switch_ip}</span>
                    <span class="tier-role">[management]</span>
                </div>
            `;
        });
        html += `</div>`;

        // VLAN 2
        html += `<div class="module-2-vlan-section">`;
        html += `<div class="module-2-vlan-label">[ VLAN 2 ]</div>`;
        prevTier = null;
        vlan2.forEach(sw => {
            if (sw.tier !== prevTier) {
                html += `<div class="tier-header">    ── Tier ${sw.tier} ──</div>`;
                prevTier = sw.tier;
            }
            const siblings = vlan2.filter(s => s.tier === sw.tier);
            const isLast = siblings[siblings.length - 1].name === sw.name;
            const connector = isLast ? '└──' : '├──';
            html += `
                <div class="tier-item">
                    <span class="tier-connector">      ${connector}</span>
                    <span class="tier-name">${sw.name}</span>
                    <span class="tier-ip">IP: ${sw.switch_ip}</span>
                    <span class="tier-role">[${sw.switch_role}]</span>
                </div>
            `;
        });
        html += `</div>`;
    } else {
        // Module 1: standard tree display
        switches.forEach(sw => {
            if (sw.tier !== prevTier) {
                const tierLabel = sw.tier === 'MGMT' ? '[ MGMT ]' : `[ Tier ${sw.tier} ]`;
                html += `<div class="tier-header">  │  ${tierLabel}</div>`;
                prevTier = sw.tier;
            }

            const siblings = switches.filter(s => s.tier === sw.tier);
            const isLast = siblings[siblings.length - 1].name === sw.name;
            const connector = isLast ? '└──' : '├──';

            html += `
                <div class="tier-item">
                    <span class="tier-connector">  │    ${connector}</span>
                    <span class="tier-name">${sw.name}</span>
                    <span class="tier-ip">IP: ${sw.switch_ip}</span>
                    <span class="tier-role">[${sw.switch_role}]</span>
                </div>
            `;
        });
    }

    container.innerHTML = html;

    // Config page row
    const configRow = document.getElementById('config-page-row');
    configRow.innerHTML = `
        <div class="tier-item config-item">
            <span class="tier-connector">  │    └──</span>
            <span class="tier-name">CONFIG</span>
            <span class="tier-ip"><a href="http://${configIp}" target="_blank" rel="noopener noreferrer" class="config-link">${configIp}</a></span>
            <span class="tier-role">[Web Page]</span>
        </div>
    `;
}

// ─── Reset IPs ───
async function resetIPs() {
    try {
        const data = await api('/reset-ips', { method: 'POST' });
        showMessage('home', data.message, 'success');
        await loadTopology();
    } catch (err) {
        showMessage('home', `✗ ${err.message}`, 'error');
    }
}

// ─── Assign IP View ───
async function loadAssignView() {
    try {
        const data = await api('/switches');
        const listContainer = document.getElementById('assign-switch-list');
        const select = document.getElementById('assign-select');

        // Build switch list display
        let listHtml = '';
        data.switches.forEach((sw, idx) => {
            listHtml += `
                <div class="switch-list-item">
                    <span class="switch-list-num">${idx + 1}.</span>
                    <span class="switch-list-name">${sw.name}</span>
                    <span class="switch-list-ip">${sw.ip}</span>
                </div>
            `;
        });
        listContainer.innerHTML = listHtml;

        // Build select options
        select.innerHTML = '<option value="">-- Choose a switch --</option>';
        data.switches.forEach(sw => {
            select.innerHTML += `<option value="${sw.name}">${sw.name} (${sw.ip})</option>`;
        });

        // Clear previous input and messages
        document.getElementById('assign-ip-input').value = '';
        hideMessage('assign');
    } catch (err) {
        console.error('Failed to load assign view:', err);
    }
}

async function assignIP() {
    const switchName = document.getElementById('assign-select').value;
    const newIP = document.getElementById('assign-ip-input').value.trim();

    if (!switchName) {
        showMessage('assign', '✗ Please select a switch', 'error');
        return;
    }

    if (!newIP) {
        showMessage('assign', '✗ Please enter an IP address', 'error');
        return;
    }

    if (!isValidIP(newIP)) {
        showMessage('assign', `✗ '${newIP}' is not a valid IPv4 address`, 'error');
        return;
    }

    try {
        const data = await api('/assign-ip', {
            method: 'POST',
            body: JSON.stringify({ switch_name: switchName, new_ip: newIP }),
        });
        showMessage('assign', `✔ ${data.message}`, 'success');
        document.getElementById('assign-ip-input').value = '';
        await loadAssignView();
    } catch (err) {
        showMessage('assign', `✗ ${err.message}`, 'error');
    }
}

// ─── Ping View ───
async function loadPingView() {
    try {
        const data = await api('/switches');
        const select = document.getElementById('ping-switch-select');
        select.innerHTML = '<option value="">-- Choose a switch --</option>';
        data.switches.forEach(sw => {
            select.innerHTML += `<option value="${sw.name}">${sw.name} (${sw.ip})</option>`;
        });

        // Reset outputs
        document.getElementById('ping-output').classList.add('hidden');
        document.getElementById('ping-result').innerHTML = '';
    } catch (err) {
        console.error('Failed to load ping view:', err);
    }
}

function setPingMode(mode) {
    currentPingMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    document.getElementById('ping-switch-section').classList.toggle('hidden', mode !== 'switch');
    document.getElementById('ping-custom-section').classList.toggle('hidden', mode !== 'custom');
}

async function doPing() {
    let target;
    const count = parseInt(document.getElementById('ping-count').value) || 4;

    if (currentPingMode === 'switch') {
        const switchName = document.getElementById('ping-switch-select').value;
        if (!switchName) {
            showMessage('ping', '✗ Please select a switch', 'error');
            return;
        }
        // Get IP from topology
        const topologyData = await api('/topology');
        const sw = topologyData.switches.find(s => s.name === switchName);
        if (!sw || sw.switch_ip === 'N/A' || !sw.switch_ip) {
            showMessage('ping', `✗ ${switchName} has no IP configured`, 'error');
            return;
        }
        target = sw.switch_ip;
    } else {
        target = document.getElementById('ping-custom-input').value.trim();
        if (!target) {
            showMessage('ping', '✗ Please enter a hostname or IP address', 'error');
            return;
        }
    }

    const outputDiv = document.getElementById('ping-output');
    const resultPre = document.getElementById('ping-result');
    outputDiv.classList.remove('hidden');
    resultPre.innerHTML = '';

    try {
        const data = await api('/ping', {
            method: 'POST',
            body: JSON.stringify({ target, count }),
        });

        // Render each line with appropriate color
        let html = '';
        if (data.lines && data.lines.length > 0) {
            data.lines.forEach(line => {
                html += `<span class="line-${line.type}">${escapeHtml(line.text)}</span>\n`;
            });
        } else {
            html = `<span class="line-info">${escapeHtml(data.output)}</span>`;
        }
        resultPre.innerHTML = html;
    } catch (err) {
        resultPre.innerHTML = `<span class="line-timeout">✗ ${escapeHtml(err.message)}</span>`;
    }
}

// ─── Ping All View ───
function resetPingAllView() {
    document.getElementById('ping-all-output').classList.add('hidden');
    document.getElementById('ping-all-summary').classList.add('hidden');
    document.getElementById('ping-all-progress').classList.add('hidden');
}

async function doPingAll() {
    const count = parseInt(document.getElementById('ping-all-count').value) || 2;
    const progress = document.getElementById('ping-all-progress');
    const progressFill = progress.querySelector('.progress-fill');
    const progressText = progress.querySelector('.progress-text');
    const outputDiv = document.getElementById('ping-all-output');
    const resultPre = document.getElementById('ping-all-result');
    const summaryDiv = document.getElementById('ping-all-summary');
    const tbody = document.getElementById('ping-all-tbody');

    outputDiv.classList.add('hidden');
    summaryDiv.classList.add('hidden');
    progress.classList.remove('hidden');
    progressFill.style.width = '10%';
    progressText.textContent = 'Starting ping sweep...';

    try {
        // Start sequential pings with progress updates
        const topologyData = await api('/topology');
        const switches = topologyData.switches;
        const results = [];

        for (let i = 0; i < switches.length; i++) {
            const sw = switches[i];
            const percent = Math.round(((i + 1) / switches.length) * 100);
            progressFill.style.width = `${percent}%`;
            progressText.textContent = `Pinging ${sw.name} (${sw.switch_ip})...`;

            if (!sw.switch_ip || sw.switch_ip === 'N/A') {
                results.push({ switch_name: sw.name, ip: sw.switch_ip, status: 'no_ip', success: null, lines: [] });
                continue;
            }

            const pingData = await api('/ping', {
                method: 'POST',
                body: JSON.stringify({ target: sw.switch_ip, count }),
            });

            results.push({
                switch_name: sw.name,
                ip: sw.switch_ip,
                status: pingData.success ? 'up' : 'down',
                success: pingData.success,
                lines: pingData.lines,
            });
        }

        progress.classList.add('hidden');

        // Show individual results
        let outputHtml = '';
        results.forEach(r => {
            const statusIcon = r.status === 'no_ip' ? '⚠' : r.success ? '✅' : r.status === 'unreachable_but_blocked' ? '⚠' : '❌';
            const statusText = r.status === 'no_ip' ? 'no IP configured' : r.success ? 'Reachable' : r.status === 'unreachable_but_blocked' ? 'REACHABLE (blocked)' : 'Unreachable';
            outputHtml += `\n── ${r.switch_name} (${r.ip}) ${statusIcon} ${statusText}\n`;
            if (r.status === 'unreachable_but_blocked') {
                outputHtml += `    ⚠ DIAGNOSTIC: Host ${r.ip} is reachable but actively rejecting connections.\n`;
            }
            if (r.lines && r.lines.length > 0) {
                r.lines.forEach(line => {
                    outputHtml += `<span class="line-${line.type}">  ${escapeHtml(line.text)}</span>\n`;
                });
            }
            outputHtml += '─'.repeat(58) + '\n';
        });
        resultPre.innerHTML = outputHtml;
        outputDiv.classList.remove('hidden');

        // Show summary table
        tbody.innerHTML = '';
        results.forEach(r => {
            let statusClass, statusText;
            if (r.status === 'no_ip') {
                statusClass = 'status-no-ip';
                statusText = 'NO IP';
            } else if (r.success) {
                statusClass = 'status-up';
                statusText = 'UP ✅';
            } else if (r.status === 'unreachable_but_blocked') {
                statusClass = 'status-blocked';
                statusText = 'UP (BLOCKED) ⚠';
            } else {
                statusClass = 'status-down';
                statusText = 'DOWN ❌';
            }
            tbody.innerHTML += `
                <tr>
                    <td>${r.switch_name}</td>
                    <td>${r.ip || '—'}</td>
                    <td class="${statusClass}">${statusText}</td>
                </tr>
            `;
        });
        summaryDiv.classList.remove('hidden');

    } catch (err) {
        progress.classList.add('hidden');
        resultPre.innerHTML = `<span class="line-timeout">✗ ${escapeHtml(err.message)}</span>`;
        outputDiv.classList.remove('hidden');
    }
}

// ─── Discovery View ───
async function startDiscovery() {
    discoveryAutoRefreshEnabled = true;
    updateRefreshToggleButton();
    await refreshDiscovery();
    if (discoveryRefreshInterval) {
        clearInterval(discoveryRefreshInterval);
    }
    discoveryRefreshInterval = setInterval(() => {
        if (discoveryAutoRefreshEnabled) {
            refreshDiscovery();
        }
    }, 5000);
}

function toggleDiscoveryRefresh() {
    discoveryAutoRefreshEnabled = !discoveryAutoRefreshEnabled;
    updateRefreshToggleButton();
    const badge = document.getElementById('discovery-status-badge');
    if (!discoveryAutoRefreshEnabled) {
        badge.textContent = 'AUTO-REFRESH PAUSED';
        badge.className = 'status-badge paused';
        setTimeout(() => badge.classList.add('hidden'), 3000);
    }
}

function updateRefreshToggleButton() {
    const btn = document.getElementById('discovery-refresh-toggle');
    if (!btn) return;
    if (discoveryAutoRefreshEnabled) {
        btn.textContent = '⏸ Pause Auto-Refresh';
        btn.classList.remove('paused');
    } else {
        btn.textContent = '▶ Resume Auto-Refresh';
        btn.classList.add('paused');
    }
}

function showBadge(text, type) {
    const badge = document.getElementById('discovery-status-badge');
    badge.textContent = text;
    badge.className = `status-badge ${type}`;
}

function hideBadge() {
    const badge = document.getElementById('discovery-status-badge');
    badge.className = 'status-badge hidden';
}

async function refreshDiscovery() {
    showBadge('REFRESHING...', 'active');
    try {
        const data = await api('/discovery');
        hideBadge();
        renderDiscovery(data);
    } catch (err) {
        showBadge('REFRESH FAILED', 'error');
        setTimeout(hideBadge, 3000);
        console.error('Failed to refresh discovery:', err);
    }
}

async function scanNetwork() {
    showBadge('SCANNING...', 'active');
    try {
        // Call discovery with scan parameter to trigger ping sweep
        const data = await api('/discovery?scan=true');
        hideBadge();
        renderDiscovery(data);
    } catch (err) {
        showBadge('SCAN FAILED', 'error');
        setTimeout(hideBadge, 3000);
        console.error('Failed to scan network:', err);
    }
}

async function pingDiscoveryDevice(ip) {
    const btnId = 'ping-btn-' + ip.replace(/\./g, '-');
    const btn = document.getElementById(btnId);
    if (!btn) return;

    btn.textContent = '...';
    btn.disabled = true;
    btn.classList.remove('ping-result');

    try {
        const data = await api('/ping', {
            method: 'POST',
            body: JSON.stringify({ target: ip, count: 2 }),
        });

        btn.classList.add('ping-result');
        if (data.success) {
            btn.textContent = '✅✅';
            pingResultsCache[ip] = '✅✅';
        } else {
            btn.textContent = '❌❌';
            pingResultsCache[ip] = '❌❌';
        }
    } catch (err) {
        btn.classList.add('ping-result');
        btn.textContent = '❌❌';
        pingResultsCache[ip] = '❌❌';
    }

    setTimeout(() => {
        btn.textContent = pingResultsCache[ip] || 'Ping';
        btn.disabled = false;
        if (pingResultsCache[ip]) {
            btn.classList.add('ping-result');
        }
    }, 2000);
}

function renderDiscovery(data) {
    const subnetEl = document.getElementById('discovery-subnets');
    if (subnetEl) {
        subnetEl.textContent = `Subnets: ${data.subnets.join(', ')}`;
    }

    const tbody = document.getElementById('discovery-tbody');
    if (!tbody) {
        console.error('discovery-tbody not found');
        return;
    }

    let html = '';

    // Known devices
    if (data.known_devices && data.known_devices.length > 0) {
        data.known_devices.forEach(dev => {
            const statusClass = dev.status === 'online' ? 'device-status-online' : 'device-status-offline';
            const statusText = dev.status === 'online' ? 'ONLINE' : 'OFFLINE';
            const btnId = 'ping-btn-' + dev.ip.replace(/\./g, '-');
            const cachedResult = pingResultsCache[dev.ip];
            const pingBtnText = cachedResult || 'Ping';
            const pingBtnClass = cachedResult ? 'device-assign-btn ping-result' : 'device-assign-btn';
            html += `
                <tr>
                    <td class="${statusClass}">${statusText}</td>
                    <td class="device-ip">${dev.ip}</td>
                    <td class="device-mac">${dev.mac}</td>
                    <td class="device-name">${dev.switch_name}</td>
                    <td><button id="${btnId}" class="${pingBtnClass}" onclick="pingDiscoveryDevice('${dev.ip}')">${pingBtnText}</button></td>
                </tr>
            `;
        });
    }

    // Other discovered devices
    if (data.other_devices && data.other_devices.length > 0) {
        data.other_devices.forEach(dev => {
            const btnId = 'ping-btn-' + dev.ip.replace(/\./g, '-');
            const cachedResult = pingResultsCache[dev.ip];
            const pingBtnText = cachedResult || 'Ping';
            const pingBtnClass = cachedResult ? 'device-assign-btn ping-btn ping-result' : 'device-assign-btn ping-btn';
            html += `
                <tr>
                    <td class="device-status-discovered">DISCOVERED</td>
                    <td class="device-ip">${dev.ip}</td>
                    <td class="device-mac">${dev.mac}</td>
                    <td class="dim-text">—</td>
                    <td>
                        <button class="device-assign-btn" onclick="openAssignModal('${dev.ip}')">Assign</button>
                        <button id="${btnId}" class="${pingBtnClass}" onclick="pingDiscoveryDevice('${dev.ip}')">${pingBtnText}</button>
                    </td>
                </tr>
            `;
        });
    }

    if (!html) {
        html = '<tr><td colspan="5" class="dim-text">No devices discovered. Click "Scan Network" to scan.</td></tr>';
    }

    tbody.innerHTML = html;

    // Populate assign dropdowns
    populateSwitchSelects(data.known_devices || []);
}

function populateSwitchSelects(knownDevices) {
    const knownNames = new Set(knownDevices.map(d => d.switch_name));
    const allSelects = ['assign-discovery-select'];

    allSelects.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        // Keep current value
        const currentVal = select.value;
        // Re-populate
        select.innerHTML = '<option value="">-- Choose a switch --</option>';
        // We need all switches - fetch from topology
        api('/switches').then(data => {
            data.switches.forEach(sw => {
                const assigned = knownNames.has(sw.name) ? ' [assigned]' : '';
                select.innerHTML += `<option value="${sw.name}">${sw.name}${assigned}</option>`;
            });
            select.value = currentVal;
        });
    });
}

// ─── Ping discovered device ───
async function openAssignPanel() {
    const panel = document.getElementById('assign-discovery-panel');
    panel.classList.remove('hidden');
    document.getElementById('assign-discovery-ip-input').value = '';
    hideMessage('assign-discovery');
    await populateAssignPanelSwitches();
}

function closeAssignPanel() {
    document.getElementById('assign-discovery-panel').classList.add('hidden');
}

async function populateAssignPanelSwitches() {
    const select = document.getElementById('assign-discovery-switch-select');
    select.innerHTML = '<option value="">-- Choose a switch --</option>';
    try {
        const data = await api('/switches');
        data.switches.forEach(sw => {
            select.innerHTML += `<option value="${sw.name}">${sw.name} (${sw.ip})</option>`;
        });
    } catch (err) {
        console.error('Failed to populate switch select:', err);
    }
}

async function confirmAssignDiscoveryPanel() {
    const targetIP = document.getElementById('assign-discovery-ip-input').value.trim();
    const switchName = document.getElementById('assign-discovery-switch-select').value;

    if (!targetIP) {
        showMessage('assign-discovery', '✗ Enter a discovered IP address', 'error');
        return;
    }
    if (!isValidIP(targetIP)) {
        showMessage('assign-discovery', `✗ '${targetIP}' is not a valid IPv4 address`, 'error');
        return;
    }
    if (!switchName) {
        showMessage('assign-discovery', '✗ Please select a switch', 'error');
        return;
    }

    // Verify IP exists in the current discovery list
    const discoveryData = await api('/discovery');
    const allDiscoveredIPs = new Set();
    discoveryData.known_devices.forEach(d => allDiscoveredIPs.add(d.ip));
    discoveryData.other_devices.forEach(d => allDiscoveredIPs.add(d.ip));

    if (!allDiscoveredIPs.has(targetIP)) {
        showMessage('assign-discovery', `✗ IP '${targetIP}' not found in discovery list`, 'error');
        return;
    }

    try {
        const data = await api('/discovery/assign', {
            method: 'POST',
            body: JSON.stringify({ discovered_ip: targetIP, switch_name: switchName }),
        });
        showMessage('assign-discovery', `✔ ${data.message}`, 'success');
        document.getElementById('assign-discovery-ip-input').value = '';
        setTimeout(() => {
            closeAssignPanel();
            refreshDiscovery();
        }, 1500);
    } catch (err) {
        showMessage('assign-discovery', `✗ ${err.message}`, 'error');
    }
}

// ─── Assign Discovery Modal (per-row Assign button) ───
function openAssignModal(ip) {
    currentDiscoveryIP = ip;
    document.getElementById('assign-discovery-ip').textContent = `Assign ${ip} to a switch:`;
    document.getElementById('assign-discovery-modal').classList.remove('hidden');
    hideMessage('assign-discovery');
}

function closeAssignModal() {
    document.getElementById('assign-discovery-modal').classList.add('hidden');
    currentDiscoveryIP = null;
}

async function confirmAssignDiscovery() {
    const switchName = document.getElementById('assign-discovery-select').value;
    if (!switchName) {
        showMessage('assign-discovery', '✗ Please select a switch', 'error');
        return;
    }
    if (!currentDiscoveryIP) {
        showMessage('assign-discovery', '✗ No IP selected', 'error');
        return;
    }

    try {
        const data = await api('/discovery/assign', {
            method: 'POST',
            body: JSON.stringify({ discovered_ip: currentDiscoveryIP, switch_name: switchName }),
        });
        showMessage('assign-discovery', `✔ ${data.message}`, 'success');
        setTimeout(() => {
            closeAssignModal();
            refreshDiscovery();
        }, 1500);
    } catch (err) {
        showMessage('assign-discovery', `✗ ${err.message}`, 'error');
    }
}

// ─── Netstat View ───
async function loadNetstatView() {
    // Auto-load netstat when view opens
    await loadNetstat();
}

async function loadNetstat() {
    const output = document.getElementById('netstat-output');
    output.textContent = 'Loading netstat...';
    try {
        const data = await api('/netstat');
        if (data.lines && data.lines.length > 0) {
            let html = '';
            data.lines.forEach(line => {
                html += `<span class="line-${line.type}">${escapeHtml(line.text)}</span>\n`;
            });
            output.innerHTML = html;
        } else {
            output.textContent = data.output || 'No output';
        }
    } catch (err) {
        output.textContent = `Failed: ${err.message}`;
    }
}


// ─── Message Helpers ───
function showMessage(context, text, type) {
    let el;
    if (context === 'home') {
        // Show in a toast-like manner at top of home
        el = document.getElementById('home-message');
        if (!el) {
            el = document.createElement('div');
            el.id = 'home-message';
            el.className = 'message hidden';
            document.querySelector('#view-home').prepend(el);
        }
    } else if (context === 'assign') {
        el = document.getElementById('assign-message');
    } else if (context === 'assign-discovery') {
        el = document.getElementById('assign-discovery-message');
    } else if (context === 'config-ip') {
        el = document.getElementById('config-ip-message');
    } else if (context === 'traceroute') {
        el = document.getElementById('traceroute-message');
    } else if (context === 'ping') {
        // Show in ping output area
        const outputDiv = document.getElementById('ping-output');
        const resultPre = document.getElementById('ping-result');
        outputDiv.classList.remove('hidden');
        resultPre.innerHTML = `<span class="line-${type === 'error' ? 'timeout' : 'reply'}">${escapeHtml(text)}</span>`;
        return;
    }

    if (el) {
        el.textContent = text;
        el.className = `message ${type}`;
        el.classList.remove('hidden');

        // Auto-hide after 5 seconds for success
        if (type === 'success') {
            setTimeout(() => el.classList.add('hidden'), 5000);
        }
    }
}

function hideMessage(context) {
    let el;
    if (context === 'assign') {
        el = document.getElementById('assign-message');
    } else if (context === 'assign-discovery') {
        el = document.getElementById('assign-discovery-message');
    }
    if (el) {
        el.classList.add('hidden');
    }
}

// ─── Utility ───
function isValidIP(ip) {
    const parts = ip.split('.');
    if (parts.length !== 4) return false;
    return parts.every(part => {
        const num = parseInt(part, 10);
        return !isNaN(num) && num >= 0 && num <= 255 && part === num.toString();
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ─── ipconfig View ───
async function loadIpconfigView() {
    await loadIpconfig();
    await loadConfigIp();
}

async function loadIpconfig() {
    const output = document.getElementById('ipconfig-output');
    output.textContent = 'Loading...';
    try {
        const data = await api('/ipconfig');
        output.textContent = data.output || 'No output';
    } catch (err) {
        output.textContent = `Failed: ${err.message}`;
    }
}

async function loadConfigIp() {
    const display = document.getElementById('config-ip-display');
    try {
        const data = await api('/config-ip');
        display.innerHTML = `
            <p>Current config page IP: <a href="http://${data.config_ip}" target="_blank" rel="noopener noreferrer" class="config-link">${data.config_ip}</a></p>
        `;
    } catch (err) {
        display.innerHTML = '<p class="dim-text">Failed to load</p>';
    }
}

async function setConfigIp() {
    const newIp = document.getElementById('config-ip-input').value.trim();
    if (!newIp) {
        showMessage('config-ip', '✗ Enter an IP address', 'error');
        return;
    }
    if (!isValidIP(newIp)) {
        showMessage('config-ip', `✗ '${newIp}' is not a valid IPv4 address`, 'error');
        return;
    }
    try {
        await api('/config-ip', {
            method: 'POST',
            body: JSON.stringify({ new_ip: newIp }),
        });
        showMessage('config-ip', `✔ Config page IP updated to ${newIp}`, 'success');
        document.getElementById('config-ip-input').value = '';
        await loadConfigIp();
        await loadTopology();
    } catch (err) {
        showMessage('config-ip', `✗ ${err.message}`, 'error');
    }
}

// ─── Traceroute View ───
async function loadTracerouteView() {
    const subnetsEl = document.getElementById('traceroute-subnets');
    try {
        const data = await api('/discovery');
        if (data.local_ips.length > 0) {
            subnetsEl.textContent = `Your IPs: ${data.local_ips.join(', ')}  |  Subnets: ${data.subnets.slice(0, 3).join(', ')}`;
        } else {
            subnetsEl.textContent = `Subnets: ${data.subnets.slice(0, 3).join(', ')}`;
        }
    } catch (err) {
        subnetsEl.textContent = '';
    }
    document.getElementById('traceroute-output').classList.add('hidden');
    hideMessage('traceroute');
}

async function runTraceroute() {
    const raw = document.getElementById('traceroute-input').value.trim();
    if (!raw) {
        showMessage('traceroute', '✗ Enter a target (IP, hostname, or domain)', 'error');
        return;
    }

    const output = document.getElementById('traceroute-output');
    output.classList.remove('hidden');
    output.innerHTML = '<span class="line-info">Tracing route...</span>';

    try {
        const data = await api('/traceroute', {
            method: 'POST',
            body: JSON.stringify({ new_ip: raw }),
        });

        if (data.lines && data.lines.length > 0) {
            let html = '';
            data.lines.forEach(line => {
                html += `<span class="line-${line.type}">${escapeHtml(line.text)}</span>\n`;
            });
            output.innerHTML = html;
        } else {
            output.innerHTML = '<span class="line-info">No output returned.</span>';
        }
    } catch (err) {
        output.innerHTML = `<span class="line-timeout">✗ ${escapeHtml(err.message)}</span>`;
    }
}

// ─── ARP Table View ───
async function loadArpView() {
    document.getElementById('arp-output').textContent = '';
    await loadArpTable();
}

async function loadArpTable() {
    const output = document.getElementById('arp-output');
    output.textContent = 'Loading ARP table...';
    try {
        const data = await api('/arp');
        if (data.lines && data.lines.length > 0) {
            let html = '';
            data.lines.forEach(line => {
                html += `<span class="line-${line.type}">${escapeHtml(line.text)}</span>\n`;
            });
            output.innerHTML = html;
        } else {
            output.textContent = data.output || 'No output';
        }
    } catch (err) {
        output.textContent = `Failed: ${err.message}`;
    }
}

// ─── Initialize on load ───
document.addEventListener('DOMContentLoaded', () => {
    loadTopology();
});
