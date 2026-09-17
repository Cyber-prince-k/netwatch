function showToast(message) {
  const toast = document.querySelector('#toastMessage');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('is-visible');
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove('is-visible'), 2800);
}

function animateMetrics() {
  document.querySelectorAll('[data-count]').forEach((element) => {
    const target = Number(element.dataset.count);
    const decimals = Number.isInteger(target) ? 0 : 2;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - start) / 700, 1);
      const eased = 1 - ((1 - progress) ** 3);
      element.firstChild.textContent = (target * eased).toFixed(decimals);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function setConnection(online) {
  const label = document.querySelector('#connectionLabel');
  const dot = document.querySelector('#connectionDot');
  if (label) label.textContent = online ? 'Live fabric view' : 'Sync unavailable';
  if (dot) dot.style.background = online ? 'var(--cyan)' : 'var(--coral)';
}

async function loadAssets() {
  const response = await fetch('/api/v1/assets');
  if (!response.ok) throw new Error('Inventory request failed');
  const assets = await response.json();
  document.querySelector('#assetRows').innerHTML = assets.map((asset, index) => `
    <tr style="animation-delay:${index * 60}ms"><td><span class="asset-name">${asset.name}</span><span class="asset-host">${asset.hostname}</span></td>
    <td>${asset.asset_type}</td><td>Site ${asset.site_id}</td>
    <td><span class="status-tag status-${asset.status}">${asset.status}</span></td>
    <td class="asset-tags">${asset.tags.join(' · ')}</td></tr>`).join('');
}

async function loadChart() {
  const response = await fetch('/api/v1/overview');
  if (!response.ok) throw new Error('Telemetry request failed');
  const data = await response.json();
  drawLatencyChart([...data.telemetry].reverse());
}

function drawLatencyChart(points) {
  const canvas = document.querySelector('#latencyChart');
  const bounds = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const width = Math.max(bounds.width, 320);
  const height = Math.max(bounds.height, 220);
  canvas.width = width * scale;
  canvas.height = height * scale;
  const context = canvas.getContext('2d');
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);
  const values = points.map((point) => point.latency_ms || 0);
  const max = Math.max(...values, 10);
  const left = 12;
  const right = width - 12;
  const top = 16;
  const bottom = height - 24;
  const xStep = values.length > 1 ? (right - left) / (values.length - 1) : right - left;
  const y = (value) => bottom - ((value / max) * (bottom - top));
  context.strokeStyle = '#e7efed';
  context.lineWidth = 1;
  for (let index = 0; index < 4; index += 1) {
    const gridY = top + ((bottom - top) * index / 3);
    context.beginPath(); context.moveTo(left, gridY); context.lineTo(right, gridY); context.stroke();
  }
  if (!values.length) {
    context.fillStyle = '#8d9b97'; context.font = '11px DM Mono'; context.fillText('Waiting for telemetry', left, height / 2);
    return;
  }
  const chartPoints = values.map((value, index) => ({x: left + (index * xStep), y: y(value)}));
  context.beginPath();
  chartPoints.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
  context.lineTo(right, bottom); context.lineTo(left, bottom); context.closePath();
  context.fillStyle = 'rgba(52,174,185,.12)'; context.fill();
  context.beginPath();
  chartPoints.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
  context.strokeStyle = '#5877c8'; context.lineWidth = 2.5; context.stroke();
  chartPoints.forEach((point) => { context.beginPath(); context.arc(point.x, point.y, 3.5, 0, Math.PI * 2); context.fillStyle = '#fff'; context.fill(); context.strokeStyle = '#5877c8'; context.lineWidth = 2; context.stroke(); });
}

async function refreshDashboard() {
  const button = document.querySelector('#refreshButton');
  button.classList.add('is-loading');
  try {
    await Promise.all([loadAssets(), loadChart()]);
    setConnection(true);
    document.querySelector('#lastSync').textContent = `Synced ${new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
    showToast('Fabric data refreshed');
  } catch (error) {
    setConnection(false);
    showToast('Unable to refresh fabric data');
  } finally {
    button.classList.remove('is-loading');
  }
}

document.querySelector('#refreshButton').addEventListener('click', refreshDashboard);
animateMetrics();
refreshDashboard();
window.setInterval(refreshDashboard, 30000);
window.addEventListener('resize', () => loadChart().catch(() => undefined));
