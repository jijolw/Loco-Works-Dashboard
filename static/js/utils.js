/* ============================================================
   LW/PER Workshop Intelligence — Utility Functions
   ============================================================ */

/**
 * API fetch wrapper.
 * @param {string} endpoint — e.g. 'aerial', 'live', 'coach/12345'
 * @param {Object} [params] — query-string key/value pairs
 * @returns {Promise<Object>} parsed JSON
 */
async function api(endpoint, params) {
    let url = '/api/' + endpoint;
    if (params && Object.keys(params).length) {
        const qs = new URLSearchParams();
        for (const [k, v] of Object.entries(params)) {
            if (v !== undefined && v !== null && v !== '') {
                qs.append(k, v);
            }
        }
        const qsStr = qs.toString();
        if (qsStr) url += '?' + qsStr;
    }
    try {
        const resp = await fetch(url);
        if (!resp.ok) {
            const errBody = await resp.text();
            throw new Error(`API ${resp.status}: ${errBody}`);
        }
        return await resp.json();
    } catch (err) {
        console.error('[api]', endpoint, err);
        throw err;
    }
}

/* ---------- Date helpers ---------- */

/**
 * Parse a date string (DD/MM/YYYY or ISO) to a Date object.
 * Returns null on failure.
 */
function parseDate(dateStr) {
    if (!dateStr) return null;
    // DD/MM/YYYY
    const slashMatch = String(dateStr).match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (slashMatch) {
        const d = new Date(+slashMatch[3], +slashMatch[2] - 1, +slashMatch[1]);
        return isNaN(d) ? null : d;
    }
    // ISO or other
    const d = new Date(dateStr);
    return isNaN(d) ? null : d;
}

/**
 * Format a date string for display (DD-MMM-YYYY).
 */
function formatDate(dateStr) {
    const d = parseDate(dateStr);
    if (!d) return dateStr || '—';
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const dd = String(d.getDate()).padStart(2, '0');
    return `${dd}-${months[d.getMonth()]}-${d.getFullYear()}`;
}

/**
 * Calculate days between a date string and today.
 * Returns integer (positive = past).
 */
function daysBetween(dateStr, today) {
    const d = parseDate(dateStr);
    if (!d) return null;
    const t = today || new Date();
    const diffMs = t.getTime() - d.getTime();
    return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

/* ---------- Loading overlay ---------- */

function showLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.add('active');
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.remove('active');
}

/* ---------- CSV download ---------- */

/**
 * Convert array of objects to CSV and trigger browser download.
 * @param {Object[]} data
 * @param {string} filename
 */
function downloadCSV(data, filename) {
    if (!data || !data.length) return;
    const keys = Object.keys(data[0]);
    const csvRows = [];
    // Header
    csvRows.push(keys.map(k => `"${k}"`).join(','));
    // Rows
    for (const row of data) {
        csvRows.push(keys.map(k => {
            let val = row[k];
            if (val === null || val === undefined) val = '';
            val = String(val).replace(/"/g, '""');
            return `"${val}"`;
        }).join(','));
    }
    const csvStr = csvRows.join('\r\n');
    const blob = new Blob(['\uFEFF' + csvStr], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/* ---------- Escape HTML ---------- */

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ---------- Debounce ---------- */

function debounce(fn, ms) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), ms);
    };
}

/* ---------- Metric Card HTML ---------- */

/**
 * Returns HTML string for a metric card.
 * @param {string} label
 * @param {string|number} value
 * @param {string} icon — emoji
 * @param {string} colorClass — e.g. 'accent-blue', 'accent-danger'
 * @returns {string}
 */
function createMetricCard(label, value, icon, colorClass, extraAttrs) {
    return `
        <div class="metric-card ${colorClass || 'accent-blue'}" ${extraAttrs || ''}>
            <div class="metric-icon">${icon || ''}</div>
            <div class="metric-value">${escapeHtml(String(value))}</div>
            <div class="metric-label">${escapeHtml(label)}</div>
        </div>`;
}

/* ---------- Data Table ---------- */

/**
 * Build a sortable/searchable data table.
 * @param {Object[]} data — array of row objects
 * @param {Array<{key:string, label:string, format?:Function, sortable?:boolean}>} columns
 * @param {Object} options — {id, height, colorRowFn?, searchable?}
 * @returns {string} HTML
 */
function createDataTable(data, columns, options) {
    options = options || {};
    const tableId = options.id || ('table-' + Math.random().toString(36).substr(2, 6));
    const scrollClass = options.height ? 'scrollable' : '';
    const styleAttr = options.height ? ` style="max-height:${options.height}px"` : '';

    let html = '';

    // Search bar
    if (options.searchable) {
        html += `<div style="margin-bottom:12px">
            <input type="text" class="search-input" placeholder="Search table…"
                   onkeyup="filterTable('${tableId}', this.value)"
                   style="max-width:320px">
        </div>`;
    }

    html += `<div class="table-container ${scrollClass}"${styleAttr}>`;
    html += `<table class="data-table" id="${tableId}">`;

    // Head
    html += '<thead><tr>';
    columns.forEach((col, i) => {
        const sortable = col.sortable !== false;
        const cls = sortable ? 'sortable' : '';
        const onclick = sortable ? ` onclick="sortTable('${tableId}', ${i})"` : '';
        html += `<th class="${cls}" data-col="${i}"${onclick}>${escapeHtml(col.label)}</th>`;
    });
    html += '</tr></thead>';

    // Body
    html += '<tbody>';
    if (!data || data.length === 0) {
        html += `<tr><td colspan="${columns.length}" style="text-align:center;color:var(--text-muted);padding:32px;">No data available</td></tr>`;
    } else {
        data.forEach(row => {
            const rowClass = options.colorRowFn ? options.colorRowFn(row) : '';
            html += `<tr class="${rowClass}">`;
            columns.forEach(col => {
                let val = row[col.key];
                if (col.format) {
                    val = col.format(val, row);
                } else {
                    val = escapeHtml(String(val ?? ''));
                }
                html += `<td>${val}</td>`;
            });
            html += '</tr>';
        });
    }
    html += '</tbody></table></div>';

    return html;
}

/* ---------- Sort Table ---------- */

/** Current sort state per table */
const _sortState = {};

function sortTable(tableId, columnIndex) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (!rows.length) return;

    // Determine direction
    const key = tableId + '-' + columnIndex;
    if (!_sortState[key]) _sortState[key] = 'asc';
    else if (_sortState[key] === 'asc') _sortState[key] = 'desc';
    else _sortState[key] = 'asc';
    const dir = _sortState[key];

    // Update header classes
    thead.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    const activeTh = thead.querySelectorAll('th')[columnIndex];
    if (activeTh) activeTh.classList.add(dir === 'asc' ? 'sort-asc' : 'sort-desc');

    // Sort rows
    rows.sort((a, b) => {
        const aCell = a.children[columnIndex];
        const bCell = b.children[columnIndex];
        if (!aCell || !bCell) return 0;
        let aVal = aCell.textContent.trim();
        let bVal = bCell.textContent.trim();

        // Try numeric
        const aNum = parseFloat(aVal.replace(/[^0-9.\-]/g, ''));
        const bNum = parseFloat(bVal.replace(/[^0-9.\-]/g, ''));
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return dir === 'asc' ? aNum - bNum : bNum - aNum;
        }

        // String compare
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
        if (aVal < bVal) return dir === 'asc' ? -1 : 1;
        if (aVal > bVal) return dir === 'asc' ? 1 : -1;
        return 0;
    });

    // Re-append
    rows.forEach(r => tbody.appendChild(r));
}

/* ---------- Filter Table ---------- */

function filterTable(tableId, searchText) {
    if (tableId === 'outturn-table' && typeof window.applyOutturnFilters === 'function') {
        window.applyOutturnFilters(searchText);
        return;
    }
    const table = document.getElementById(tableId);
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    const term = (searchText || '').toLowerCase();

    rows.forEach(row => {
        if (!term) {
            row.style.display = '';
            return;
        }
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
}
