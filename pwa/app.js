/* Main app logic for Economic Sentiment Index PWA */

const API = '';  // Same origin
let charts = {};

// Chart.js global defaults for dark theme
Chart.defaults.color = '#888';
Chart.defaults.borderColor = '#2a2a4a';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 11;

// --- Data fetching ---

async function fetchJSON(url) {
    const resp = await fetch(API + url);
    return resp.json();
}

// --- Render functions ---

function renderHero(latest, delta) {
    const el = document.getElementById('composite-value');
    const deltaEl = document.getElementById('composite-delta');
    const monthEl = document.getElementById('hero-month');

    if (!latest || latest.composite_index == null) {
        el.textContent = '--';
        return;
    }

    el.textContent = latest.composite_index.toFixed(1);

    if (delta != null) {
        const sign = delta >= 0 ? '+' : '';
        deltaEl.textContent = sign + delta.toFixed(1);
        deltaEl.className = 'delta ' + (delta >= 0 ? 'positive' : 'negative');
    }

    monthEl.textContent = 'Latest: ' + latest.month;

    // Color the hero based on index level
    const card = document.getElementById('hero');
    const val = latest.composite_index;
    if (val >= 60) card.style.borderColor = '#4caf50';
    else if (val <= 40) card.style.borderColor = '#ef5350';
    else card.style.borderColor = '#ffc107';
}

function renderMetrics(latest) {
    if (!latest) return;

    const set = (id, val, decimals) => {
        document.getElementById(id).textContent =
            val != null ? val.toFixed(decimals) : '--';
    };

    set('sentiment-value', latest.sentiment_raw, 2);
    set('vix-value', latest.vix_avg, 1);
    set('cpi-value', latest.china_cpi_yoy, 2);
    set('fx-value', latest.usd_cny_change, 2);
}

function createLineChart(canvasId, labels, data, color, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    if (charts[canvasId]) charts[canvasId].destroy();

    const cfg = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 5,
                tension: 0.3,
                fill: options.fill || false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1a2e',
                    borderColor: '#4fc3f7',
                    borderWidth: 1,
                    titleColor: '#fff',
                    bodyColor: '#e0e0e0',
                }
            },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 6, maxRotation: 0 },
                    grid: { display: false }
                },
                y: {
                    ticks: { maxTicksLimit: 5 },
                    ...(options.yMin != null ? { min: options.yMin } : {}),
                    ...(options.yMax != null ? { max: options.yMax } : {}),
                }
            },
            ...(options.annotation ? {
                plugins: {
                    annotation: options.annotation
                }
            } : {})
        }
    };

    charts[canvasId] = new Chart(ctx, cfg);
    return charts[canvasId];
}

function createBarChart(canvasId, labels, data, colors) {
    const ctx = document.getElementById(canvasId).getContext('2d');

    if (charts[canvasId]) charts[canvasId].destroy();

    charts[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors || data.map(v => v >= 0 ? '#4caf5090' : '#ef535090'),
                borderColor: data.map(v => v >= 0 ? '#4caf50' : '#ef5350'),
                borderWidth: 1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: canvasId === 'pcaChart' ? 'y' : 'x',
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 6, maxRotation: 0 },
                    grid: { display: canvasId === 'pcaChart' }
                },
                y: {
                    ticks: { maxTicksLimit: 5 },
                    grid: { display: canvasId !== 'pcaChart' }
                }
            }
        }
    });
}

function renderCompositeChart(data) {
    const months = data.map(d => d.month);
    const values = data.map(d => d.composite_index);

    const ctx = document.getElementById('compositeChart').getContext('2d');
    if (charts['compositeChart']) charts['compositeChart'].destroy();

    charts['compositeChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                data: values,
                borderColor: '#4fc3f7',
                backgroundColor: '#4fc3f720',
                borderWidth: 2.5,
                pointRadius: 3,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1a2e',
                    borderColor: '#4fc3f7',
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => 'Index: ' + (ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) : 'N/A')
                    }
                }
            },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 6, maxRotation: 0 },
                    grid: { display: false }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { maxTicksLimit: 6 }
                }
            }
        },
        plugins: [{
            // Draw neutral line at 50
            afterDraw: (chart) => {
                const yScale = chart.scales.y;
                const y = yScale.getPixelForValue(50);
                const ctx = chart.ctx;
                ctx.save();
                ctx.strokeStyle = '#ffc10770';
                ctx.lineWidth = 1;
                ctx.setLineDash([6, 4]);
                ctx.beginPath();
                ctx.moveTo(chart.chartArea.left, y);
                ctx.lineTo(chart.chartArea.right, y);
                ctx.stroke();
                ctx.restore();
            }
        }]
    });
}

function renderSubIndicators(data) {
    const months = data.map(d => d.month);

    // Sentiment
    createLineChart('sentimentChart', months,
        data.map(d => d.sentiment_raw), '#4caf50', { yMin: 0, yMax: 1 });

    // VIX
    createLineChart('vixChart', months,
        data.map(d => d.vix_avg), '#ff9800');

    // USD/CNY as bar chart
    createBarChart('fxChart', months,
        data.map(d => d.usd_cny_change));

    // Uncertainty
    createLineChart('uncertaintyChart', months,
        data.map(d => d.keyword_uncertainty), '#ab47bc');
}

function renderPCA(pcaData) {
    const section = document.getElementById('pca-section');
    if (!pcaData) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    const varEl = document.getElementById('pca-variance');
    varEl.textContent = 'PC1 Variance Explained: ' +
        (pcaData.variance_explained * 100).toFixed(1) + '% (est. ' + pcaData.estimated_month + ')';

    const labels = ['Sentiment', 'Kw Net', 'Uncertainty', 'USD/CNY', 'VIX', 'CPI', 'G.Trends'];
    const loadings = pcaData.loadings;
    const trimmedLabels = labels.slice(0, loadings.length);

    createBarChart('pcaChart', trimmedLabels, loadings,
        loadings.map(v => v >= 0 ? '#4caf5090' : '#ef535090'));
}

function renderArticles(articles, months) {
    // Populate month dropdown
    const select = document.getElementById('month-select');
    select.innerHTML = '';
    months.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        select.appendChild(opt);
    });

    // Load articles for selected month
    select.onchange = () => loadArticles(select.value);

    // Show articles
    renderArticleList(articles);
}

function renderArticleList(articles) {
    const list = document.getElementById('articles-list');
    if (!articles || articles.length === 0) {
        list.innerHTML = '<div class="article-item"><span class="article-title" style="color:#888">No articles for this month</span></div>';
        return;
    }

    list.innerHTML = articles.map(a => `
        <div class="article-item">
            <div class="article-title">${escapeHtml(a.title)}</div>
            <div class="article-meta">${a.source} &middot; ${a.published_date || ''}</div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Load all data ---

async function loadArticles(month) {
    try {
        const resp = await fetchJSON('/api/articles/' + month);
        renderArticleList(resp.data);
    } catch (e) {
        console.error('Failed to load articles:', e);
    }
}

async function loadAll() {
    const btn = document.getElementById('refresh-btn');
    btn.textContent = 'Loading...';
    btn.disabled = true;

    try {
        // Fetch all data in parallel
        const [latestResp, indexResp, pcaResp] = await Promise.all([
            fetchJSON('/api/latest'),
            fetchJSON('/api/index'),
            fetchJSON('/api/pca'),
        ]);

        const indexData = indexResp.data || [];
        const validData = indexData.filter(d => d.composite_index != null);

        // Render hero + metrics
        renderHero(latestResp.latest, latestResp.delta);
        renderMetrics(latestResp.latest);

        // Render charts
        if (validData.length > 0) {
            renderCompositeChart(validData);
        }
        renderSubIndicators(indexData);

        // PCA
        renderPCA(pcaResp.data);

        // Articles - load latest month
        const months = indexData.map(d => d.month).reverse();
        const latestMonth = months[0];
        if (latestMonth) {
            const articlesResp = await fetchJSON('/api/articles/' + latestMonth);
            renderArticles(articlesResp.data, months);
        }

        // Update timestamp
        document.getElementById('last-updated').textContent =
            'Updated: ' + new Date().toLocaleTimeString();

    } catch (e) {
        console.error('Failed to load data:', e);
        document.getElementById('composite-value').textContent = 'Error';
    } finally {
        btn.textContent = 'Refresh';
        btn.disabled = false;
    }
}

// --- Service Worker Registration ---

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(() => console.log('SW registered'))
        .catch(e => console.log('SW registration failed:', e));
}

// --- Init ---
loadAll();
