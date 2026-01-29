const app = window.Telegram.WebApp;
const API_BASE = '/api';

// Initialize
app.ready();
app.expand(); // request full screen

// State
let allPRs = [];
let currentFilter = 'all';

// DOM Elements
const prListEl = document.getElementById('prList');
const searchInput = document.getElementById('searchInput');
const filterChips = document.querySelectorAll('.filter-chip');
const detailView = document.getElementById('detailView');
const detailContent = document.getElementById('detailContent');

// Fetch Data
async function fetchPRs(query = '') {
    try {
        let url = `${API_BASE}/prs?state=${currentFilter === 'all' ? '' : currentFilter}`;
        if (query) {
            url += `&q=${encodeURIComponent(query)}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error('API Error');
        allPRs = await response.json();
        renderList(allPRs);
    } catch (e) {
        prListEl.innerHTML = `<div style="text-align:center; padding:20px; color:var(--hint-color)">Error loading requests.<br>${e}</div>`;
    }
}

// Render List
function renderList(prs) {
    if (prs.length === 0) {
        prListEl.innerHTML = `<div style="text-align:center; padding:20px; color:var(--hint-color)">No requests found in database.</div>`;
        return;
    }

    prListEl.innerHTML = prs.map(pr => `
        <div class="pr-card" onclick="openDetail(${pr.id})">
            <div class="pr-header">
                <span class="pr-title">${pr.name}</span>
                <span class="pr-status status-${pr.state}">${pr.state}</span>
            </div>
            <div class="pr-meta">
                <span>👤 ${pr.requested_by}</span>
                <span>💰 ${pr.amount.toLocaleString()}</span>
            </div>
             <div class="pr-meta" style="margin-top:4px">
                <span>📅 ${pr.date_start}</span>
            </div>
        </div>
    `).join('');
}

// Open Detail View
async function openDetail(id) {
    if (!detailView || !detailContent) return;

    detailView.classList.add('open');
    detailContent.innerHTML = '<div class="loading-skeleton"></div><div class="loading-skeleton"></div>';

    if (app.BackButton) {
        app.BackButton.show();
    }

    try {
        const response = await fetch(`${API_BASE}/pr/${id}`);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);

        const pr = await response.json();

        const lines = pr.lines || [];
        const linesHtml = lines.length > 0 ? lines.map(line => `
            <div class="line-item">
                <div>
                    <div class="item-name">${line.name || 'Unknown Product'}</div>
                    <div class="item-meta">Qty: ${line.product_qty || 0}</div>
                </div>
                <div>${(line.estimated_cost || 0).toLocaleString()}</div>
            </div>
        `).join('') : '<div class="item-meta">No items</div>';

        detailContent.innerHTML = `
            <div class="detail-section">
                <div class="detail-label">Reference</div>
                <div class="detail-value">${pr.name || 'N/A'}</div>
            </div>
             <div class="detail-section">
                <div class="detail-label">Status</div>
                <span class="pr-status status-${pr.state}">${pr.state}</span>
            </div>
            <div class="detail-section">
                <div class="detail-label">Requester</div>
                <div class="detail-value">${pr.requested_by}</div>
            </div>
            <div class="detail-section">
                <div class="detail-label">Assigned To</div>
                <div class="detail-value">${pr.assigned_to}</div>
            </div>
            <div class="detail-section">
                <div class="detail-label">Description</div>
                <div class="detail-value" style="white-space: pre-wrap;">${pr.description || 'No description'}</div>
            </div>
            
            <div class="line-items">
                <div class="detail-label">Items</div>
                ${linesHtml}
            </div>
             <div class="detail-section" style="margin-top:16px; text-align:right">
                <div class="detail-label">Total</div>
                <div class="detail-value" style="font-weight:700">${(pr.amount || 0).toLocaleString()}</div>
            </div>
        `;
    } catch (e) {
        console.error(e);
        detailContent.innerHTML = `<div style="text-align:center; padding:20px; color:red">Error: ${e.message}</div>`;
    }
}

// Make globally accessible
window.openDetail = openDetail;

// Close Detail View
window.closeDetail = () => {
    detailView.classList.remove('open');
    if (app.BackButton) {
        app.BackButton.hide();
    }
};

if (app.BackButton) {
    app.BackButton.onClick(() => {
        window.closeDetail();
    });
}

// Debounce util
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Event Listeners
searchInput.addEventListener('input', debounce((e) => {
    const val = e.target.value.trim();
    if (val.length > 2 || val.length === 0) {
        prListEl.innerHTML = '<div class="loading-skeleton"></div><div class="loading-skeleton"></div>';
        fetchPRs(val);
    }
}, 500));

filterChips.forEach(btn => {
    btn.addEventListener('click', () => {
        // Toggle active class
        filterChips.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        currentFilter = btn.dataset.state;
        // Fetch new data based on filter
        prListEl.innerHTML = '<div class="loading-skeleton"></div><div class="loading-skeleton"></div>';
        const term = searchInput.value.trim();
        fetchPRs(term);
    });
});

// Start
fetchPRs();
