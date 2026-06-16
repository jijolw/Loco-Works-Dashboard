/* ---------- Navigation Helper ---------- */
window.navigateToSearch = function(coachNo) {
    location.hash = '#search';
    setTimeout(() => {
        const input = document.getElementById('coach-search-input');
        if (input) {
            input.value = coachNo;
            searchCoach();
        }
    }, 150);
};

/* ---------- Coach Categorization Helper ---------- */
window.getCoachCategoryString = function(c) {
    let st = '';
    let sched = '';
    let ac_nac = 'NA';
    const fam = (c.family || '').toUpperCase();
    const desc = (c.coach_desc || '').toUpperCase();
    const rep = (c.repair_type || '').toUpperCase();
    
    if (fam === 'LOCO' || fam === 'AC LOCO' || desc.includes('WAP') || desc.includes('WAG')) st = 'AC LOCO';
    else if (fam === 'ART' || desc.includes('ART')) st = 'ART';
    else if (fam === 'DEMU') st = 'DEMU/DTC/TC';
    else if (fam === 'MEMU' || fam === 'EMU') st = 'EMU/MEMU';
    else if (fam === 'ICF') st = 'ICF';
    else if (fam === 'LHB') st = 'LHB';
    else if (fam === 'NMG' || fam === 'NMGHS') st = 'NMGHS';
    else if (fam === 'VB') st = 'VB';
    else if (fam === 'TW' || desc.includes('TW') || desc.includes('TOWER')) {
        if (desc.includes('8W') || desc.includes('8-W')) st = 'TW 8W';
        else st = 'TW 4W';
    } else if (fam === 'SPECIAL') {
        if (desc.includes('SPART')) st = 'SPART';
        else if (desc.includes('SPIC')) st = 'SPIC';
        else if (desc.includes('TW') || desc.includes('TOWER')) {
            if (desc.includes('8W') || desc.includes('8-W')) st = 'TW 8W';
            else st = 'TW 4W';
        } else if (desc.includes('ART')) st = 'ART';
        else st = 'ICF';
    } else st = 'ICF';
    
    if (st === 'LHB' || st === 'VB') {
        if (rep.includes('SS2') || rep.includes('SS3') || rep.includes('SS2/SS3')) sched = (st === 'VB') ? 'SS2' : 'SS2/SS3';
        else if (rep.includes('OR') || rep === '4') sched = 'OR';
        else sched = 'SS1';
    } else if (st === 'ICF') {
        if (rep.includes('IOH') || rep.includes('SS1') || rep.includes('104')) sched = 'IOH';
        else sched = 'POH';
    } else if (st === 'NMGHS') sched = 'CONV/POH';
    else if (st === 'ART') sched = 'CONV';
    else sched = 'POH';
    
    if (st === 'LHB') {
        if (desc.startsWith('LWSCN') || desc.startsWith('LWS') || desc.startsWith('LSCN') || desc.startsWith('LS') || desc.startsWith('LSLRD')) ac_nac = 'NAC';
        else ac_nac = 'AC';
    } else if (st === 'ICF') {
        if (desc.includes('AC') || desc.includes('FC') || desc.startsWith('WCB')) ac_nac = 'AC';
        else ac_nac = 'NAC';
    } else if (st === 'VB') ac_nac = 'AC';
    else ac_nac = 'NA';
    
    const parts = [st, sched];
    if (ac_nac !== 'NA') parts.push(ac_nac);
    return parts.join(' ');
};

window.filterLiveByType = function(type) {
    const el = document.getElementById('lf-coachtype');
    if (el) {
        el.value = type;
        if (el.value !== type && type) {
            const target = String(type).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyLiveFilters();
    }
};

window.filterLiveByFamily = function(family) {
    const el = document.getElementById('lf-family');
    if (!el) return;
    
    if (family === 'DEMU/MEMU') {
        el.value = '';
        window._customFamilyFilter = (f) => ['DEMU', 'MEMU', 'EMU'].includes(f);
    } else if (family === 'OTHER') {
        el.value = '';
        window._customFamilyFilter = (f) => !['LHB', 'ICF', 'LOCO', 'DEMU', 'MEMU', 'EMU'].includes(f);
    } else {
        window._customFamilyFilter = null;
        el.value = family;
        if (el.value !== family && family) {
            const target = String(family).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
    }
    applyLiveFilters();
};

window.filterLiveByDivision = function(div) {
    const el = document.getElementById('lf-division');
    if (el) {
        el.value = div;
        if (el.value !== div && div) {
            const target = String(div).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyLiveFilters();
    }
};

function filterOutturnByType(type) {
    const el = document.getElementById('of-coachtype');
    if (el) {
        el.value = type;
        if (el.value !== type && type) {
            const target = String(type).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyOutturnFilters();
    }
}
window.filterOutturnByType = filterOutturnByType;

function filterOutturnByDivision(div) {
    const el = document.getElementById('of-division');
    if (el) {
        el.value = div;
        if (el.value !== div && div) {
            const target = String(div).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyOutturnFilters();
    }
}
window.filterOutturnByDivision = filterOutturnByDivision;

function filterOutturnByFamily(family) {
    const el = document.getElementById('of-family');
    if (el) {
        el.value = family;
        if (el.value !== family && family) {
            const target = String(family).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyOutturnFilters();
    }
}
window.filterOutturnByFamily = filterOutturnByFamily;

function filterOutturnByCategory(category) {
    const el = document.getElementById('of-category');
    if (el) {
        el.value = category;
        if (el.value !== category && category) {
            const target = String(category).trim().toLowerCase();
            for (let opt of el.options) {
                if (opt.value.trim().toLowerCase() === target) {
                    el.value = opt.value;
                    break;
                }
            }
        }
        applyOutturnFilters();
    }
}
window.filterOutturnByCategory = filterOutturnByCategory;

function clearOutturnFilters() {
    ['of-coachtype', 'of-division', 'of-family', 'of-category'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const searchEl = document.getElementById('of-search');
    if (searchEl) searchEl.value = '';
    applyOutturnFilters();
}
window.clearOutturnFilters = clearOutturnFilters;

function applyOutturnFilters() {
    if (!_outturnData || !_outturnData.coaches) return;
    
    // Map coaches to include category property so we don't recalculate it repeatedly
    const coaches = _outturnData.coaches.map(c => ({
        ...c,
        category: c.category || window.getCoachCategoryString(c)
    }));

    const typeFilter = (document.getElementById('of-coachtype') || {}).value || '';
    const divFilter = (document.getElementById('of-division') || {}).value || '';
    const familyFilter = (document.getElementById('of-family') || {}).value || '';
    const categoryFilter = (document.getElementById('of-category') || {}).value || '';
    const search = (document.getElementById('of-search') || {}).value || '';

    const typeTerm = typeFilter.toLowerCase();
    const divTerm = divFilter.toLowerCase();
    const familyTerm = familyFilter.toLowerCase();
    const categoryTerm = categoryFilter.toLowerCase();
    const searchTerm = search.toLowerCase();
    
    // Filter the coaches array
    const filtered = coaches.filter(c => {
        if (typeFilter && (c.coach_desc || c.family || '').toLowerCase() !== typeTerm) return false;
        if (familyFilter && (c.family || '').toLowerCase() !== familyTerm) return false;
        if (categoryFilter && (c.category || '').toLowerCase() !== categoryTerm) return false;
        if (divFilter && (c.division || '').toLowerCase() !== divTerm) return false;
        if (search) {
            const num = String(c.coachno || '').toLowerCase();
            const type = String(c.coach_desc || '').toLowerCase();
            const div = String(c.division || '').toLowerCase();
            const family = String(c.family || '').toLowerCase();
            const category = String(c.category || '').toLowerCase();
            const repair = String(c.repair_type || '').toLowerCase();
            if (!num.includes(searchTerm) && !type.includes(searchTerm) && !div.includes(searchTerm) && !family.includes(searchTerm) && !category.includes(searchTerm) && !repair.includes(searchTerm)) {
                return false;
            }
        }
        return true;
    });

    // Update table rows visibility
    const table = document.getElementById('outturn-table');
    if (table) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        const filterNums = new Set(filtered.map(c => String(c.coachno || '')));
        rows.forEach(row => {
            const firstCell = row.querySelector('td');
            if (!firstCell) return;
            const num = firstCell.textContent.trim();
            row.style.display = filterNums.has(num) ? '' : 'none';
        });
    }

    // Update label count
    const label = document.getElementById('outturn-count-label');
    if (label) label.textContent = `Showing ${filtered.length} of ${coaches.length} outturned coaches`;

    // Re-generate list of coachTypes, divisions, families from full list for the sidebar summary counts
    const coachTypes = [...new Set(coaches.map(c => c.coach_desc || c.family || '').filter(Boolean))].sort();
    const divisions = [...new Set(coaches.map(c => c.division || '').filter(Boolean))].sort();
    const families = [...new Set(coaches.map(c => c.family || '').filter(Boolean))].sort();

    // Update outturn counts
    const outturnSummaryByType = document.getElementById('outturn-summary-by-type');
    if (outturnSummaryByType) {
        outturnSummaryByType.innerHTML = `
            <table class="summary-mini-table">
                ${coachTypes.map(t => {
                    const cnt = filtered.filter(c => (c.coach_desc || c.family || '') === t).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        `;
    }

    const outturnSummaryByDiv = document.getElementById('outturn-summary-by-division');
    if (outturnSummaryByDiv) {
        outturnSummaryByDiv.innerHTML = `
            <table class="summary-mini-table">
                ${divisions.map(d => {
                    const cnt = filtered.filter(c => (c.division || '') === d).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByDivision('${escapeHtml(d)}')" class="table-link">${escapeHtml(d)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        `;
    }

    const outturnSummaryByFamily = document.getElementById('outturn-summary-by-family');
    if (outturnSummaryByFamily) {
        outturnSummaryByFamily.innerHTML = `
            <table class="summary-mini-table">
                ${families.map(f => {
                    const cnt = filtered.filter(c => (c.family || '') === f).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByFamily('${escapeHtml(f)}')" class="table-link">${escapeHtml(f)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        `;
    }
}
window.applyOutturnFilters = applyOutturnFilters;


/* ---------- Router ---------- */

const PAGES = {
    dashboard: loadDashboard,
    aerial:    loadAerialView,
    live:      loadLivePosition,
    progress:  loadCoachProgress,
    search:    loadCoachSearch,
    outturn:   loadOutturn,
    corrosion: loadCorrosion,
    poh:       loadPohAnalysis,
    'data-tools': loadDataTools,
    analytics: loadAnalytics,
    acloco:    loadAcLoco,
    audit:     loadAuditModule,
};

let currentPage = null;

function init() {
    // Sidebar toggle for mobile
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Set up navigation click handlers for direct clicking & refreshing
    document.querySelectorAll('.nav-link:not(.disabled)').forEach(link => {
        link.addEventListener('click', (e) => {
            const page = link.dataset.page;
            if (page) {
                // Force navigation so it refreshes even if on the same page
                navigate(page, true);
            }
            if (sidebar && window.innerWidth <= 768) {
                sidebar.classList.remove('open');
            }
        });
    });

    // Listen for hash changes (e.g. browser back/forward buttons)
    window.addEventListener('hashchange', () => {
        const page = location.hash.replace('#', '') || 'dashboard';
        navigate(page, false);
    });

    // Initial page load
    const startPage = location.hash.replace('#', '') || 'dashboard';
    navigate(startPage, false);

    // Hide loading if stuck
    setTimeout(() => hideLoading(), 5000);
}

let erpSyncInterval = null;

function navigate(page, force = false) {
    if (!PAGES[page]) page = 'dashboard';
    if (currentPage === page && !force) return;
    currentPage = page;

    if (page !== 'data-tools' && erpSyncInterval) {
        clearInterval(erpSyncInterval);
        erpSyncInterval = null;
    }

    // Update hash. Setting location.hash will trigger the hashchange event.
    // However, the hashchange event handler calls navigate(page, false),
    // which will see currentPage === page and return early, preventing any loop.
    if (location.hash !== '#' + page) {
        location.hash = '#' + page;
    }

    // Highlight active nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === page) {
            link.classList.add('active');
        }
    });

    // Call page loader
    PAGES[page]();
}

/* ============================================================
   DASHBOARD PAGE
   ============================================================ */

async function loadDashboard() {
    const container = document.getElementById('main-content');
    showLoading();

    let metrics = { total: '—', corrosion: '—', outturn: '—', long_stay: '—' };

    try {
        const data = await api('aerial');
        if (data && data.coaches) {
            const coaches = data.coaches;
            metrics.total = coaches.length + (data.ac_locos ? data.ac_locos.length : 0);
            metrics.corrosion = coaches.filter(c => {
                const s = (c.AERIAL_STATUS || '').toUpperCase();
                return s.includes('UNDER CORROSION');
            }).length;
            
            let longStayCount = coaches.filter(c => c.IN_DAYS !== null && c.IN_DAYS > 120).length;
            if (data.ac_locos) {
                data.ac_locos.forEach(l => {
                    const recd = l.date_recd || l.recd_on;
                    if (recd) {
                        const parse = (s) => {
                            if (s.includes('-')) return new Date(s);
                            if (s.includes('/')) {
                                const parts = s.split('/');
                                const year = parts[2].length === 2 ? '20' + parts[2] : parts[2];
                                return new Date(year, parts[1] - 1, parts[0]);
                            }
                            return new Date(s);
                        };
                        try {
                            const recdDt = parse(recd);
                            const today = new Date();
                            const diffTime = Math.abs(today - recdDt);
                            const days = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                            if (days > 120) {
                                longStayCount++;
                            }
                        } catch (err) {}
                    }
                });
            }
            metrics.long_stay = longStayCount;
        }
        const oData = await api('outturn');
        if (oData && oData.metrics) {
            metrics.outturn = oData.metrics.total;
        }
    } catch (e) {
        console.warn('Dashboard: could not load metrics', e);
    }

    container.innerHTML = `
        <div class="anim-slide">
            <div class="welcome-banner">
                <div class="welcome-title">Welcome to LW/PER Workshop Intelligence</div>
                <div class="welcome-subtitle">Real-time coach tracking, workshop analytics, and operational insights for Loco Workshop, Perambur</div>
            </div>

            <div class="metrics-grid">
                ${createMetricCard('Total Inside Workshop', metrics.total, '🚃', 'accent-blue')}
                ${createMetricCard('Under Corrosion', metrics.corrosion, '🔴', 'accent-danger')}
                ${createMetricCard('Outturn This Month', metrics.outturn, '📦', 'accent-success')}
                ${createMetricCard('Long Stay (>120d)', metrics.long_stay, '⏰', 'accent-gold')}
            </div>

            <h2 style="font-size:16px;font-weight:600;color:var(--text-primary);margin:32px 0 16px;">Modules</h2>

            <div class="quick-links">
                <div class="quick-link-card" onclick="navigate('aerial')">
                    <div class="quick-link-icon">🏭</div>
                    <div>
                        <div class="quick-link-title">Aerial View</div>
                        <div class="quick-link-desc">Workshop floor map with real-time coach positions, color-coded by status</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('live')">
                    <div class="quick-link-icon">🚆</div>
                    <div>
                        <div class="quick-link-title">Live Position</div>
                        <div class="quick-link-desc">Filterable table of all coaches currently inside the workshop</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('search')">
                    <div class="quick-link-icon">🔍</div>
                    <div>
                        <div class="quick-link-title">Coach Search</div>
                        <div class="quick-link-desc">Look up any coach by number — see location, status, repair details, and history</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('outturn')">
                    <div class="quick-link-icon">📊</div>
                    <div>
                        <div class="quick-link-title">Outturn</div>
                        <div class="quick-link-desc">Monthly outturn tracking and trends with date period filters</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('analytics')">
                    <div class="quick-link-icon">📈</div>
                    <div>
                        <div class="quick-link-title">Analytics</div>
                        <div class="quick-link-desc">Deep-dive visual analytics and outturn performance metrics using interactive charts</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('corrosion')">
                    <div class="quick-link-icon">🔧</div>
                    <div>
                        <div class="quick-link-title">Corrosion Analysis</div>
                        <div class="quick-link-desc">Analyze corrosion severity bands across POH groups, manage suspect data points, and manually override classifications</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('poh')">
                    <div class="quick-link-icon">🛠️</div>
                    <div>
                        <div class="quick-link-title">POH Analysis</div>
                        <div class="quick-link-desc">Deep analysis of coach POH cycles, schedules, shop loads, and historical outturns</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('acloco')">
                    <div class="quick-link-icon">🔌</div>
                    <div>
                        <div class="quick-link-title">AC Loco Position</div>
                        <div class="quick-link-desc">Track active AC locomotive details, repair milestone progress, and timeline updates</div>
                    </div>
                </div>
                <div class="quick-link-card" onclick="navigate('data-tools')">
                    <div class="quick-link-icon">💾</div>
                    <div>
                        <div class="quick-link-title">Data Tools</div>
                        <div class="quick-link-desc">Manual and automatic syncing tools to fetch and cache targets and ERP data</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    hideLoading();
}

/* ============================================================
   AERIAL VIEW PAGE
   ============================================================ */

async function loadAerialView() {
    const container = document.getElementById('main-content');
    showLoading();

    try {
        const data = await api('aerial');
        renderAerialView(data);
    } catch (err) {
        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">🏭 Aerial View</h1>
            </div>
            <div class="card" style="text-align:center;padding:48px;">
                <div style="font-size:40px;margin-bottom:16px;">⚠️</div>
                <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Failed to load aerial view data</div>
                <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(err.message)}</div>
                <button class="btn btn-primary" style="margin-top:20px;" onclick="loadAerialView()">Retry</button>
            </div>`;
    }

    hideLoading();
}

/* ============================================================
   LIVE POSITION PAGE
   ============================================================ */

let _liveData = null;

async function loadLivePosition() {
    const container = document.getElementById('main-content');
    showLoading();

    try {
        const data = await api('live');
        _liveData = data;
        renderLivePosition(data);
    } catch (err) {
        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">🚆 Live Position</h1>
            </div>
            <div class="card" style="text-align:center;padding:48px;">
                <div style="font-size:40px;margin-bottom:16px;">⚠️</div>
                <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Failed to load live position data</div>
                <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(err.message)}</div>
                <button class="btn btn-primary" style="margin-top:20px;" onclick="loadLivePosition()">Retry</button>
            </div>`;
    }

    hideLoading();
}

function renderLivePosition(data) {
    const container = document.getElementById('main-content');
    const coaches = data.coaches || data || [];

    // Gather unique values for filters
    const coachTypes = [...new Set(coaches.map(c => c.coach_desc || c.family || '').filter(Boolean))].sort();
    const divisions = [...new Set(coaches.map(c => c.division || '').filter(Boolean))].sort();

    // Compute metrics
    const totalInside = coaches.length;
    const uniqueTypes = coachTypes.length;
    const uniqueDivisions = divisions.length;
    const longStay = coaches.filter(c => {
        return c.IN_DAYS !== null && c.IN_DAYS !== undefined && c.IN_DAYS > 120;
    }).length;
    const suspicious = coaches.filter(c => {
        return c.IN_DAYS !== null && c.IN_DAYS !== undefined && c.IN_DAYS > 365;
    });

    let html = '';

    // Header
    html += `<div class="page-header anim-slide">
        <h1 class="page-title">🚆 Live Position</h1>
        <p class="page-subtitle">All coaches currently inside the workshop — filter, sort, and export</p>
    </div>`;

    // Gather family counts for top metrics
    const lhbCount = coaches.filter(c => c.family === 'LHB').length;
    const icfCount = coaches.filter(c => c.family === 'ICF').length;
    const acLocoCount = coaches.filter(c => c.family === 'LOCO' || c.status === 'AC LOCO').length;
    const demuMemuCount = coaches.filter(c => ['DEMU', 'MEMU', 'EMU'].includes(c.family)).length;
    const otherCount = coaches.filter(c => !['LHB', 'ICF', 'LOCO', 'DEMU', 'MEMU', 'EMU'].includes(c.family)).length;

    // Metrics
    html += `<div class="metrics-grid anim-slide" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));">
        ${createMetricCard('Total inside', totalInside, '🏭', 'accent-blue', 'id="live-metric-total-card"')}
        ${createMetricCard('LHB Coaches', `${lhbCount} (of ${lhbCount})`, '🚆', 'accent-info clickable-card', 'id="live-metric-lhb-card" onclick="window.filterLiveByFamily(\'LHB\')"')}
        ${createMetricCard('ICF Coaches', `${icfCount} (of ${icfCount})`, '🚃', 'accent-purple clickable-card', 'id="live-metric-icf-card" onclick="window.filterLiveByFamily(\'ICF\')"')}
        ${createMetricCard('AC Locomotives', `${acLocoCount} (of ${acLocoCount})`, '⚡', 'accent-danger clickable-card', 'id="live-metric-acloco-card" onclick="window.filterLiveByFamily(\'LOCO\')"')}
        ${createMetricCard('DEMU/MEMU/EMU', `${demuMemuCount} (of ${demuMemuCount})`, '🚊', 'accent-success clickable-card', 'id="live-metric-demu-card" onclick="window.filterLiveByFamily(\'DEMU/MEMU\')"')}
        ${createMetricCard('Special & NMG', `${otherCount} (of ${otherCount})`, '💼', 'accent-gold clickable-card', 'id="live-metric-other-card" onclick="window.filterLiveByFamily(\'OTHER\')"')}
    </div>`;

    // Gather unique families
    const families = [...new Set(coaches.map(c => c.family || '').filter(Boolean))].sort();

    // Layout: sidebar + main table
    html += `<div class="live-layout">`;

    // -- Sidebar filters
    html += `<div class="live-sidebar">`;
    html += `<div class="card card-no-hover">
        <div class="card-title">🎛️ Filters</div>
        <div style="display:flex;flex-direction:column;gap:12px;">
            <div class="filter-group">
                <label class="filter-label">Family</label>
                <select class="filter-select" id="lf-family" style="width:100%">
                    <option value="">All Families</option>
                    ${families.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join('')}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Coach Type</label>
                <select class="filter-select" id="lf-coachtype" style="width:100%">
                    <option value="">All Types</option>
                    ${coachTypes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label">Division</label>
                <select class="filter-select" id="lf-division" style="width:100%">
                    <option value="">All Divisions</option>
                    ${divisions.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('')}
                </select>
            </div>
            <label class="checkbox-label">
                <input type="checkbox" id="lf-longstay"> Long Stay Only (>120d)
            </label>
            <div class="filter-group">
                <label class="filter-label">Search</label>
                <input type="text" class="filter-input" id="lf-search" placeholder="Coach number…">
            </div>
            <button class="btn btn-secondary btn-sm" onclick="applyLiveFilters()">Apply</button>
            <button class="btn btn-secondary btn-sm" onclick="clearLiveFilters()">Clear</button>
        </div>
    </div>`;

    // -- Summary by Coach Type
    html += `<div class="card card-no-hover" style="margin-top:12px;">
        <div class="card-title">By Type</div>
        <div id="live-summary-by-type">
            <table class="summary-mini-table">
                ${coachTypes.map(t => {
                const cnt = coaches.filter(c => (c.coach_desc || c.family) === t).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        </div>
    </div>`;

    // -- Summary by Division
    html += `<div class="card card-no-hover" style="margin-top:12px;">
        <div class="card-title">By Division</div>
        <div id="live-summary-by-division">
            <table class="summary-mini-table">
                ${divisions.map(d => {
                    const cnt = coaches.filter(c => (c.division || '') === d).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(d)}')" class="table-link">${escapeHtml(d)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        </div>
    </div>`;

    html += `</div>`; // end sidebar

    // -- Main table area
    html += `<div>`;

    // Action bar
    html += `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <span style="font-size:13px;color:var(--text-secondary);" id="live-count-label">Showing ${totalInside} coaches</span>
        <button class="btn btn-secondary btn-sm" onclick="downloadLiveCSV()">📥 Download CSV</button>
    </div>`;

    // Breakdown card container
    html += `<div id="live-family-breakdown-card" style="margin-bottom: 20px; display: none;"></div>`;

    // Main data table
    const columns = [
        { key: 'coachno', label: 'Coach No.', sortable: true,
          format: (v) => `<a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>`
        },
        { key: 'coach_desc', label: 'Type', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'family', label: 'Family', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterLiveByFamily('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'repair_type', label: 'Repair', sortable: true },
        { key: 'pitnum', label: 'Location', sortable: true },
        { key: 'division', label: 'Division', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'recd_date', label: 'Entry Date', sortable: true, format: v => formatDate(v) },
        { key: 'IN_DAYS', label: 'Days', sortable: true,
          format: (v, row) => {
              const d = row.IN_DAYS;
              if (d === null || d === undefined) return '—';
              return `<span style="font-weight:600;color:${d > 120 ? 'var(--danger)' : d > 60 ? 'var(--gold)' : 'var(--accent)'};">${d}</span>`;
          }
        },
        { key: 'AERIAL_STATUS', label: 'Status', sortable: true,
          format: (v) => {
              const vl = (v || '').toUpperCase();
              let badgeCls = 'badge-info';
              if (vl.includes('UNDER CORROSION')) badgeCls = 'badge-danger';
              else if (vl.includes('DONE')) badgeCls = 'badge-warning';
              else if (vl.includes('PDC')) badgeCls = 'badge-purple';
              return `<span class="badge ${badgeCls}">${escapeHtml(v || 'Normal')}</span>`;
          }
        },
    ];

    const colorRowFn = (row) => {
        const s = (row.AERIAL_STATUS || '').toUpperCase();
        if (s.includes('PDC')) return 'row-purple';
        
        const d = row.IN_DAYS;
        if (d !== null && d !== undefined && d > 120) return 'row-danger';
        if (d !== null && d !== undefined && d > 60) return 'row-warning';
        return 'row-info';
    };

    html += createDataTable(coaches, columns, {
        id: 'live-table',
        height: 500,
        colorRowFn: colorRowFn,
        searchable: false, // we have sidebar search
    });

    // Suspicious coaches
    if (suspicious.length) {
        html += `<div class="suspicious-callout" style="margin-top:20px;">
            <div class="card-title">⚠️ Suspicious — Over 365 Days (${suspicious.length})</div>
            <div class="table-container" style="max-height:250px;overflow-y:auto;">
                <table class="data-table">
                    <thead><tr>
                        <th>Coach No.</th><th>Type</th><th>Days Inside</th><th>Location</th><th>Division</th>
                    </tr></thead>
                    <tbody>
                    ${suspicious.map(c => {
                        return `<tr class="row-danger">
                            <td><a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(String(c.coachno || ''))}')" class="table-link">${escapeHtml(String(c.coachno || ''))}</a></td>
                            <td>${escapeHtml(c.coach_desc || c.family || '')}</td>
                            <td style="font-weight:700;color:var(--danger);">${c.IN_DAYS}</td>
                            <td>${escapeHtml(c.pitnum || '')}</td>
                            <td>${escapeHtml(c.division || '')}</td>
                        </tr>`;
                    }).join('')}
                    </tbody>
                </table>
            </div>
        </div>`;
    }

    // Cross-tab: Division × Coach Type
    if (divisions.length && coachTypes.length) {
        html += `<div style="margin-top:24px;">
            <h3 style="font-size:15px;font-weight:600;color:var(--text-primary);margin-bottom:12px;">Division × Coach Type</h3>
            <div id="live-crosstab-container">
                <div class="table-container" style="overflow-x:auto;">
                    <table class="cross-tab">
                        <thead><tr><th>Division</th>
                            ${coachTypes.map(t => `<th><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></th>`).join('')}
                            <th>Total</th>
                        </tr></thead>
                        <tbody>
                        ${divisions.map(div => {
                            let rowTotal = 0;
                            const cells = coachTypes.map(t => {
                                const cnt = coaches.filter(c => (c.division || '') === div && (c.coach_desc || c.family || '') === t).length;
                                rowTotal += cnt;
                                const cellVal = cnt ? `<a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}'); window.filterLiveByType('${escapeHtml(t)}');" class="table-link">${cnt}</a>` : '·';
                                return `<td>${cellVal}</td>`;
                            }).join('');
                            return `<tr><td style="text-align:left;font-weight:600;"><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}')" class="table-link">${escapeHtml(div)}</a></td>${cells}<td style="font-weight:700;"><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}'); window.filterLiveByType('');" class="table-link">${rowTotal}</a></td></tr>`;
                        }).join('')}
                        <tr style="font-weight:700;background:var(--bg-secondary);">
                            <td style="text-align:left;">Total</td>
                            ${coachTypes.map(t => {
                                const cnt = coaches.filter(c => (c.coach_desc || c.family || '') === t).length;
                                return `<td><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}'); window.filterLiveByDivision('');" class="table-link">${cnt}</a></td>`;
                            }).join('')}
                            <td>${coaches.length}</td>
                        </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;
    }

    html += `</div>`; // end main table area
    html += `</div>`; // end live-layout

    container.innerHTML = html;

    // Attach filter listeners
    setTimeout(() => {
        ['lf-family', 'lf-coachtype', 'lf-division'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    if (id === 'lf-family') {
                        window._customFamilyFilter = null; // Clear card filter on select change
                    }
                    applyLiveFilters();
                });
            }
        });
        const cb = document.getElementById('lf-longstay');
        if (cb) cb.addEventListener('change', applyLiveFilters);
        const searchEl = document.getElementById('lf-search');
        if (searchEl) searchEl.addEventListener('input', debounce(applyLiveFilters, 250));
    }, 50);
}

function applyLiveFilters() {
    if (!_liveData) return;
    const coaches = _liveData.coaches || _liveData || [];

    const familyFilter = (document.getElementById('lf-family') || {}).value || '';
    const typeFilter = (document.getElementById('lf-coachtype') || {}).value || '';
    const divFilter = (document.getElementById('lf-division') || {}).value || '';
    const longOnly = (document.getElementById('lf-longstay') || {}).checked;
    const search = (document.getElementById('lf-search') || {}).value || '';

    let filtered = coaches;

    if (window._customFamilyFilter) {
        filtered = filtered.filter(c => window._customFamilyFilter(c.family));
    } else if (familyFilter) {
        filtered = filtered.filter(c => (c.family || '') === familyFilter);
    }

    if (typeFilter) {
        filtered = filtered.filter(c => (c.coach_desc || c.family || '') === typeFilter);
    }
    if (divFilter) {
        filtered = filtered.filter(c => (c.division || '') === divFilter);
    }
    if (longOnly) {
        filtered = filtered.filter(c => {
            return c.IN_DAYS !== null && c.IN_DAYS !== undefined && c.IN_DAYS > 120;
        });
    }
    if (search) {
        const s = search.toLowerCase();
        filtered = filtered.filter(c => {
            const num = String(c.coachno || '').toLowerCase();
            return num.includes(s);
        });
    }

    // Update family metrics cards inside the current filtered state
    const activeLhb = filtered.filter(c => c.family === 'LHB').length;
    const activeIcf = filtered.filter(c => c.family === 'ICF').length;
    const activeLoco = filtered.filter(c => c.family === 'LOCO' || c.status === 'AC LOCO').length;
    const activeDemu = filtered.filter(c => ['DEMU', 'MEMU', 'EMU'].includes(c.family)).length;
    const activeOther = filtered.filter(c => !['LHB', 'ICF', 'LOCO', 'DEMU', 'MEMU', 'EMU'].includes(c.family)).length;

    const totalEl = document.querySelector('#live-metric-total-card .metric-value');
    if (totalEl) totalEl.textContent = filtered.length;

    const lhbEl = document.querySelector('#live-metric-lhb-card .metric-value');
    if (lhbEl) lhbEl.textContent = `${activeLhb} (of ${coaches.filter(c => c.family === 'LHB').length})`;

    const icfEl = document.querySelector('#live-metric-icf-card .metric-value');
    if (icfEl) icfEl.textContent = `${activeIcf} (of ${coaches.filter(c => c.family === 'ICF').length})`;

    const aclocoEl = document.querySelector('#live-metric-acloco-card .metric-value');
    if (aclocoEl) aclocoEl.textContent = `${activeLoco} (of ${coaches.filter(c => c.family === 'LOCO' || c.status === 'AC LOCO').length})`;

    const demuEl = document.querySelector('#live-metric-demu-card .metric-value');
    if (demuEl) demuEl.textContent = `${activeDemu} (of ${coaches.filter(c => ['DEMU', 'MEMU', 'EMU'].includes(c.family)).length})`;

    const otherEl = document.querySelector('#live-metric-other-card .metric-value');
    if (otherEl) otherEl.textContent = `${activeOther} (of ${coaches.filter(c => !['LHB', 'ICF', 'LOCO', 'DEMU', 'MEMU', 'EMU'].includes(c.family)).length})`;

    // Dynamic family breakdown card logic
    const breakdownDiv = document.getElementById('live-family-breakdown-card');
    if (breakdownDiv) {
        let selectedFamily = '';
        if (window._customFamilyFilter) {
            if (window._customFamilyFilter('DEMU')) {
                selectedFamily = 'DEMU/MEMU/EMU';
            } else {
                selectedFamily = 'Special & NMG';
            }
        } else if (familyFilter) {
            selectedFamily = familyFilter;
            if (selectedFamily === 'LOCO') selectedFamily = 'AC Locomotives';
            else if (selectedFamily === 'OTHER') selectedFamily = 'Special & NMG';
        }

        if (selectedFamily) {
            // Count by coach_desc
            const typeCounts = {};
            // Filter coaches matching this family
            const familyCoaches = coaches.filter(c => {
                if (window._customFamilyFilter) {
                    return window._customFamilyFilter(c.family);
                } else {
                    return (c.family || '') === familyFilter;
                }
            });
            familyCoaches.forEach(c => {
                const type = c.coach_desc || c.family || 'Unknown';
                typeCounts[type] = (typeCounts[type] || 0) + 1;
            });

            const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);

            let breakdownHtml = `
                <div class="card card-no-hover" style="padding: 16px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;">
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between;">
                        <span>📊 Detailed Breakdown: ${escapeHtml(selectedFamily)} (${familyCoaches.length} total inside)</span>
                        <button class="btn btn-secondary btn-sm" style="padding: 2px 8px; font-size: 11px; cursor: pointer;" onclick="window.filterLiveByFamily('')">Clear Filter</button>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            `;

            sortedTypes.forEach(([type, count]) => {
                // Find how many of this type are currently visible under active filters
                const activeCount = filtered.filter(c => (c.coach_desc || c.family || 'Unknown') === type).length;
                breakdownHtml += `
                    <div class="clickable-card" style="background: var(--bg-secondary); border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; gap: 8px; cursor: pointer;" onclick="window.filterLiveByType('${escapeHtml(type)}')">
                        <span style="font-weight: 500; color: var(--text-secondary); font-size: 13px;">${escapeHtml(type)}</span>
                        <span style="background: var(--accent); color: white; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px;">${activeCount} (of ${count})</span>
                    </div>
                `;
            });

            breakdownHtml += `
                    </div>
                </div>
            `;
            breakdownDiv.innerHTML = breakdownHtml;
            breakdownDiv.style.display = '';
        } else {
            breakdownDiv.innerHTML = '';
            breakdownDiv.style.display = 'none';
        }
    }

    // Update table
    const table = document.getElementById('live-table');
    if (table) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');
        const filterNums = new Set(filtered.map(c => String(c.coachno || '')));

        rows.forEach(row => {
            const firstCell = row.querySelector('td');
            if (!firstCell) return;
            const num = firstCell.textContent.trim();
            row.style.display = filterNums.has(num) ? '' : 'none';
        });
    }

    // Update count label
    const label = document.getElementById('live-count-label');
    if (label) label.textContent = `Showing ${filtered.length} of ${coaches.length} coaches`;

    // Update summary tables and crosstab dynamically
    const coachTypes = [...new Set(coaches.map(c => c.coach_desc || c.family || '').filter(Boolean))].sort();
    const divisions = [...new Set(coaches.map(c => c.division || '').filter(Boolean))].sort();

    const summaryByTypeDiv = document.getElementById('live-summary-by-type');
    if (summaryByTypeDiv) {
        summaryByTypeDiv.innerHTML = `
            <table class="summary-mini-table">
                ${coachTypes.map(t => {
                    const cnt = filtered.filter(c => (c.coach_desc || c.family) === t).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        `;
    }

    const summaryByDivDiv = document.getElementById('live-summary-by-division');
    if (summaryByDivDiv) {
        summaryByDivDiv.innerHTML = `
            <table class="summary-mini-table">
                ${divisions.map(d => {
                    const cnt = filtered.filter(c => (c.division || '') === d).length;
                    return `<tr><td><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(d)}')" class="table-link">${escapeHtml(d)}</a></td><td>${cnt}</td></tr>`;
                }).join('')}
            </table>
        `;
    }

    const crosstabContainer = document.getElementById('live-crosstab-container');
    if (crosstabContainer) {
        crosstabContainer.innerHTML = `
            <div class="table-container" style="overflow-x:auto;">
                <table class="cross-tab">
                    <thead><tr><th>Division</th>
                        ${coachTypes.map(t => `<th><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></th>`).join('')}
                        <th>Total</th>
                    </tr></thead>
                    <tbody>
                    ${divisions.map(div => {
                        let rowTotal = 0;
                        const cells = coachTypes.map(t => {
                            const cnt = filtered.filter(c => (c.division || '') === div && (c.coach_desc || c.family || '') === t).length;
                            rowTotal += cnt;
                            const cellVal = cnt ? `<a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}'); window.filterLiveByType('${escapeHtml(t)}');" class="table-link">${cnt}</a>` : '·';
                            return `<td>${cellVal}</td>`;
                        }).join('');
                        return `<tr><td style="text-align:left;font-weight:600;"><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}')" class="table-link">${escapeHtml(div)}</a></td>${cells}<td style="font-weight:700;"><a href="javascript:void(0)" onclick="window.filterLiveByDivision('${escapeHtml(div)}'); window.filterLiveByType('');" class="table-link">${rowTotal}</a></td></tr>`;
                    }).join('')}
                    <tr style="font-weight:700;background:var(--bg-secondary);">
                        <td style="text-align:left;">Total</td>
                        ${coachTypes.map(t => {
                            const cnt = filtered.filter(c => (c.coach_desc || c.family || '') === t).length;
                            return `<td><a href="javascript:void(0)" onclick="window.filterLiveByType('${escapeHtml(t)}'); window.filterLiveByDivision('');" class="table-link">${cnt}</a></td>`;
                        }).join('')}
                        <td>${filtered.length}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
        `;
    }
}

function clearLiveFilters() {
    ['lf-family', 'lf-coachtype', 'lf-division'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    window._customFamilyFilter = null;
    const cb = document.getElementById('lf-longstay');
    if (cb) cb.checked = false;
    const searchEl = document.getElementById('lf-search');
    if (searchEl) searchEl.value = '';
    applyLiveFilters();
}

function downloadLiveCSV() {
    if (!_liveData) return;
    const coaches = _liveData.coaches || _liveData || [];
    const data = coaches.map(c => ({
        'Coach Number': c.coachno || '',
        'Coach Type': c.coach_desc || '',
        'Repair Type': c.repair_type || '',
        'Location': c.pitnum || '',
        'Status': c.AERIAL_STATUS || c.status || '',
        'Division': c.division || '',
        'Entry Date': c.recd_date || '',
        'Days Inside': c.IN_DAYS || '',
        'Family': c.family || '',
    }));
    downloadCSV(data, 'live_position.csv');
}

/* ============================================================
   COACH SEARCH PAGE
   ============================================================ */

async function loadCoachSearch() {
    const container = document.getElementById('main-content');

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">🔍 Coach Search</h1>
                <p class="page-subtitle">Look up any coach by number — view location, status, repair details, and history</p>
            </div>

            <div class="search-box">
                <input type="text" class="search-input" id="coach-search-input"
                       placeholder="Enter coach number (e.g. 04517)" autofocus
                       onkeydown="if(event.key==='Enter') searchCoach()">
                <button class="btn btn-primary" onclick="searchCoach()">Search</button>
            </div>

            <div id="coach-search-results"></div>
        </div>
    `;
}

async function searchCoach() {
    const input = document.getElementById('coach-search-input');
    const resultsDiv = document.getElementById('coach-search-results');
    if (!input || !resultsDiv) return;

    const query = input.value.trim();
    if (!query) {
        resultsDiv.innerHTML = `<div style="color:var(--text-muted);padding:16px;">Please enter a coach number.</div>`;
        return;
    }

    resultsDiv.innerHTML = `<div style="color:var(--text-secondary);padding:16px;">Searching…</div>`;

    try {
        const data = await api('coach/' + encodeURIComponent(query));

        // Handle {matches: [...], count: N} or direct array
        const matches = data.matches || (Array.isArray(data) ? data : [data]);
        
        if (!matches || matches.length === 0 || data.error) {
            resultsDiv.innerHTML = `
                <div class="card" style="text-align:center;padding:32px;">
                    <div style="font-size:32px;margin-bottom:12px;">🔍</div>
                    <div style="color:var(--text-secondary);">No coach found matching <strong style="color:var(--text-primary);font-family:var(--font-mono);">${escapeHtml(query)}</strong></div>
                </div>`;
            return;
        }

        const enrichedHTMLs = await Promise.all(matches.map(async coach => {
            // Determine status badge
            const statusVal = coach.AERIAL_STATUS || coach.status || 'Normal';
            const sl = statusVal.toUpperCase();
            let badgeCls = 'badge-info';
            if (sl.includes('UNDER CORROSION')) badgeCls = 'badge-danger';
            else if (sl.includes('DONE')) badgeCls = 'badge-warning';
            else if (sl.includes('PDC')) badgeCls = 'badge-purple';

            // Build key-value pairs
            const fields = [
                ['Coach Number',     coach.coachno || ''],
                ['Coach Type',       coach.coach_desc || ''],
                ['Repair Type',      coach.repair_type || ''],
                ['Location',         coach.pitnum || ''],
                ['Status',           `<span class="badge ${badgeCls}">${escapeHtml(statusVal)}</span>`],
                ['Division',         coach.division || ''],
                ['Family',           coach.family || ''],
                ['Entry Date',       formatDate(coach.recd_date)],
                ['Days Inside',      coach.IN_DAYS ?? '—'],
                ['POH Days',         coach.pohdays || '—'],
                ['Total Days',       coach.noofdays || '—'],
                ['Year Built',       coach.year_built || '—'],
                ['Make',             coach.make || '—'],
                ['Man Hours',        coach.man_hours || coach.effective_hours || '—'],
                ['Corrosion Status', coach.corrosion_label || '—'],
                ['Corrosion In Date', coach.corr_place || '—'],
                ['Corrosion Comp. Date', coach.corr_comp || '—'],
                ['Bio Tank Stage',    coach.bio_tank_status || '—'],
                ['Lowering Stage',   coach.lowering_status || '—'],
                ['Furnishing Stage', coach.furnishing_status || '—'],
                ['Despatch Stage',   coach.despatch_status || '—'],
                ['Google Sheet PDC', coach.google_pdc || '—'],
                ['Google Remarks',   coach.google_remarks || '—'],
                ['ERP Remarks',      coach.remarks || '—'],
                ['VG Status (Manual)', coach.vg_status || '—'],
                ['VG Date (Manual)', coach.vg_date ? formatDate(coach.vg_date) : '—'],
                ['Physical Despatch (Manual)', coach.physical_status || '—'],
                ['Physical Date (Manual)', coach.physical_date ? formatDate(coach.physical_date) : '—'],
            ];

            let movementsHtml = '';
            try {
                const movements = await api(`coach/${encodeURIComponent(coach.coachno)}/movements`);
                if (movements && movements.length > 0) {
                    movementsHtml = `
                        <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);">
                            <h4 style="font-size:14px;font-weight:600;margin-bottom:12px;color:var(--text-primary);">📍 Shop Location History (Timeline)</h4>
                            <div class="movement-timeline">
                                ${movements.map(m => `
                                    <div class="timeline-step">
                                        <div class="timeline-dot"></div>
                                        <div class="timeline-info">
                                            <div class="timeline-loc">
                                                ${escapeHtml(m.from_location)} &rarr; <strong>${escapeHtml(m.to_location)}</strong>
                                            </div>
                                            <div class="timeline-time">${m.timestamp}</div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                } else {
                    movementsHtml = `
                        <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);color:var(--text-muted);font-size:12px;">
                            📍 No movements logged for this coach.
                        </div>
                    `;
                }
            } catch (me) {
                console.warn('Failed to load movements history', me);
            }

            return `<div class="card coach-detail-card anim-slide" style="margin-bottom:16px;">
                <div class="card-title" style="font-size:18px;">
                    🚃 ${escapeHtml(String(coach.coachno || query))}
                    <span class="badge ${badgeCls}" style="margin-left:8px;">${escapeHtml(statusVal)}</span>
                </div>
                ${fields.map(([k, v]) => `
                    <div class="detail-row">
                        <div class="detail-key">${escapeHtml(k)}</div>
                        <div class="detail-value">${typeof v === 'number' ? v : (v || '—')}</div>
                    </div>
                `).join('')}

                <!-- Manual Updates Form Section -->
                <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);">
                    <h4 style="font-size:14px;font-weight:600;margin-bottom:12px;color:var(--text-primary);">✍️ Update Outturn Milestones (Supabase)</h4>
                    <div class="filter-bar" style="background:transparent;padding:0;margin-bottom:12px;border:none;gap:12px;flex-wrap:wrap;box-shadow:none;">
                        <div class="filter-group" style="min-width:200px;flex:1;">
                            <label class="filter-label" style="font-size:11px;">VG Status</label>
                            <select class="filter-input" id="manual-vg-status-${coach.coachno}">
                                <option value="" ${!coach.vg_status ? 'selected' : ''}>—</option>
                                <option value="Pending" ${coach.vg_status === 'Pending' ? 'selected' : ''}>Pending</option>
                                <option value="Completed" ${coach.vg_status === 'Completed' ? 'selected' : ''}>Completed</option>
                            </select>
                        </div>
                        <div class="filter-group" style="min-width:200px;flex:1;">
                            <label class="filter-label" style="font-size:11px;">VG Date</label>
                            <input type="date" class="filter-input" id="manual-vg-date-${coach.coachno}" value="${coach.vg_date || ''}">
                        </div>
                    </div>
                    <div class="filter-bar" style="background:transparent;padding:0;margin-bottom:16px;border:none;gap:12px;flex-wrap:wrap;box-shadow:none;">
                        <div class="filter-group" style="min-width:200px;flex:1;">
                            <label class="filter-label" style="font-size:11px;">Physical Despatch</label>
                            <select class="filter-input" id="manual-phys-status-${coach.coachno}">
                                <option value="" ${!coach.physical_status ? 'selected' : ''}>—</option>
                                <option value="Pending" ${coach.physical_status === 'Pending' ? 'selected' : ''}>Pending</option>
                                <option value="Despatched" ${coach.physical_status === 'Despatched' ? 'selected' : ''}>Despatched</option>
                            </select>
                        </div>
                        <div class="filter-group" style="min-width:200px;flex:1;">
                            <label class="filter-label" style="font-size:11px;">Despatch Date</label>
                            <input type="date" class="filter-input" id="manual-phys-date-${coach.coachno}" value="${coach.physical_date || ''}">
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="saveManualUpdates('${coach.coachno}')">Save Milestone Updates</button>
                </div>

                ${movementsHtml}
            </div>`;
        }));

        let html = `<div style="color:var(--text-secondary);font-size:13px;margin-bottom:12px;">Found ${matches.length} match${matches.length > 1 ? 'es' : ''}</div>`;
        html += enrichedHTMLs.join('');
        resultsDiv.innerHTML = html;

    } catch (err) {
        resultsDiv.innerHTML = `
            <div class="card" style="text-align:center;padding:32px;">
                <div style="font-size:32px;margin-bottom:12px;">⚠️</div>
                <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Search Error</div>
                <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(err.message)}</div>
            </div>`;
    }
}

async function saveManualUpdates(coachno) {
    const vgStatus = document.getElementById(`manual-vg-status-${coachno}`).value;
    const vgDate = document.getElementById(`manual-vg-date-${coachno}`).value;
    const physStatus = document.getElementById(`manual-phys-status-${coachno}`).value;
    const physDate = document.getElementById(`manual-phys-date-${coachno}`).value;

    showLoading();
    try {
        const response = await fetch('/api/coach/manual_update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                coachno: coachno,
                vg_status: vgStatus,
                vg_date: vgDate,
                physical_status: physStatus,
                physical_date: physDate
            })
        });
        const result = await response.json();
        if (result.success) {
            alert('Milestones updated successfully in Supabase!');
            // Re-run search to refresh display
            searchCoach();
        } else {
            alert('Error updating milestones: ' + result.error);
        }
    } catch (err) {
        alert('Failed to save manual updates: ' + err.message);
    } finally {
        hideLoading();
    }
}
window.saveManualUpdates = saveManualUpdates;

let _outturnData = null;

async function loadOutturn() {
    const container = document.getElementById('main-content');
    showLoading();

    // Default dates: start of current month to today
    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    
    // Format helper for YYYY-MM-DD local timezone
    const formatYMD = (d) => {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const defaultStart = formatYMD(startOfMonth);
    const defaultEnd = formatYMD(now);

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">📊 Outturn</h1>
                <p class="page-subtitle">Track, filter, and analyze coaches outturned (despatched) from the workshop</p>
            </div>

            <!-- Date range selector -->
            <div class="filter-bar">
                <div class="filter-group">
                    <label class="filter-label">From Date</label>
                    <input type="date" class="filter-input" id="outturn-start-date" value="${defaultStart}">
                </div>
                <div class="filter-group">
                    <label class="filter-label">To Date</label>
                    <input type="date" class="filter-input" id="outturn-end-date" value="${defaultEnd}">
                </div>
                <div class="filter-group" style="justify-content: flex-end;">
                    <button class="btn btn-primary" onclick="fetchOutturnData()">Fetch Outturn</button>
                </div>
            </div>

            <div id="outturn-content-area"></div>
        </div>
    `;

    await fetchOutturnData();
    hideLoading();
}

async function fetchOutturnData() {
    const contentArea = document.getElementById('outturn-content-area');
    if (!contentArea) return;

    const startDate = document.getElementById('outturn-start-date').value;
    const endDate = document.getElementById('outturn-end-date').value;

    contentArea.innerHTML = `<div style="text-align:center;padding:48px;color:var(--text-secondary);">Loading outturn records…</div>`;

    try {
        const data = await api('outturn', { start_date: startDate, end_date: endDate });
        _outturnData = data;
        renderOutturnContent(data);
    } catch (err) {
        contentArea.innerHTML = `
            <div class="card" style="text-align:center;padding:48px;margin-top:16px;">
                <div style="font-size:40px;margin-bottom:16px;">⚠️</div>
                <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Failed to load outturn data</div>
                <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(err.message)}</div>
            </div>`;
    }
}

function renderOutturnContent(data) {
    const contentArea = document.getElementById('outturn-content-area');
    if (!contentArea) return;

    const coaches = (data.coaches || []).map(c => ({
        ...c,
        category: window.getCoachCategoryString(c)
    }));
    const metrics = data.metrics || { total: 0, coach_types: {}, divisions: {} };

    const coachTypes = [...new Set(coaches.map(c => c.coach_desc || c.family || '').filter(Boolean))].sort();
    const divisions = [...new Set(coaches.map(c => c.division || '').filter(Boolean))].sort();
    const families = [...new Set(coaches.map(c => c.family || '').filter(Boolean))].sort();
    const categories = [...new Set(coaches.map(c => c.category || '').filter(Boolean))].sort();

    let html = '';

    // Metric cards
    html += `
        <div class="metrics-grid" style="margin-top:20px;">
            ${createMetricCard('Total Outturned', metrics.total, '📦', 'accent-success')}
            ${createMetricCard('Coach Families', Object.keys(metrics.coach_types).length, '📋', 'accent-info')}
            ${createMetricCard('Divisions Reached', Object.keys(metrics.divisions).length, '🏛️', 'accent-purple')}
        </div>
    `;

    // Content layout: filters, mini-tables side by side + main table
    html += `
        <div class="live-layout" style="margin-top:20px;">
            <div class="live-sidebar">
                <!-- Filters card -->
                <div class="card card-no-hover">
                    <div class="card-title">🎛️ Filters</div>
                    <div style="display:flex;flex-direction:column;gap:12px;">
                        <div class="filter-group">
                            <label class="filter-label">Coach Family</label>
                            <select class="filter-select" id="of-family" style="width:100%">
                                <option value="">All Families</option>
                                ${families.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join('')}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Category</label>
                            <select class="filter-select" id="of-category" style="width:100%">
                                <option value="">All Categories</option>
                                ${categories.map(cat => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`).join('')}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Coach Type</label>
                            <select class="filter-select" id="of-coachtype" style="width:100%">
                                <option value="">All Types</option>
                                ${coachTypes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Division</label>
                            <select class="filter-select" id="of-division" style="width:100%">
                                <option value="">All Divisions</option>
                                ${divisions.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('')}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label class="filter-label">Search</label>
                            <input type="text" class="filter-input" id="of-search" placeholder="Coach number…">
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="applyOutturnFilters()">Apply</button>
                        <button class="btn btn-secondary btn-sm" onclick="clearOutturnFilters()">Clear</button>
                    </div>
                </div>

                <div class="card card-no-hover" style="margin-top:12px;">
                    <div class="card-title">Families Outturned</div>
                    <div id="outturn-summary-by-family">
                        <table class="summary-mini-table">
                            ${families.map(f => {
                                const cnt = coaches.filter(c => (c.family || '') === f).length;
                                return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByFamily('${escapeHtml(f)}')" class="table-link">${escapeHtml(f)}</a></td><td>${cnt}</td></tr>`;
                            }).join('')}
                        </table>
                    </div>
                </div>

                <div class="card card-no-hover" style="margin-top:12px;">
                    <div class="card-title">Types Outturned</div>
                    <div id="outturn-summary-by-type">
                        <table class="summary-mini-table">
                            ${coachTypes.map(t => {
                                const cnt = coaches.filter(c => (c.coach_desc || c.family || '') === t).length;
                                return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByType('${escapeHtml(t)}')" class="table-link">${escapeHtml(t)}</a></td><td>${cnt}</td></tr>`;
                            }).join('')}
                        </table>
                    </div>
                </div>

                <div class="card card-no-hover" style="margin-top:12px;">
                    <div class="card-title">To Divisions</div>
                    <div id="outturn-summary-by-division">
                        <table class="summary-mini-table">
                            ${divisions.map(d => {
                                const cnt = coaches.filter(c => (c.division || '') === d).length;
                                return `<tr><td><a href="javascript:void(0)" onclick="window.filterOutturnByDivision('${escapeHtml(d)}')" class="table-link">${escapeHtml(d)}</a></td><td>${cnt}</td></tr>`;
                            }).join('')}
                        </table>
                    </div>
                </div>
            </div>

            <div>
                <!-- Action bar -->
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                    <span style="font-size:13px;color:var(--text-secondary);" id="outturn-count-label">Showing ${coaches.length} outturned coaches</span>
                    <button class="btn btn-secondary btn-sm" onclick="downloadOutturnCSV()">📥 Download CSV</button>
                </div>
    `;

    const columns = [
        { key: 'coachno', label: 'Coach No.', sortable: true,
          format: (v) => `<a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>`
        },
        { key: 'coach_desc', label: 'Type', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterOutturnByType('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'family', label: 'Family', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterOutturnByFamily('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'category', label: 'Category', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterOutturnByCategory('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'repair_type', label: 'Repair', sortable: true },
        { key: 'division', label: 'Division', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterOutturnByDivision('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'recd_date', label: 'Entry Date', sortable: true, format: v => formatDate(v) },
        { key: 'desp_date', label: 'Despatch Date', sortable: true, format: v => formatDate(v) },
    ];

    html += createDataTable(coaches, columns, {
        id: 'outturn-table',
        height: 500,
        searchable: false,
    });

    html += `
            </div>
        </div>
    `;

    contentArea.innerHTML = html;

    // Attach filter listeners after DOM is updated
    setTimeout(() => {
        ['of-coachtype', 'of-division', 'of-family', 'of-category'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => applyOutturnFilters());
        });
        const searchEl = document.getElementById('of-search');
        if (searchEl) searchEl.addEventListener('input', debounce(() => applyOutturnFilters(), 250));
    }, 50);
}

function downloadOutturnCSV() {
    if (!_outturnData) return;
    const coaches = _outturnData.coaches || [];
    const data = coaches.map(c => ({
        'Coach Number': c.coachno || '',
        'Coach Type': c.coach_desc || '',
        'Family': c.family || '',
        'Category': window.getCoachCategoryString(c),
        'Repair Type': c.repair_type || '',
        'Division': c.division || '',
        'Entry Date': c.recd_date || '',
        'Despatch Date': c.desp_date || '',
        'Make': c.make || '',
        'Year Built': c.year_built || '',
    }));
    const startStr = document.getElementById('outturn-start-date').value;
    const endStr = document.getElementById('outturn-end-date').value;
    downloadCSV(data, `outturn_${startStr}_to_${endStr}.csv`);
}

/* ============================================================
   CORROSION ANALYSIS PAGE
   ============================================================ */

let _corrosionData = null;
let _activeCorrosionTab = 'poh-analysis';

function getCorrosionOverrides() {
    try {
        const data = localStorage.getItem('corrosion_overrides');
        return data ? JSON.parse(data) : {};
    } catch (e) {
        return {};
    }
}

function saveCorrosionOverrides(overrides) {
    try {
        localStorage.setItem('corrosion_overrides', JSON.stringify(overrides));
    } catch (e) {
        console.error('Failed to save corrosion overrides', e);
    }
}

window.setCoachOverride = function(coachno, key, value) {
    const overrides = getCorrosionOverrides();
    if (!overrides[coachno]) {
        overrides[coachno] = {};
    }
    
    // Normalize boolean for 'include'
    if (key === 'include') {
        overrides[coachno][key] = !!value;
    } else {
        overrides[coachno][key] = value;
    }
    
    saveCorrosionOverrides(overrides);
    recalculateCorrosionStats();
};

window.resetAllCorrosionOverrides = function() {
    if (confirm('Are you sure you want to clear all manual POH group overrides and inclusion/exclusion settings?')) {
        localStorage.removeItem('corrosion_overrides');
        recalculateCorrosionStats();
    }
};

window.switchCorrosionTab = function(tabId) {

    _activeCorrosionTab = tabId;

    // Toggle active state in navigation buttons
    document.querySelectorAll('.tabs-nav-container .tab-nav-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Toggle display of tab contents
    document.querySelectorAll('.corrosion-tab-content').forEach(content => {
        if (content.id === 'tab-' + tabId) {
            content.style.display = '';
        } else {
            content.style.display = 'none';
        }
    });
};

window.clearCorrosionFilters = function() {
    const familyEl = document.getElementById('cf-family');
    if (familyEl) familyEl.value = 'ALL';
    
    const typeEl = document.getElementById('cf-coachtype');
    if (typeEl) typeEl.value = '';
    
    const suspectEl = document.getElementById('cf-suspect');
    if (suspectEl) suspectEl.value = 'ALL';
    
    const searchEl = document.getElementById('cf-search');
    if (searchEl) searchEl.value = '';
    
    const fysDiv = document.getElementById('cf-fys');
    if (fysDiv) {
        fysDiv.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = true;
        });
    }

    populateCoachTypesFilter();
    recalculateCorrosionStats();
};

async function loadCorrosion() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth(); 
    const currentFYYear = currentMonth >= 3 ? currentYear : currentYear - 1;

    // Generate recent 8 FYs (checking the most recent 3 by default for initial load speed)
    const fys = [];
    for (let i = 0; i < 8; i++) {
        const y = currentFYYear - i;
        const fyStr = `${y}-${String(y + 1).slice(2)}`;
        fys.push({
            year: fyStr,
            checked: i < 3
        });
    }

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">🔧 Corrosion Analysis</h1>
                <p class="page-subtitle">Analyze corrosion severity bands across POH groups, manage suspect data points, and manually override classifications.</p>
            </div>

            <div class="live-layout" style="margin-top:20px;">
                <!-- Sidebar Filters -->
                <div class="live-sidebar">
                    <div class="card card-no-hover">
                        <div class="card-title">🎛️ Filters</div>
                        <div style="display:flex;flex-direction:column;gap:12px;">
                            
                            <div class="filter-group">
                                <label class="filter-label">Financial Year(s)</label>
                                <div style="display:flex;flex-direction:column;gap:6px;margin-top:4px;" id="cf-fys">
                                    ${fys.map(fy => `
                                        <label class="checkbox-label" style="font-weight:normal;">
                                            <input type="checkbox" value="${fy.year}" ${fy.checked ? 'checked' : ''} onchange="fetchCorrosionData()"> ${fy.year}
                                        </label>
                                    `).join('')}
                                </div>
                            </div>

                            <div class="filter-group">
                                <label class="filter-label">Coach Family</label>
                                <select class="filter-select" id="cf-family" style="width:100%" onchange="fetchCorrosionData()">
                                    <option value="ALL">All Families</option>
                                    <option value="LHB">LHB</option>
                                    <option value="ICF">ICF</option>
                                    <option value="DEMU">DEMU</option>
                                    <option value="MEMU">MEMU</option>
                                    <option value="NMG">NMG</option>
                                    <option value="SPECIAL">SPECIAL</option>
                                    <option value="LOCO">LOCO</option>
                                </select>
                            </div>

                            <div class="filter-group">
                                <label class="filter-label">Coach Type</label>
                                <select class="filter-select" id="cf-coachtype" style="width:100%" onchange="recalculateCorrosionStats()">
                                    <option value="">All Types</option>
                                </select>
                            </div>

                            <div class="filter-group">
                                <label class="filter-label">Suspect Filter</label>
                                <select class="filter-select" id="cf-suspect" style="width:100%" onchange="recalculateCorrosionStats()">
                                    <option value="ALL">All Coaches</option>
                                    <option value="SUSPECT">Suspect Only</option>
                                    <option value="OVERRIDDEN">Overridden Only</option>
                                    <option value="EXCLUDED">Excluded Only</option>
                                </select>
                            </div>

                            <div class="filter-group">
                                <label class="filter-label">Search Coach No.</label>
                                <input type="text" class="filter-input" id="cf-search" placeholder="Search number..." oninput="recalculateCorrosionStats()">
                            </div>

                            <button class="btn btn-primary btn-sm" onclick="fetchCorrosionData()">Refresh Data</button>
                            <button class="btn btn-secondary btn-sm" onclick="clearCorrosionFilters()">Reset Filters</button>
                        </div>
                    </div>
                </div>

                <!-- Main Content Area -->
                <div style="flex:1;min-width:0;">
                    <!-- Metrics Row -->
                    <div class="metrics-grid" id="corrosion-metrics-grid" style="margin-bottom:20px;"></div>

                    <!-- Navigation Tabs -->
                    <div class="tabs-nav-container" style="margin-bottom: 20px;">
                        <button class="tab-nav-btn active" data-tab="poh-analysis" onclick="switchCorrosionTab('poh-analysis')">🔬 POH Group Analysis</button>
                        <button class="tab-nav-btn" data-tab="llhw-baseline" id="tab-llhw-btn" onclick="switchCorrosionTab('llhw-baseline')">🆚 vs LLHW Baseline</button>
                        <button class="tab-nav-btn" data-tab="fy-trend" onclick="switchCorrosionTab('fy-trend')">📈 FY Trend</button>
                        <button class="tab-nav-btn" data-tab="coach-list" onclick="switchCorrosionTab('coach-list')">📋 Coach List</button>
                        <button class="tab-nav-btn" data-tab="data-quality" onclick="switchCorrosionTab('data-quality')">🧹 Data Quality</button>
                    </div>

                    <!-- Tab Contents -->
                    <div id="tab-poh-analysis" class="corrosion-tab-content"></div>
                    <div id="tab-llhw-baseline" class="corrosion-tab-content" style="display:none;"></div>
                    <div id="tab-fy-trend" class="corrosion-tab-content" style="display:none;"></div>
                    <div id="tab-coach-list" class="corrosion-tab-content" style="display:none;"></div>
                    <div id="tab-data-quality" class="corrosion-tab-content" style="display:none;"></div>
                </div>
            </div>
        </div>
    `;

    // Fetch initial data
    await fetchCorrosionData();
    hideLoading();
}

window.loadCorrosion = loadCorrosion;

async function fetchCorrosionData() {
    showLoading();
    
    // Read selected FYs
    const fysDiv = document.getElementById('cf-fys');
    const checkedFys = [];
    if (fysDiv) {
        fysDiv.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
            checkedFys.push(cb.value);
        });
    }

    const family = document.getElementById('cf-family').value || 'ALL';
    
    try {
        const queryParams = {};
        if (checkedFys.length > 0) {
            queryParams.fys = checkedFys.join(',');
        }
        queryParams.family = family;

        const data = await api('corrosion/analysis', queryParams);
        _corrosionData = data;

        // Populate Coach Type selector
        populateCoachTypesFilter();

        // Calculate and Render
        recalculateCorrosionStats();
    } catch (e) {
        console.error('Failed to fetch corrosion analysis data', e);
        const activeTabContent = document.getElementById('tab-poh-analysis');
        if (activeTabContent) {
            activeTabContent.innerHTML = `
                <div class="card" style="text-align:center;padding:48px;">
                    <div style="font-size:40px;margin-bottom:16px;">⚠️</div>
                    <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Failed to load corrosion analysis data</div>
                    <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(e.message)}</div>
                </div>`;
        }
    }
    
    hideLoading();
}
window.fetchCorrosionData = fetchCorrosionData;

function populateCoachTypesFilter() {
    const el = document.getElementById('cf-coachtype');
    if (!el || !_corrosionData || !_corrosionData.coaches) return;

    const currentVal = el.value;
    const types = [...new Set(_corrosionData.coaches.map(c => c.coach_desc || c.family || '').filter(Boolean))].sort();

    el.innerHTML = `
        <option value="">All Types</option>
        ${types.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}
    `;

    // Restore selected type if it still exists
    if (types.includes(currentVal)) {
        el.value = currentVal;
    }
}

function recalculateCorrosionStats() {
    if (!_corrosionData || !_corrosionData.coaches) return;

    const coaches = _corrosionData.coaches;
    const overrides = getCorrosionOverrides();

    // 1. Filter values
    const typeFilter = document.getElementById('cf-coachtype').value || '';
    const suspectFilter = document.getElementById('cf-suspect').value || 'ALL';
    const searchFilter = (document.getElementById('cf-search').value || '').trim().toLowerCase();

    let evaluatedCount = 0;
    let includedCount = 0;
    let suspectCount = 0;
    let overriddenCount = 0;
    let excludedCount = 0;

    // 2. Enrich coaches with overrides and apply filtering
    const enrichedCoaches = coaches.map(c => {
        const ovr = overrides[c.coachno] || {};
        
        const isIncluded = (ovr.include !== undefined) ? ovr.include : true;
        const pohGroup = (ovr.poh_group && ovr.poh_group !== 'Auto') ? ovr.poh_group : c.poh_group;
        const hasOverride = (ovr.include !== undefined || (ovr.poh_group !== undefined && ovr.poh_group !== 'Auto'));

        return {
            ...c,
            _is_included: isIncluded,
            _poh_group: pohGroup,
            _has_override: hasOverride
        };
    });

    const filteredCoaches = enrichedCoaches.filter(c => {
        if (typeFilter && (c.coach_desc || c.family || '') !== typeFilter) return false;
        if (searchFilter && !String(c.coachno || '').toLowerCase().includes(searchFilter)) return false;

        if (suspectFilter === 'SUSPECT' && !c.is_suspect) return false;
        if (suspectFilter === 'OVERRIDDEN' && !c._has_override) return false;
        if (suspectFilter === 'EXCLUDED' && c._is_included) return false;

        return true;
    });

    // 3. Aggregate totals
    filteredCoaches.forEach(c => {
        evaluatedCount++;
        if (c.is_suspect) suspectCount++;
        if (c._has_override) overriddenCount++;
        if (!c._is_included) excludedCount++;
        else includedCount++;
    });

    // 4. Render metrics
    const metricsGrid = document.getElementById('corrosion-metrics-grid');
    if (metricsGrid) {
        metricsGrid.innerHTML = `
            ${createMetricCard('Coaches Evaluated', evaluatedCount, '🚃', 'accent-blue')}
            ${createMetricCard('Included in Calculations', includedCount, '✅', 'accent-success')}
            ${createMetricCard('Suspect Coaches', suspectCount, '⚠️', suspectCount > 0 ? 'accent-danger' : 'accent-info')}
            ${createMetricCard('Manual Overrides', overriddenCount, '✏️', overriddenCount > 0 ? 'accent-purple' : 'accent-info')}
        `;
    }

    // 5. LLHW baseline tab display toggle (always active)
    const tabLlhBtn = document.getElementById('tab-llhw-btn');
    if (tabLlhBtn) {
        tabLlhBtn.classList.remove('disabled');
        tabLlhBtn.style.opacity = '1';
        tabLlhBtn.style.cursor = 'pointer';
        tabLlhBtn.title = '';
    }

    // 6. Stats grouping for POH Groups and bands (included only)
    const includedCoaches = filteredCoaches.filter(c => c._is_included);

    const pohGroups = ["1st POH", "2nd POH", "3rd POH", "4th & onwards"];
    const bands = ["L", "LM", "M", "H"];
    const pohStats = {};
    
    pohGroups.forEach(grp => {
        pohStats[grp] = {
            total: 0,
            L: 0,
            LM: 0,
            M: 0,
            H: 0,
            unclassified: 0
        };
    });

    includedCoaches.forEach(c => {
        const grp = c._poh_group;
        const b = c.band;
        
        if (pohStats[grp]) {
            pohStats[grp].total++;
            if (bands.includes(b)) {
                pohStats[grp][b]++;
            } else {
                pohStats[grp].unclassified++;
            }
        }
    });

    // 7. Trigger Renderers
    window._lastFilteredCorrosionCoaches = filteredCoaches;

    renderPohAnalysisTab(pohStats, pohGroups, bands);
    renderLlhBaselineTab(pohStats, pohGroups, bands);
    renderFyTrendTab(includedCoaches, pohGroups, bands);
    renderCoachListTab(filteredCoaches, overrides);
    renderDataQualityTab(filteredCoaches, suspectCount, overriddenCount, excludedCount);
}
window.recalculateCorrosionStats = recalculateCorrosionStats;

function renderCorrosionBarHtml(stats, bands, grp) {
    const total = stats.total || 0;
    if (total === 0) {
        return `<div class="corrosion-bar-empty">No coaches included in this group</div>`;
    }

    const colors = {
        L: '#2471A3',
        LM: '#E67E22',
        M: '#7D6608',
        H: '#F1C40F'
    };
    const labels = {
        L: 'Light (L)',
        LM: 'Light-Medium (LM)',
        M: 'Medium (M)',
        H: 'Heavy (H)'
    };

    let html = `<div class="corrosion-stack-bar">`;
    bands.forEach(b => {
        const count = stats[b] || 0;
        const pct = ((count / total) * 100).toFixed(1);
        if (count > 0) {
            html += `
                <div class="corrosion-bar-segment" style="width:${pct}%;background:${colors[b]};cursor:pointer;" title="${labels[b]}: ${count} (${pct}%)" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}', '${b}')">
                    <span class="segment-label">${pct}%</span>
                </div>
            `;
        }
    });
    html += `</div>`;

    html += `<div class="corrosion-bar-legend">`;
    bands.forEach(b => {
        const count = stats[b] || 0;
        const pct = ((count / total) * 100).toFixed(1);
        html += `
            <div class="legend-item-detail">
                <span class="legend-color-dot" style="background:${colors[b]};"></span>
                <span class="legend-label" style="cursor:pointer;" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}', '${b}')">
                    ${labels[b]}: <strong style="text-decoration:underline;color:var(--accent);">${count}</strong> (<span style="text-decoration:underline;color:var(--accent);">${pct}%</span>)
                </span>
            </div>
        `;
    });
    if (stats.unclassified > 0) {
        const pct = ((stats.unclassified / total) * 100).toFixed(1);
        html += `
            <div class="legend-item-detail">
                <span class="legend-color-dot" style="background:#cbd5e1;"></span>
                <span class="legend-label" style="cursor:pointer;" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}')">
                    Not Filled: <strong style="text-decoration:underline;color:var(--accent);">${stats.unclassified}</strong> (<span style="text-decoration:underline;color:var(--accent);">${pct}%</span>)
                </span>
            </div>
        `;
    }
    html += `</div>`;

    return html;
}

function renderPohAnalysisTab(pohStats, pohGroups, bands) {
    const el = document.getElementById('tab-poh-analysis');
    if (!el) return;

    let html = `<div class="poh-analysis-grid">`;
    pohGroups.forEach(grp => {
        const stats = pohStats[grp];
        html += `
            <div class="card card-no-hover corrosion-analysis-card">
                <div class="corrosion-card-header">
                    <div class="corrosion-card-title">${escapeHtml(grp)}</div>
                    <div class="corrosion-card-badge" style="cursor:pointer;text-decoration:underline;color:var(--accent);" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}')">${stats.total} Coach${stats.total !== 1 ? 'es' : ''}</div>
                </div>
                <div class="corrosion-card-body">
                    ${renderCorrosionBarHtml(stats, bands, grp)}
                </div>
            </div>
        `;
    });
    html += `</div>`;
    el.innerHTML = html;
}

function renderLlhBaselineTab(pohStats, pohGroups, bands) {
    const el = document.getElementById('tab-llhw-baseline');
    if (!el) return;

    const llhwBaseline = {
        "1st POH": { L: 73.0, LM: 25.0, M: 2.0, H: 0.0 },
        "2nd POH": { L: 55.0, LM: 35.0, M: 8.0, H: 2.0 },
        "3rd POH": { L: 40.0, LM: 40.0, M: 15.0, H: 5.0 },
        "4th & onwards": { L: 20.0, LM: 40.0, M: 25.0, H: 15.0 }
    };

    let alertHtml = '';
    let tableRowsHtml = '';

    pohGroups.forEach(grp => {
        const stats = pohStats[grp];
        const total = stats.total || 0;
        const baseline = llhwBaseline[grp];

        if (total === 0) {
            tableRowsHtml += `
                <tr style="border-bottom: 2px solid var(--border);">
                    <td style="font-weight:600;text-align:left;" rowspan="4">${escapeHtml(grp)}</td>
                    <td colspan="4" style="color:var(--text-muted);text-align:center;padding:24px;">No coaches included in this group</td>
                </tr>
            `;
            return;
        }

        const lwPerMH = (((stats.M + stats.H) / total) * 100);
        const llhwMH = baseline.M + baseline.H;
        const diffMH = lwPerMH - llhwMH;
        if (diffMH > 5.0) {
            alertHtml += `
                <div class="alert-callout alert-warning" style="margin-bottom:12px;">
                    <strong>⚠️ High Corrosion Alert for ${escapeHtml(grp)}</strong>: 
                    The combined Medium (M) & Heavy (H) corrosion at LW/PER is <strong>${lwPerMH.toFixed(1)}%</strong>, 
                    which is <strong>${diffMH.toFixed(1)}% higher</strong> than Liluah Workshop's baseline (${llhwMH.toFixed(1)}%).
                </div>
            `;
        }

        bands.forEach((b, idx) => {
            const count = stats[b] || 0;
            const lwPct = ((count / total) * 100);
            const llhwPct = baseline[b];
            const diff = lwPct - llhwPct;
            
            let diffClass = '';
            let diffSign = '';
            if (diff > 1.0) {
                diffClass = (b === 'H' || b === 'M') ? 'text-danger' : 'text-warning';
                diffSign = '+';
            } else if (diff < -1.0) {
                diffClass = 'text-success';
                diffSign = '';
            }

            const isLast = (idx === bands.length - 1);
            const borderStyle = isLast ? 'border-bottom: 2px solid var(--border);' : '';

            tableRowsHtml += `
                <tr style="${borderStyle}">
                    ${idx === 0 ? `<td style="font-weight:600;text-align:left;vertical-align:middle;background:var(--bg-secondary);" rowspan="4"><a href="javascript:void(0)" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}')" style="text-decoration:underline;color:var(--accent);font-weight:700;">${escapeHtml(grp)}</a><br><small style="font-weight:normal;color:var(--text-muted);">${total} coaches</small></td>` : ''}
                    <td style="font-weight:600;">${escapeHtml(b)}</td>
                    <td>${lwPct.toFixed(1)}% <small style="color:var(--text-muted);font-size:11px;cursor:pointer;text-decoration:underline;color:var(--accent);" onclick="window.showCorrosionCoachesModal('${escapeHtml(grp)}', '${b}')">(${count})</small></td>
                    <td>${llhwPct.toFixed(1)}%</td>
                    <td class="${diffClass}" style="font-weight:600;">${diffSign}${diff.toFixed(1)}%</td>
                </tr>
            `;
        });
    });

    el.innerHTML = `
        <div class="card card-no-hover">
            <div class="card-title">🆚 LW/PER vs Liluah Workshop (LLHW) Baseline Comparison</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                Comparing current corrosion distributions against the official Liluah Workshop reference baseline (Letter No. 2023/M(C)/141/2).
            </p>
            ${alertHtml}
            <div class="table-container">
                <table class="data-table" style="text-align:center;">
                    <thead>
                        <tr>
                            <th style="text-align:left;background:var(--bg-secondary);width:200px;">POH Group</th>
                            <th>Severity Band</th>
                            <th>LW/PER (Current)</th>
                            <th>LLHW (Reference)</th>
                            <th>Deviation</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRowsHtml || '<tr><td colspan="5">No data available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

window.showCorrosionCoachesModal = function(pohGroup, severityBand = null) {
    const coaches = window._lastFilteredCorrosionCoaches || [];
    const filtered = coaches.filter(c => {
        // Must be included in stats
        if (!c._is_included) return false;
        // Match POH group
        if (c._poh_group !== pohGroup) return false;
        // Optionally match severity band
        if (severityBand && c.band !== severityBand) return false;
        return true;
    });

    const modal = document.getElementById('analytics-coaches-modal');
    const titleEl = document.getElementById('modal-title');
    const container = document.getElementById('modal-table-container');

    if (modal && titleEl && container) {
        const bandTitle = severityBand ? `Severity Band ${severityBand}` : 'All Severity Bands';
        titleEl.innerHTML = `📋 Corrosion Analysis Coaches — ${escapeHtml(pohGroup)} (${escapeHtml(bandTitle)})`;

        if (filtered.length === 0) {
            container.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-secondary);">No coaches found for this group.</div>`;
        } else {
            let tableHtml = `
                <table class="summary-mini-table" style="width:100%;font-size:12px;border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border);font-weight:600;color:var(--text-primary);text-align:left;">
                            <th style="padding:8px;">Coach No</th>
                            <th style="padding:8px;">Description</th>
                            <th style="padding:8px;">Repair Type</th>
                            <th style="padding:8px;">Corrosion Date</th>
                            <th style="padding:8px;">Band</th>
                            <th style="padding:8px;">Days Inside</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            filtered.forEach(c => {
                let badgeClass = 'badge-info';
                if (c.band === 'LM') badgeClass = 'badge-warning';
                else if (c.band === 'M') badgeClass = 'badge-purple';
                else if (c.band === 'H') badgeClass = 'badge-danger';
                const bandBadge = c.band ? `<span class="badge ${badgeClass}">${escapeHtml(c.band)}</span>` : '—';

                tableHtml += `
                    <tr style="border-bottom:1px solid var(--border);">
                        <td style="padding:8px;font-weight:600;">
                            <a href="javascript:void(0)" onclick="closeAnalyticsModal(); window.navigateToSearch('${escapeHtml(c.coachno)}')" class="table-link">${escapeHtml(c.coachno)}</a>
                        </td>
                        <td style="padding:8px;color:var(--text-secondary);">${escapeHtml(c.coach_desc || c.family || '')}</td>
                        <td style="padding:8px;">${escapeHtml(c.repair_type || '')}</td>
                        <td style="padding:8px;">${escapeHtml(c.corr_date || '')}</td>
                        <td style="padding:8px;">${bandBadge}</td>
                        <td style="padding:8px;color:var(--text-secondary);">${escapeHtml(String(c.IN_DAYS ?? '—'))}</td>
                    </tr>
                `;
            });

            tableHtml += `
                    </tbody>
                </table>
            `;
            container.innerHTML = tableHtml;
        }
        modal.style.display = 'flex';
    }
};

function renderFyTrendTab(includedCoaches, pohGroups, bands) {
    const el = document.getElementById('tab-fy-trend');
    if (!el) return;

    const fys = [...new Set(includedCoaches.map(c => c.fy).filter(Boolean))].sort().reverse();

    if (fys.length === 0) {
        el.innerHTML = `
            <div class="card card-no-hover">
                <div class="card-title">📈 Financial Year Trend Analysis</div>
                <div style="text-align:center;padding:48px;color:var(--text-muted);">No financial year data available to show trends.</div>
            </div>
        `;
        return;
    }

    let rowsHtml = '';
    fys.forEach(fy => {
        pohGroups.forEach((grp, idx) => {
            const fyGroupCoaches = includedCoaches.filter(c => c.fy === fy && c._poh_group === grp);
            const total = fyGroupCoaches.length;

            if (total === 0) {
                rowsHtml += `
                    <tr style="${idx === pohGroups.length - 1 ? 'border-bottom: 2px solid var(--border);' : ''}">
                        ${idx === 0 ? `<td style="font-weight:600;vertical-align:middle;background:var(--bg-secondary);" rowspan="4">${escapeHtml(fy)}</td>` : ''}
                        <td style="font-weight:600;text-align:left;">${escapeHtml(grp)}</td>
                        <td>0</td>
                        <td>—</td>
                        <td>—</td>
                        <td>—</td>
                        <td>—</td>
                    </tr>
                `;
                return;
            }

            const pcts = {};
            bands.forEach(b => {
                const count = fyGroupCoaches.filter(c => c.band === b).length;
                pcts[b] = ((count / total) * 100).toFixed(1) + '%';
            });

            rowsHtml += `
                <tr style="${idx === pohGroups.length - 1 ? 'border-bottom: 2px solid var(--border);' : ''}">
                    ${idx === 0 ? `<td style="font-weight:600;vertical-align:middle;background:var(--bg-secondary);" rowspan="4">${escapeHtml(fy)}</td>` : ''}
                    <td style="font-weight:600;text-align:left;">${escapeHtml(grp)}</td>
                    <td>${total}</td>
                    <td style="color:#2471A3;font-weight:600;">${pcts.L}</td>
                    <td style="color:#E67E22;font-weight:600;">${pcts.LM}</td>
                    <td style="color:#7D6608;font-weight:600;">${pcts.M}</td>
                    <td style="color:#dc2626;font-weight:600;">${pcts.H}</td>
                </tr>
            `;
        });
    });

    el.innerHTML = `
        <div class="card card-no-hover">
            <div class="card-title">📈 Financial Year Trend Analysis</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                Historical percentage distributions of corrosion bands for each POH group across selected financial years.
            </p>
            <div class="table-container">
                <table class="data-table" style="text-align:center;">
                    <thead>
                        <tr>
                            <th style="background:var(--bg-secondary);width:150px;">Financial Year</th>
                            <th style="text-align:left;width:180px;">POH Group</th>
                            <th>Total Coaches</th>
                            <th style="color:#2471A3;">Light (L)</th>
                            <th style="color:#E67E22;">Light-Medium (LM)</th>
                            <th style="color:#7D6608;">Medium (M)</th>
                            <th style="color:#dc2626;">Heavy (H)</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function renderCoachListTab(filteredCoaches, overrides) {
    const el = document.getElementById('tab-coach-list');
    if (!el) return;

    if (filteredCoaches.length === 0) {
        el.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-size:13px;color:var(--text-secondary);">Showing 0 coaches</span>
            </div>
            <div class="card card-no-hover" style="text-align:center;padding:48px;">
                <div style="font-size:32px;margin-bottom:12px;">📋</div>
                <div style="color:var(--text-secondary);">No coaches match the active filters.</div>
            </div>
        `;
        return;
    }

    let rowsHtml = '';
    filteredCoaches.forEach(c => {
        const ovr = overrides[c.coachno] || {};
        const isIncluded = c._is_included;
        const overridePohVal = ovr.poh_group || 'Auto';

        let suspectBadgeHtml = '';
        if (c.is_suspect) {
            const reasonsEscaped = c.suspect_reasons.map(r => `• ${escapeHtml(r)}`).join('<br>');
            suspectBadgeHtml = `
                <span class="badge badge-danger badge-tooltip" style="cursor:help;" 
                      onclick="showSuspectModal('${escapeHtml(c.coachno)}', '${reasonsEscaped}')" 
                      title="${reasonsEscaped.replace(/<br>/g, '\n')}">
                    ⚠️ Anomaly
                </span>
            `;
        }

        let bandBadge = '—';
        if (c.band) {
            let badgeClass = 'badge-info';
            if (c.band === 'LM') badgeClass = 'badge-warning';
            else if (c.band === 'M') badgeClass = 'badge-purple';
            else if (c.band === 'H') badgeClass = 'badge-danger';
            bandBadge = `<span class="badge ${badgeClass}">${escapeHtml(c.band)}</span>`;
        }

        const pohOptions = ["Auto", "1st POH", "2nd POH", "3rd POH", "4th & onwards"];
        const selectHtml = `
            <select class="table-override-select" onchange="setCoachOverride('${escapeHtml(c.coachno)}', 'poh_group', this.value)">
                ${pohOptions.map(opt => {
                    const selected = (opt === overridePohVal) ? 'selected' : '';
                    const label = opt === 'Auto' ? `Auto (${c.poh_group || 'None'})` : opt;
                    return `<option value="${opt}" ${selected}>${label}</option>`;
                }).join('')}
            </select>
        `;

        rowsHtml += `
            <tr class="${!isIncluded ? 'row-dimmed' : (c.is_suspect ? 'row-suspect-highlight' : '')}">
                <td>
                    <input type="checkbox" onchange="setCoachOverride('${escapeHtml(c.coachno)}', 'include', this.checked)" ${isIncluded ? 'checked' : ''}>
                </td>
                <td style="font-weight:600;font-family:var(--font-mono);">
                    <a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(c.coachno)}')" class="table-link">${escapeHtml(c.coachno)}</a>
                </td>
                <td>
                    <span style="font-weight:500;">${escapeHtml(c.coach_desc || '—')}</span><br>
                    <small style="color:var(--text-muted);text-transform:uppercase;">${escapeHtml(c.family || 'OTHER')}</small>
                </td>
                <td>
                    ${escapeHtml(c.year_built_raw || '—')}<br>
                    <small style="color:var(--text-muted);">${c.coach_age !== null ? c.coach_age + ' yrs' : '—'}</small>
                </td>
                <td>
                    ${formatDate(c.recd_date)}<br>
                    <small style="color:var(--text-muted);">${escapeHtml(c.division || '—')}</small>
                </td>
                <td style="vertical-align:middle;">
                    ${selectHtml}
                </td>
                <td>
                    <strong>${c.effective_hrs || '0'}</strong> hrs<br>
                    ${bandBadge}
                </td>
                <td style="text-align:center;">
                    ${suspectBadgeHtml || '<span class="text-success" style="font-size:16px;">✓</span>'}
                </td>
            </tr>
        `;
    });

    el.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <span style="font-size:13px;color:var(--text-secondary);" id="corrosion-count-label">Showing ${filteredCoaches.length} matching coaches</span>
            <button class="btn btn-secondary btn-sm" onclick="downloadCorrosionCSV()">📥 Download CSV</button>
        </div>

        <div class="table-container" style="max-height: 600px;">
            <table class="data-table corrosion-editable-table">
                <thead>
                    <tr>
                        <th style="width:40px;">Inc</th>
                        <th style="width:90px;">Coach No.</th>
                        <th>Type / Family</th>
                        <th style="width:100px;">Year Built / Age</th>
                        <th style="width:110px;">Recd / Division</th>
                        <th style="width:200px;">POH Group Override</th>
                        <th style="width:110px;">Man-Hrs / Band</th>
                        <th style="width:90px;text-align:center;">Data Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>
    `;
}

function renderDataQualityTab(filteredCoaches, suspectCount, overriddenCount, excludedCount) {
    const el = document.getElementById('tab-data-quality');
    if (!el) return;

    const total = filteredCoaches.length;
    const cleanCount = total - suspectCount;
    const cleanPct = total > 0 ? ((cleanCount / total) * 100).toFixed(1) : 100;
    const suspectPct = total > 0 ? ((suspectCount / total) * 100).toFixed(1) : 0;

    let suspectDetailsHtml = '';
    const suspectCoaches = filteredCoaches.filter(c => c.is_suspect);
    if (suspectCoaches.length > 0) {
        suspectDetailsHtml = `
            <div style="margin-top:20px;">
                <h4 style="font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text-primary);">Anomalous Coach List</h4>
                <div class="table-container" style="max-height:250px;">
                    <table class="data-table" style="font-size:12px;">
                        <thead>
                            <tr>
                                <th>Coach No.</th>
                                <th>Type</th>
                                <th>Issues Found</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${suspectCoaches.map(sc => `
                                <tr>
                                    <td style="font-weight:600;font-family:var(--font-mono);">
                                        <a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(sc.coachno)}')" class="table-link">${escapeHtml(sc.coachno)}</a>
                                    </td>
                                    <td>${escapeHtml(sc.coach_desc || sc.family || '—')}</td>
                                    <td style="color:var(--danger);">${sc.suspect_reasons.join(', ')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    el.innerHTML = `
        <div class="card card-no-hover">
            <div class="card-title">🧹 Data Quality Report & Maintenance</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:20px;">
                Review the integrity of imported database records. Clean, correct, or exclude coaches manually.
            </p>

            <div style="display:grid;grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));gap:16px;margin-bottom:24px;">
                <div class="data-quality-stat-box" style="border-left: 4px solid var(--success);">
                    <div style="font-size:24px;font-weight:700;color:var(--success);">${cleanCount} (${cleanPct}%)</div>
                    <div style="font-size:12px;color:var(--text-secondary);">Clean & Reliable Records</div>
                </div>
                <div class="data-quality-stat-box" style="border-left: 4px solid var(--danger);">
                    <div style="font-size:24px;font-weight:700;color:var(--danger);">${suspectCount} (${suspectPct}%)</div>
                    <div style="font-size:12px;color:var(--text-secondary);">Anomaly/Suspect Records</div>
                </div>
                <div class="data-quality-stat-box" style="border-left: 4px solid var(--purple);">
                    <div style="font-size:24px;font-weight:700;color:var(--purple);">${overriddenCount}</div>
                    <div style="font-size:12px;color:var(--text-secondary);">Active Manual Overrides</div>
                </div>
                <div class="data-quality-stat-box" style="border-left: 4px solid var(--text-muted);">
                    <div style="font-size:24px;font-weight:700;color:var(--text-muted);">${excludedCount}</div>
                    <div style="font-size:12px;color:var(--text-secondary);">Coaches Excluded from Calculations</div>
                </div>
            </div>

            <div style="background:var(--bg-secondary);padding:16px;border-radius:var(--radius);border:1px dashed var(--border);">
                <h4 style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">Reset Action</h4>
                <p style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;">
                    This will clear all manual group overrides and inclusion/exclusion decisions stored in this browser.
                </p>
                <button class="btn btn-secondary btn-sm" onclick="resetAllCorrosionOverrides()" style="color:var(--danger);border-color:var(--danger);background:transparent;">
                    🗑️ Reset All Manual Overrides
                </button>
            </div>

            ${suspectDetailsHtml}
        </div>
    `;
}

window.downloadCorrosionCSV = function() {
    if (!_corrosionData || !_corrosionData.coaches) return;
    
    const overrides = getCorrosionOverrides();
    const typeFilter = document.getElementById('cf-coachtype').value || '';
    const suspectFilter = document.getElementById('cf-suspect').value || 'ALL';
    const searchFilter = (document.getElementById('cf-search').value || '').trim().toLowerCase();

    const csvData = _corrosionData.coaches
        .map(c => {
            const ovr = overrides[c.coachno] || {};
            const isIncluded = (ovr.include !== undefined) ? ovr.include : true;
            const pohGroup = (ovr.poh_group && ovr.poh_group !== 'Auto') ? ovr.poh_group : c.poh_group;
            const hasOverride = (ovr.include !== undefined || (ovr.poh_group !== undefined && ovr.poh_group !== 'Auto'));

            return {
                ...c,
                _is_included: isIncluded,
                _poh_group: pohGroup,
                _has_override: hasOverride
            };
        })
        .filter(c => {
            if (typeFilter && (c.coach_desc || c.family || '') !== typeFilter) return false;
            if (searchFilter && !String(c.coachno || '').toLowerCase().includes(searchFilter)) return false;

            if (suspectFilter === 'SUSPECT' && !c.is_suspect) return false;
            if (suspectFilter === 'OVERRIDDEN' && !c._has_override) return false;
            if (suspectFilter === 'EXCLUDED' && c._is_included) return false;

            return true;
        })
        .map(c => ({
            'Coach Number': c.coachno || '',
            'Coach Type': c.coach_desc || '',
            'Family': c.family || '',
            'Included': c._is_included ? 'Yes' : 'No',
            'Original POH Group': c.poh_group || '',
            'Active POH Group': c._poh_group || '',
            'Is Overridden': c._has_override ? 'Yes' : 'No',
            'Year Built': c.year_built || '',
            'Year Built Raw': c.year_built_raw || '',
            'Age': c.coach_age !== null ? c.coach_age : '',
            'Receive Date': c.recd_date || '',
            'Financial Year': c.fy || '',
            'Man Hours': c.effective_hrs || '',
            'Corrosion Band': c.band || '',
            'Is Suspect': c.is_suspect ? 'Yes' : 'No',
            'Suspect Reasons': c.is_suspect ? c.suspect_reasons.join('; ') : ''
        }));

    downloadCSV(csvData, 'corrosion_analysis.csv');
};

window.showSuspectModal = function(coachno, reasons) {
    let modal = document.getElementById('corrosion-suspect-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'corrosion-suspect-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-card">
                <div class="modal-header">
                    <h3>⚠️ Data Anomalies for Coach <span id="modal-coachno"></span></h3>
                    <button class="close-btn" onclick="closeSuspectModal()">&times;</button>
                </div>
                <div class="modal-body" id="modal-reasons" style="margin-top:12px; line-height:1.8;"></div>
                <div class="modal-footer" style="text-align:right;margin-top:16px;">
                    <button class="btn btn-primary btn-sm" onclick="closeSuspectModal()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    document.getElementById('modal-coachno').textContent = coachno;
    document.getElementById('modal-reasons').innerHTML = reasons;
    modal.classList.add('open');
};

window.closeSuspectModal = function() {
    const modal = document.getElementById('corrosion-suspect-modal');
    if (modal) modal.classList.remove('open');
};

/* ============================================================
   POH ANALYSIS PAGE
   ============================================================ */

let _pohAnalysisData = null;
let _pohTargetData = null;
let _activePohTab = 'wks-performance';

async function loadPohAnalysis() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth(); 
    const currentFYYear = currentMonth >= 3 ? currentYear : currentYear - 1;

    // Generate recent 7 FYs
    const fys = [];
    for (let i = 0; i < 7; i++) {
        const y = currentFYYear - i;
        const fyStr = `${y}-${String(y + 1).slice(2)}`;
        fys.push(fyStr);
    }

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">🛠️ POH Analysis</h1>
                <p class="page-subtitle">Analyze performance of previous workshop cycles, audit schedule selections, and evaluate monthly target achievements.</p>
            </div>

            <div class="live-layout" style="margin-top:20px;">
                <!-- Sidebar Filters -->
                <div class="live-sidebar">
                    <div class="card card-no-hover">
                        <div class="card-title">🎛️ Target Filters</div>
                        <div style="display:flex;flex-direction:column;gap:12px;">
                            <div class="filter-group">
                                <label class="filter-label">Financial Year</label>
                                <select class="filter-select" id="pf-fy" style="width:100%" onchange="onPohYearChange()">
                                    ${fys.map(fy => `<option value="${fy}">${fy}</option>`).join('')}
                                </select>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="fetchPohAnalysis()">Refresh Data</button>
                        </div>
                    </div>
                </div>

                <!-- Main Content Area -->
                <div style="flex:1;min-width:0;">
                    <!-- Navigation Tabs -->
                    <div class="tabs-nav-container" style="margin-bottom: 20px;">
                        <button class="tab-nav-btn active" data-tab="wks-performance" onclick="switchPohTab('wks-performance')">🔬 Previous Workshop Performance</button>
                        <button class="tab-nav-btn" data-tab="sched-anomalies" onclick="switchPohTab('sched-anomalies')">🔬 LHB Schedule Analysis</button>
                        <button class="tab-nav-btn" data-tab="target-vs-achievement" onclick="switchPohTab('target-vs-achievement')">🆚 Target vs Achievement</button>
                    </div>

                    <!-- Tab Contents -->
                    <div id="tab-wks-performance" class="poh-tab-content"></div>
                    <div id="tab-sched-anomalies" class="poh-tab-content" style="display:none;"></div>
                    <div id="tab-target-vs-achievement" class="poh-tab-content" style="display:none;"></div>
                </div>
            </div>
        </div>
    `;

    await fetchPohAnalysis();
    hideLoading();
}
window.loadPohAnalysis = loadPohAnalysis;

async function fetchPohAnalysis() {
    showLoading();
    try {
        const fyEl = document.getElementById('pf-fy');
        const fy = fyEl ? fyEl.value : null;
        const data = await api('poh/analysis', fy ? { fy: fy } : {});
        _pohAnalysisData = data;
        _selectedWksFamily = 'ALL';
        _selectedWksDesc = 'ALL';
        renderWksPerformanceTab();
        renderLhbScheduleAnalysisTab();
        
        // Load targets for selected FY
        await fetchPohTargets();
    } catch (e) {
        console.error('Failed to fetch POH analysis data', e);
        const tabWks = document.getElementById('tab-wks-performance');
        if (tabWks) {
            tabWks.innerHTML = `
                <div class="card" style="text-align:center;padding:48px;">
                    <div style="font-size:40px;margin-bottom:16px;">⚠️</div>
                    <div style="color:var(--danger);font-weight:600;margin-bottom:8px;">Failed to load POH analysis data</div>
                    <div style="color:var(--text-secondary);font-size:13px;">${escapeHtml(e.message)}</div>
                </div>`;
        }
    }
    hideLoading();
}
window.fetchPohAnalysis = fetchPohAnalysis;

async function fetchPohTargets() {
    const fyEl = document.getElementById('pf-fy');
    if (!fyEl) return;
    const fy = fyEl.value;
    
    try {
        const data = await api('poh/targets', { fy: fy });
        _pohTargetData = data;
        renderTargetVsAchievementTab();
    } catch (e) {
        console.error('Failed to fetch POH targets data', e);
    }
}
window.fetchPohTargets = fetchPohTargets;

async function onPohYearChange() {
    await fetchPohAnalysis();
}
window.onPohYearChange = onPohYearChange;

let _filteredWorkshops = null;
let _selectedWksFamily = 'ALL';
let _selectedWksDesc = 'ALL';

function renderWksPerformanceTab() {
    const el = document.getElementById('tab-wks-performance');
    if (!el || !_pohAnalysisData || !_pohAnalysisData.workshops) return;
    
    if (typeof _selectedWksFamily === 'undefined') window._selectedWksFamily = 'ALL';
    if (typeof _selectedWksDesc === 'undefined') window._selectedWksDesc = 'ALL';
    
    const workshops = _pohAnalysisData.workshops;
    
    // Gather unique families and descriptions for dropdowns
    const familiesSet = new Set();
    const descSet = new Set();
    
    Object.keys(workshops).forEach(code => {
        const wks = workshops[code];
        if (wks.coaches) {
            wks.coaches.forEach(c => {
                if (c.family) familiesSet.add(c.family);
                if (c.coach_desc) descSet.add(c.coach_desc);
            });
        }
    });
    
    const familiesList = ['ALL', ...Array.from(familiesSet).sort()];
    const descList = ['ALL', ...Array.from(descSet).sort()];
    
    // Recalculate stats based on filters
    const filtered = {};
    Object.keys(workshops).forEach(code => {
        const wks = workshops[code];
        const coaches = wks.coaches || [];
        
        const matched = coaches.filter(c => {
            const famMatch = (_selectedWksFamily === 'ALL' || c.family === _selectedWksFamily);
            const descMatch = (_selectedWksDesc === 'ALL' || c.coach_desc === _selectedWksDesc);
            return famMatch && descMatch;
        });
        
        if (matched.length > 0) {
            const total = matched.length;
            let premature_count = 0;
            const man_hours_list = [];
            const bands = {"Light": 0, "Medium Light": 0, "Medium Heavy": 0, "Very Heavy": 0, "Not Filled": 0};
            
            matched.forEach(c => {
                if (c.is_premature) premature_count++;
                if (c.man_hours > 0) man_hours_list.push(c.man_hours);
                
                let band = "Not Filled";
                const hrs = c.man_hours;
                if (hrs > 0) {
                    if (hrs <= 200) band = "Light";
                    else if (hrs <= 500) band = "Medium Light";
                    else if (hrs <= 1000) band = "Medium Heavy";
                    else band = "Very Heavy";
                }
                bands[band]++;
            });
            
            const avg_hrs = man_hours_list.length > 0 
                ? (man_hours_list.reduce((a, b) => a + b, 0) / man_hours_list.length)
                : 0.0;
            const prem_rate = (premature_count / total) * 100;
            
            const band_pcts = {};
            Object.keys(bands).forEach(b => {
                band_pcts[b] = (bands[b] / total) * 100;
            });
            
            filtered[code] = {
                total_count: total,
                avg_man_hours: Math.round(avg_hrs * 10) / 10,
                premature_count: premature_count,
                premature_rate: Math.round(prem_rate * 10) / 10,
                bands: {
                    "Light": Math.round(band_pcts["Light"] * 10) / 10,
                    "Medium Light": Math.round(band_pcts["Medium Light"] * 10) / 10,
                    "Medium Heavy": Math.round(band_pcts["Medium Heavy"] * 10) / 10,
                    "Very Heavy": Math.round(band_pcts["Very Heavy"] * 10) / 10,
                    "Not Filled": Math.round(band_pcts["Not Filled"] * 10) / 10
                },
                coaches: matched
            };
        }
    });
    
    _filteredWorkshops = filtered;
    
    const wksCodes = Object.keys(filtered).sort((a, b) => filtered[b].total_count - filtered[a].total_count);
    
    let rowsHtml = '';
    wksCodes.forEach(code => {
        const s = filtered[code];
        
        let rateColor = 'var(--text-primary)';
        if (s.premature_rate > 20) rateColor = 'var(--danger)';
        else if (s.premature_rate > 10) rateColor = 'var(--warning)';
        else rateColor = 'var(--success)';
        
        const b = s.bands || { "Light": 0, "Medium Light": 0, "Medium Heavy": 0, "Very Heavy": 0, "Not Filled": 0 };
        
        rowsHtml += `
            <tr>
                <td style="font-weight:700;background:var(--bg-secondary);">
                    <a href="javascript:void(0)" onclick="drillDownWorkshop('${escapeHtml(code)}')" style="color:var(--accent);text-decoration:underline;font-weight:700;">${escapeHtml(code || 'Unknown')}</a>
                </td>
                <td>${s.total_count}</td>
                <td style="font-weight:600;">${s.avg_man_hours > 0 ? s.avg_man_hours + ' hrs' : '—'}</td>
                <td style="color:#2ECC71;font-weight:600;">${b["Light"]}%</td>
                <td style="color:#F1C40F;font-weight:600;">${b["Medium Light"]}%</td>
                <td style="color:#E67E22;font-weight:600;">${b["Medium Heavy"]}%</td>
                <td style="color:#dc2626;font-weight:600;">${b["Very Heavy"]}%</td>
                <td>${s.premature_count}</td>
                <td style="font-weight:700;color:${rateColor};">${s.premature_rate}%</td>
            </tr>
        `;
    });
    
    if (wksCodes.length === 0) {
        rowsHtml = `<tr><td colspan="9" style="text-align:center;color:var(--text-secondary);padding:32px;">No matching data found for selected filters.</td></tr>`;
    }
    
    const familyOptions = familiesList.map(f => `<option value="${f}" ${f === _selectedWksFamily ? 'selected' : ''}>${f}</option>`).join('');
    const descOptions = descList.map(d => `<option value="${d}" ${d === _selectedWksDesc ? 'selected' : ''}>${d}</option>`).join('');
    
    el.innerHTML = `
        <div class="card card-no-hover" style="margin-bottom: 20px;">
            <div class="card-title" style="margin-bottom: 12px;">🔍 Filter Previous Workshop Performance</div>
            <div style="display:flex; gap:16px; flex-wrap:wrap; align-items:flex-end;">
                <div class="filter-group" style="flex:1; min-width:180px;">
                    <label class="filter-label">Coach Family</label>
                    <select class="filter-select" id="wks-filter-family" style="width:100%" onchange="filterWksPerformance()">
                        ${familyOptions}
                    </select>
                </div>
                <div class="filter-group" style="flex:1; min-width:180px;">
                    <label class="filter-label">Coach Description (Type)</label>
                    <select class="filter-select" id="wks-filter-desc" style="width:100%" onchange="filterWksPerformance()">
                        ${descOptions}
                    </select>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn btn-secondary btn-sm" onclick="resetWksFilters()" style="padding: 8px 16px; height: 38px;">Reset</button>
                    <button class="btn btn-primary btn-sm" onclick="downloadWksPerformanceCSV()" style="padding: 8px 16px; height: 38px;">📥 Download Summary</button>
                </div>
            </div>
        </div>

        <div class="card card-no-hover">
            <div class="card-title">🔬 Previous Workshop Performance Analysis</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                Performance metrics of workshops that previously outturned returning coaches, concentrating on man-hours required for repairs (the heavier the repairs, the worse the previous work) and premature out-of-course returns (OR). <strong>Click on a workshop name</strong> to drill down into the list of coaches received from that workshop.
            </p>
            <div class="table-container">
                <table class="data-table" style="text-align:center;">
                    <thead>
                        <tr>
                            <th style="background:var(--bg-secondary);width:120px;">Workshop</th>
                            <th>Coaches Received</th>
                            <th>Avg Man-Hours</th>
                            <th style="color:#2ECC71;">Light (<200h)</th>
                            <th style="color:#F1C40F;">Med Light (200-500h)</th>
                            <th style="color:#E67E22;">Med Heavy (500-1kh)</th>
                            <th style="color:#dc2626;">Heavy (>1kh)</th>
                            <th>Premature Returns (OR)</th>
                            <th>Premature Rate</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
            <div id="wks-drilldown-container" style="display:none;"></div>
        </div>
    `;
}

window.filterWksPerformance = function() {
    const famEl = document.getElementById('wks-filter-family');
    const descEl = document.getElementById('wks-filter-desc');
    _selectedWksFamily = famEl ? famEl.value : 'ALL';
    _selectedWksDesc = descEl ? descEl.value : 'ALL';
    
    renderWksPerformanceTab();
    
    const detailEl = document.getElementById('wks-drilldown-container');
    if (detailEl && detailEl.style.display !== 'none') {
        const wksCode = detailEl.dataset.selectedWks;
        if (wksCode) {
            if (_filteredWorkshops && _filteredWorkshops[wksCode]) {
                drillDownWorkshop(wksCode);
            } else {
                detailEl.style.display = 'none';
            }
        }
    }
};

window.resetWksFilters = function() {
    _selectedWksFamily = 'ALL';
    _selectedWksDesc = 'ALL';
    const famEl = document.getElementById('wks-filter-family');
    const descEl = document.getElementById('wks-filter-desc');
    if (famEl) famEl.value = 'ALL';
    if (descEl) descEl.value = 'ALL';
    renderWksPerformanceTab();
    
    const detailEl = document.getElementById('wks-drilldown-container');
    if (detailEl && detailEl.style.display !== 'none') {
        const wksCode = detailEl.dataset.selectedWks;
        if (wksCode) drillDownWorkshop(wksCode);
    }
};

window.downloadWksPerformanceCSV = function() {
    if (!_filteredWorkshops || Object.keys(_filteredWorkshops).length === 0) {
        alert('No data available to download.');
        return;
    }
    const dataToExport = Object.keys(_filteredWorkshops).map(wksCode => {
        const s = _filteredWorkshops[wksCode];
        const b = s.bands || {};
        return {
            'Workshop': wksCode,
            'Coaches Received': s.total_count,
            'Avg Man-Hours': s.avg_man_hours,
            'Light (<200h) %': b['Light'] || 0,
            'Med Light (200-500h) %': b['Medium Light'] || 0,
            'Med Heavy (500-1kh) %': b['Medium Heavy'] || 0,
            'Heavy (>1kh) %': b['Very Heavy'] || 0,
            'Premature Returns (OR)': s.premature_count,
            'Premature Rate %': s.premature_rate
        };
    });
    
    dataToExport.sort((a, b) => b['Coaches Received'] - a['Coaches Received']);
    
    const fyEl = document.getElementById('pf-fy');
    const fy = fyEl ? fyEl.value : 'analysis';
    downloadCSV(dataToExport, `previous_workshop_performance_${fy}_${_selectedWksFamily}_${_selectedWksDesc}.csv`);
};

window.downloadWksCoachesCSV = function(wksCode) {
    if (!_filteredWorkshops || !_filteredWorkshops[wksCode]) return;
    const coaches = _filteredWorkshops[wksCode].coaches;
    if (!coaches || !coaches.length) return;
    
    const dataToExport = coaches.map(c => ({
        'Coach No': c.coachno,
        'Description': c.coach_desc,
        'Family': c.family,
        'Repair Type': c.repair_type,
        'Received Date': c.recd_date,
        'Man-Hours': c.man_hours || 0,
        'Weight Band': c.weight_band,
        'Is Premature': c.is_premature ? 'YES' : 'NO'
    }));
    
    downloadCSV(dataToExport, `coaches_received_${wksCode}_${_selectedWksFamily}_${_selectedWksDesc}.csv`);
};

window.drillDownWorkshop = function(wksCode) {
    const workshops = _filteredWorkshops || {};
    const s = workshops[wksCode];
    if (!s || !s.coaches) return;
    
    const detailEl = document.getElementById('wks-drilldown-container');
    if (!detailEl) return;
    
    detailEl.dataset.selectedWks = wksCode;
    detailEl.style.display = '';
    
    let coachRows = '';
    s.coaches.forEach(c => {
        coachRows += `
            <tr class="${c.is_premature ? 'row-danger' : ''}">
                <td style="font-weight:700;">${escapeHtml(c.coachno)}</td>
                <td>${escapeHtml(c.coach_desc)}</td>
                <td>${escapeHtml(c.family)}</td>
                <td>${escapeHtml(c.repair_type)}</td>
                <td>${escapeHtml(c.recd_date)}</td>
                <td style="font-weight:600;">${c.man_hours > 0 ? c.man_hours + ' hrs' : '—'}</td>
                <td>
                    <span class="badge ${c.weight_band === 'Very Heavy' ? 'badge-danger' : c.weight_band === 'Medium Heavy' ? 'badge-warning' : c.weight_band === 'Light' ? 'badge-success' : 'badge-info'}">
                        ${escapeHtml(c.weight_band)}
                    </span>
                </td>
                <td style="font-weight:700;color:${c.is_premature ? 'var(--danger)' : 'var(--text-secondary)'};">
                    ${c.is_premature ? '⚠️ Premature (OR)' : 'Normal'}
                </td>
            </tr>
        `;
    });
    
    detailEl.innerHTML = `
        <div class="card card-no-hover" style="margin-top:24px;border:1px solid var(--accent);padding:20px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <h3 style="font-size:15px;font-weight:600;margin:0;color:var(--text-primary);">🔍 Coaches Received from ${escapeHtml(wksCode)} (${s.coaches.length} coaches)</h3>
                <div style="display:flex;gap:8px;">
                    <button class="btn btn-primary btn-sm" onclick="downloadWksCoachesCSV('${escapeHtml(wksCode)}')" style="padding:4px 8px;font-size:11px;">📥 Download Coaches CSV</button>
                    <button class="btn btn-secondary btn-sm" onclick="document.getElementById('wks-drilldown-container').style.display='none'" style="padding:4px 8px;font-size:11px;">✕ Close</button>
                </div>
            </div>
            <div class="table-container" style="max-height:350px;">
                <table class="data-table" style="text-align:center;">
                    <thead>
                        <tr>
                            <th>Coach No</th>
                            <th>Description</th>
                            <th>Family</th>
                            <th>Repair Type</th>
                            <th>Received Date</th>
                            <th>Man-Hours</th>
                            <th>Weight Band</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${coachRows}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    detailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
};

function renderLhbScheduleAnalysisTab() {
    const el = document.getElementById('tab-sched-anomalies');
    if (!el || !_pohAnalysisData || !_pohAnalysisData.lhb_analysis) return;
    
    const lhb = _pohAnalysisData.lhb_analysis;
    const byFy = lhb.by_fy || {};
    const byType = lhb.by_type || {};
    const coaches = lhb.coaches || [];
    
    // 1. Annual Schedule Summary Table
    let fyRowsHtml = '';
    const sortedFys = Object.keys(byFy).sort().reverse();
    sortedFys.forEach(fy => {
        const counts = byFy[fy];
        fyRowsHtml += `
            <tr>
                <td style="font-weight:700;background:var(--bg-secondary);">${escapeHtml(fy)}</td>
                <td style="font-weight:600;color:var(--success);cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}', 'SS1')">${counts["SS1"] || 0}</td>
                <td style="font-weight:700;color:#F1C40F;cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}', 'SS2')">${counts["SS2"] || 0}</td>
                <td style="font-weight:700;color:#E67E22;cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}', 'SS3')">${counts["SS3"] || 0}</td>
                <td style="color:var(--text-secondary);cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}', 'CONV_POH')">${counts["CONV_POH"] || 0}</td>
                <td style="color:var(--text-secondary);cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}', 'OTHER')">${counts["OTHER"] || 0}</td>
                <td style="font-weight:700;background:var(--bg-secondary);cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal('${escapeHtml(fy)}')">${counts["TOTAL"] || 0}</td>
            </tr>
        `;
    });
    
    if (sortedFys.length === 0) {
        fyRowsHtml = '<tr><td colspan="7" style="color:var(--text-secondary);">No LHB schedule history available.</td></tr>';
    }
    
    // 2. Schedule by Coach Type Summary Table
    let typeRowsHtml = '';
    const sortedTypes = Object.keys(byType).sort();
    sortedTypes.forEach(type => {
        const counts = byType[type];
        typeRowsHtml += `
            <tr>
                <td style="font-weight:600;background:var(--bg-secondary);text-align:left;padding-left:16px;">${escapeHtml(type)}</td>
                <td style="cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, 'SS1', '${escapeHtml(type)}')">${counts["SS1"] || 0}</td>
                <td style="font-weight:600;color:#F1C40F;cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, 'SS2', '${escapeHtml(type)}')">${counts["SS2"] || 0}</td>
                <td style="font-weight:600;color:#E67E22;cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, 'SS3', '${escapeHtml(type)}')">${counts["SS3"] || 0}</td>
                <td style="cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, 'CONV_POH', '${escapeHtml(type)}')">${counts["CONV_POH"] || 0}</td>
                <td style="cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, 'OTHER', '${escapeHtml(type)}')">${counts["OTHER"] || 0}</td>
                <td style="font-weight:700;background:var(--bg-secondary);cursor:pointer;text-decoration:underline;" onclick="window.showLhbCoachesModal(null, null, '${escapeHtml(type)}')">${counts["TOTAL"] || 0}</td>
            </tr>
        `;
    });
    
    if (sortedTypes.length === 0) {
        typeRowsHtml = '<tr><td colspan="7" style="color:var(--text-secondary);">No LHB type details available.</td></tr>';
    }
    
    // Save directory globally
    window._lhbCoachesDirectory = coaches;
    
    el.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr;gap:24px;">
            <!-- Section 1: Annual POH/SS schedule summary -->
            <div class="card card-no-hover">
                <div class="card-title">📅 LHB Annual Maintenance Schedule History</div>
                <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                    Year-on-year outturn counts of standardized LHB schedules (SS1, SS2, SS3). This shows exactly how many SS2 and SS3 schedules are performed annually.
                </p>
                <div class="table-container">
                    <table class="data-table" style="text-align:center;">
                        <thead>
                            <tr>
                                <th style="background:var(--bg-secondary);width:150px;">Financial Year</th>
                                <th style="color:var(--success);">SS1 (18m)</th>
                                <th style="color:#F1C40F;">SS2 (36m)</th>
                                <th style="color:#E67E22;">SS3 (72m)</th>
                                <th>Conventional POH</th>
                                <th>Other</th>
                                <th style="background:var(--bg-secondary);">Total LHB</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${fyRowsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Section 2: Schedule by Coach Type breakdown -->
            <div class="card card-no-hover">
                <div class="card-title">🚃 Maintenance Schedules by LHB Coach Type</div>
                <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                    Cumulative distribution of schedules across LHB layouts and descriptions.
                </p>
                <div class="table-container">
                    <table class="data-table" style="text-align:center;">
                        <thead>
                            <tr>
                                <th style="background:var(--bg-secondary);text-align:left;padding-left:16px;">Coach Type / Desc</th>
                                <th style="color:var(--success);">SS1</th>
                                <th style="color:#F1C40F;">SS2</th>
                                <th style="color:#E67E22;">SS3</th>
                                <th>Conventional POH</th>
                                <th>Other</th>
                                <th style="background:var(--bg-secondary);">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${typeRowsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Section 3: Detailed Coach Directory with warnings -->
            <div class="card card-no-hover">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
                    <div>
                        <div class="card-title" style="margin-bottom:4px;">🔍 LHB Coach POH Directory</div>
                        <p style="font-size:13px;color:var(--text-secondary);margin-bottom:0;">
                            Review schedules, physical age, and configuration alignment for all LHB coaches inside or outturned.
                        </p>
                    </div>
                    <div style="display:flex;gap:12px;align-items:center;">
                        <input type="text" id="lhb-coach-search-input" placeholder="Search Coach No/Type..." 
                               oninput="filterLhbCoachDirectory()" 
                               style="background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--border);padding:8px 16px;border-radius:6px;width:240px;outline:none;font-size:13px;">
                        <select id="lhb-coach-filter-sched" onchange="filterLhbCoachDirectory()"
                                style="background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--border);padding:8px 12px;border-radius:6px;outline:none;font-size:13px;cursor:pointer;">
                            <option value="ALL">All Schedules</option>
                            <option value="SS1">SS1</option>
                            <option value="SS2">SS2</option>
                            <option value="SS3">SS3</option>
                            <option value="CONV_POH">Conventional POH</option>
                            <option value="OTHER">Other</option>
                            <option value="WARNING">Has Warnings Only</option>
                        </select>
                    </div>
                </div>
                
                <div class="table-container" style="max-height: 500px;">
                    <table class="data-table" style="text-align:center;" id="lhb-coach-dir-table">
                        <thead>
                            <tr>
                                <th>Coach No</th>
                                <th>Type</th>
                                <th>Schedule</th>
                                <th>Year Built</th>
                                <th>Age</th>
                                <th>Received Date</th>
                                <th>Prev Workshop</th>
                                <th>Alignment / Notes</th>
                            </tr>
                        </thead>
                        <tbody id="lhb-coach-dir-body">
                            <!-- Populated dynamically by filterLhbCoachDirectory -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    filterLhbCoachDirectory();
}

window.showLhbCoachesModal = function(fy = null, schedule = null, coachType = null) {
    const coaches = window._lhbCoachesDirectory || [];
    const filtered = coaches.filter(c => {
        if (fy && c.fy !== fy) return false;
        if (schedule && c.schedule !== schedule) return false;
        if (coachType && c.coach_desc !== coachType) return false;
        return true;
    });

    const modal = document.getElementById('analytics-coaches-modal');
    const titleEl = document.getElementById('modal-title');
    const container = document.getElementById('modal-table-container');

    if (modal && titleEl && container) {
        let titleParts = [];
        if (fy) titleParts.push(fy);
        if (schedule) titleParts.push(schedule);
        if (coachType) titleParts.push(coachType);
        const criteria = titleParts.join(' — ') || 'All LHB Coaches';
        titleEl.innerHTML = `📋 LHB POH Schedule Directory — ${escapeHtml(criteria)}`;

        if (filtered.length === 0) {
            container.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-secondary);">No coaches found for this selection.</div>`;
        } else {
            let tableHtml = `
                <table class="summary-mini-table" style="width:100%;font-size:12px;border-collapse:collapse;">
                    <thead>
                        <tr style="border-bottom:1px solid var(--border);font-weight:600;text-align:left;color:var(--text-primary);">
                            <th style="padding:8px;">Coach No</th>
                            <th style="padding:8px;">Description</th>
                            <th style="padding:8px;">Repair Type</th>
                            <th style="padding:8px;">Schedule</th>
                            <th style="padding:8px;">Age</th>
                            <th style="padding:8px;">Received Date</th>
                            <th style="padding:8px;">Remarks/Issue</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            filtered.forEach(c => {
                tableHtml += `
                    <tr style="border-bottom:1px solid var(--border);">
                        <td style="padding:8px;font-weight:600;">
                            <a href="javascript:void(0)" onclick="closeAnalyticsModal(); window.navigateToSearch('${escapeHtml(c.coachno)}')" class="table-link">${escapeHtml(c.coachno)}</a>
                        </td>
                        <td style="padding:8px;color:var(--text-secondary);">${escapeHtml(c.coach_desc || '')}</td>
                        <td style="padding:8px;">${escapeHtml(c.repair_type || '')}</td>
                        <td style="padding:8px;font-weight:600;">${escapeHtml(c.schedule || '')}</td>
                        <td style="padding:8px;">${escapeHtml(String(c.age !== null ? c.age + 'y' : '—'))}</td>
                        <td style="padding:8px;color:var(--text-secondary);">${formatDate(c.recd_date)}</td>
                        <td style="padding:8px;color:var(--danger);font-size:11px;">${escapeHtml(c.issue || '—')}</td>
                    </tr>
                `;
            });

            tableHtml += `
                    </tbody>
                </table>
            `;
            container.innerHTML = tableHtml;
        }
        modal.style.display = 'flex';
    }
};

window.filterLhbCoachDirectory = function() {
    const searchVal = (document.getElementById('lhb-coach-search-input')?.value || '').trim().toLowerCase();
    const filterSched = document.getElementById('lhb-coach-filter-sched')?.value || 'ALL';
    const selectedFy = document.getElementById('pf-fy')?.value || 'ALL';
    const tbody = document.getElementById('lhb-coach-dir-body');
    if (!tbody || !window._lhbCoachesDirectory) return;
    
    let rowsHtml = '';
    let matchCount = 0;
    
    window._lhbCoachesDirectory.forEach(c => {
        const matchesSearch = c.coachno.toLowerCase().includes(searchVal) || c.coach_desc.toLowerCase().includes(searchVal);
        
        let matchesSched = false;
        if (filterSched === 'ALL') {
            matchesSched = true;
        } else if (filterSched === 'WARNING') {
            matchesSched = !!c.issue;
        } else {
            matchesSched = c.schedule === filterSched;
        }
        
        // Filter by financial year
        const matchesFy = (selectedFy === 'ALL' || c.fy === selectedFy);
        
        if (matchesSearch && matchesSched && matchesFy) {
            matchCount++;
            
            let badgeClass = 'badge-info';
            if (c.schedule === 'SS2') badgeClass = 'badge-warning';
            else if (c.schedule === 'SS3') badgeClass = 'badge-danger';
            else if (c.schedule === 'SS1') badgeClass = 'badge-success';
            else if (c.schedule === 'CONV_POH') badgeClass = 'badge-purple';
            
            rowsHtml += `
                <tr class="${c.issue ? 'row-warning' : ''}">
                    <td style="font-weight:700;">
                        <a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(c.coachno)}')" style="color:var(--accent);text-decoration:underline;font-weight:700;">${escapeHtml(c.coachno)}</a>
                    </td>
                    <td>${escapeHtml(c.coach_desc)}</td>
                    <td>
                        <span class="badge ${badgeClass}">${escapeHtml(c.schedule)}</span>
                    </td>
                    <td>${c.year_built || 'Unknown'}</td>
                    <td style="font-weight:600;">${c.age !== null ? c.age + ' yrs' : '—'}</td>
                    <td>${escapeHtml(c.recd_date)}</td>
                    <td>${escapeHtml(c.last_poh_wks || '—')}</td>
                    <td style="text-align:left;padding-left:16px;">
                        ${c.issue 
                            ? `<span style="color:var(--warning);font-weight:600;">⚠️ ${escapeHtml(c.issue)}</span>`
                            : `<span style="color:var(--success);font-weight:600;">✓ Correct Schedule</span>`
                        }
                    </td>
                </tr>
            `;
        }
    });
    
    if (matchCount === 0) {
        rowsHtml = `
            <tr>
                <td colspan="8" style="padding:32px;color:var(--text-secondary);">No LHB coaches found matching your filters.</td>
            </tr>
        `;
    }
    
    tbody.innerHTML = rowsHtml;
};

function renderTargetVsAchievementTab() {
    const el = document.getElementById('tab-target-vs-achievement');
    if (!el) return;
    
    const fyVal = document.getElementById('pf-fy').value;
    
    if (!_pohTargetData || _pohTargetData.length === 0) {
        el.innerHTML = `
            <div class="card card-no-hover" style="text-align:center;padding:48px;">
                <div style="font-size:32px;margin-bottom:12px;">🆚</div>
                <div style="color:var(--text-secondary);font-weight:600;margin-bottom:8px;">No outturn targets synced for FY ${escapeHtml(fyVal)}</div>
                <div style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Please use the Data Tools page to sync targets from your Google Sheet.</div>
                <button class="btn btn-secondary btn-sm" onclick="location.hash='#data-tools'">💾 Go to Data Tools</button>
            </div>
        `;
        return;
    }
    
    // Check if monthly data is present and generate Annual Summary
    const hasMonthly = _pohTargetData.some(r => r.type === 'monthly');
    let summaryHtml = '';
    
    // Determine maximum completed month name for YTD cumulative list
    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();
    const currentMonth = currentDate.getMonth() + 1;
    const currentFYStart = currentMonth >= 4 ? currentYear : currentYear - 1;
    const currentFYStr = `${currentFYStart}-${String(currentFYStart + 1).slice(2)}`;
    
    let maxMonthName = 'March';
    if (fyVal === currentFYStr) {
        const monthNames = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];
        maxMonthName = monthNames[(currentMonth - 4 + 12) % 12];
    }
    
    if (hasMonthly) {
        const familySummary = {};
        _pohTargetData.forEach(r => {
            if (r.type === 'monthly') {
                const fam = r.family;
                if (!familySummary[fam]) {
                    familySummary[fam] = { target: 0, actual: 0 };
                }
                familySummary[fam].target += r.target;
                familySummary[fam].actual += r.actual;
            }
        });
        
        let summaryRows = '';
        Object.keys(familySummary).sort().forEach(fam => {
            const sumData = familySummary[fam];
            const variance = sumData.actual - sumData.target;
            
            let varColor = 'var(--text-primary)';
            let varSign = '';
            if (variance > 0) {
                varColor = 'var(--success)';
                varSign = '+';
            } else if (variance < 0) {
                varColor = 'var(--danger)';
            }
            
            const actualCell = sumData.actual;
            
            summaryRows += `
                <tr>
                    <td style="font-weight:700;text-align:left;padding-left:16px;">${escapeHtml(fam)}</td>
                    <td>${sumData.target}</td>
                    <td>${actualCell}</td>
                    <td style="font-weight:700;color:${varColor};">${varSign}${variance}</td>
                </tr>
            `;
        });
        
        summaryHtml = `
            <div class="card card-no-hover" style="margin-bottom:24px;border:1px solid var(--border);">
                <div class="card-title" style="font-size:15px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
                    <span>📊 Annual Summary (YTD Cumulative)</span>
                    <span class="badge badge-success" style="font-size:11px;">Calculated</span>
                </div>
                <div class="table-container">
                    <table class="data-table" style="text-align:center;">
                        <thead>
                            <tr>
                                <th style="text-align:left;padding-left:16px;">Coach Family</th>
                                <th>Total Target</th>
                                <th>Total Achieved</th>
                                <th>Variance</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${summaryRows}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    
    let rowsHtml = '';
    _pohTargetData.forEach(r => {
        const isMonthly = r.type === 'monthly';
        const periodStr = isMonthly ? r.month_name : 'Full Year';
        
        let varColor = 'var(--text-primary)';
        let varSign = '';
        if (r.variance > 0) {
            varColor = 'var(--success)';
            varSign = '+';
        } else if (r.variance < 0) {
            varColor = 'var(--danger)';
        }
        
        const targetMonth = isMonthly ? r.month_name : 'March';
        const actualCell = r.actual;
            
        rowsHtml += `
            <tr>
                <td style="font-weight:600;background:var(--bg-secondary);">${escapeHtml(periodStr)}</td>
                <td style="font-weight:700;">${escapeHtml(r.family)}</td>
                <td>${r.target}</td>
                <td>${actualCell}</td>
                <td style="font-weight:700;color:${varColor};">${varSign}${r.variance}</td>
            </tr>
        `;
    });
    
    el.innerHTML = `
        ${summaryHtml}
        <div class="card card-no-hover">
            <div class="card-title">🆚 Target vs Achievement Comparison (FY ${escapeHtml(fyVal)})</div>
            <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                Outturn target numbers mapped against actual workshop outturned coach counts. 
                Displays month-wise comparisons for the current year, and annual summaries for previous years.
            </p>
            <div class="table-container" style="max-height: 450px;">
                <table class="data-table" style="text-align:center;">
                    <thead>
                        <tr>
                            <th style="background:var(--bg-secondary);width:150px;">Period</th>
                            <th>Coach Family</th>
                            <th>Target Outturn</th>
                            <th>Actual Outturn</th>
                            <th>Variance</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

window.switchPohTab = function(tabId) {
    _activePohTab = tabId;
    document.querySelectorAll('.poh-tab-content').forEach(el => {
        el.style.display = el.id === 'tab-' + tabId ? '' : 'none';
    });
    
    // Toggle active tab nav class
    document.querySelectorAll('.tabs-nav-container .tab-nav-btn').forEach(btn => {
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes('switchPohTab')) {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        }
    });
};

/* ============================================================
   DATA TOOLS PAGE
   ============================================================ */

async function loadDataTools() {
    const container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">💾 Data Tools</h1>
                <p class="page-subtitle">Manage external integrations, trigger data syncs, and review system database operations.</p>
            </div>

            <div style="display:grid;grid-template-columns:1fr;gap:20px;margin-top:20px;">
                <!-- Google Sheets Sync Card -->
                <div class="card card-no-hover" style="padding:24px;">
                    <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;color:var(--text-primary);">🔄 Google Sheet Target Sync</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                        Import targets for month-wise (2026-27) and year-wise (Archive) outturn comparisons. Uses credentials file at:
                        <code style="font-family:var(--font-mono);background:var(--bg-secondary);padding:3px 6px;border-radius:4px;font-size:12px;">D:\\JIJO\\information\\Coach Position\\credentials.json</code>
                    </p>
                    <div style="display:flex;align-items:center;gap:16px;">
                        <button class="btn btn-primary" onclick="triggerGoogleSheetSync()">🔄 Sync Targets Now</button>
                        <span id="sync-status-msg" style="font-size:13px;font-weight:600;"></span>
                    </div>
                </div>

                <!-- Supabase Sync Card -->
                <div class="card card-no-hover" style="padding:24px;">
                    <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;color:var(--text-primary);">🔄 ERP to Supabase Coach Sync</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                        Synchronize active workshop coaches and historical outturn records from the local ERP system to the cloud Supabase database.
                    </p>
                    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
                        <button class="btn btn-primary" id="btn-sync-incremental" onclick="triggerErpSync('incremental')">⚡ Sync Last 45 Days (Fast)</button>
                        <button class="btn btn-secondary" id="btn-sync-full" onclick="triggerErpSync('full')">🔄 Sync Full History (Since 1990)</button>
                    </div>
                    <div id="erp-sync-status-container" style="font-size:13px;padding:12px;border-radius:6px;background:var(--bg-secondary);display:none;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span>Status:</span>
                            <strong id="erp-sync-status-val">—</strong>
                        </div>
                        <div id="erp-sync-mode-row" style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span>Mode:</span>
                            <strong id="erp-sync-mode-val">—</strong>
                        </div>
                        <div id="erp-sync-time-row" style="display:flex;justify-content:space-between;margin-bottom:6px;">
                            <span>Started:</span>
                            <span id="erp-sync-time-val">—</span>
                        </div>
                        <div id="erp-sync-error-row" style="color:var(--danger);margin-top:6px;display:none;">
                            <span>Error:</span>
                            <span id="erp-sync-error-val"></span>
                        </div>
                    </div>
                </div>

                <!-- Database Status Card -->
                <div class="card card-no-hover" style="padding:24px;">
                    <h3 style="font-size:16px;font-weight:600;margin-bottom:8px;color:var(--text-primary);">💾 Database Configuration</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
                        The app stores coach movement logs and targets inside a local database. Supabase external database integration can be enabled.
                    </p>
                    <div style="display:flex;flex-direction:column;gap:10px;">
                        <div class="detail-row" style="padding:8px 0;border-bottom:1px solid var(--border);">
                            <div class="detail-key" style="font-weight:600;">SQLite Local Store</div>
                            <div class="detail-value text-success" style="font-weight:700;">✓ Connected (Local database active)</div>
                        </div>
                        <div class="detail-row" style="padding:8px 0;">
                            <div class="detail-key" style="font-weight:600;">Supabase Sync Integration</div>
                            <div class="detail-value" style="color:var(--text-muted);">Disconnected (Using SQLite local store)</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Start polling sync status
    pollErpSyncStatus();
    if (erpSyncInterval) clearInterval(erpSyncInterval);
    erpSyncInterval = setInterval(pollErpSyncStatus, 2000);
}
window.loadDataTools = loadDataTools;

async function triggerGoogleSheetSync() {
    const statusMsg = document.getElementById('sync-status-msg');
    if (!statusMsg) return;
    
    statusMsg.textContent = 'Syncing targets...';
    statusMsg.style.color = 'var(--text-muted)';
    
    try {
        const res = await api('targets/sync');
        if (res.success) {
            statusMsg.textContent = `✓ Success! Synced ${res.hq_records} HQ targets and ${res.archive_records} Archive targets.`;
            statusMsg.style.color = 'var(--success)';
        } else {
            statusMsg.textContent = `❌ Sync failed: ${res.error}`;
            statusMsg.style.color = 'var(--danger)';
        }
    } catch (e) {
        statusMsg.textContent = `❌ Sync error: ${e.message}`;
        statusMsg.style.color = 'var(--danger)';
    }
}
window.triggerGoogleSheetSync = triggerGoogleSheetSync;

async function triggerErpSync(mode) {
    const btnInc = document.getElementById('btn-sync-incremental');
    const btnFull = document.getElementById('btn-sync-full');
    
    if (btnInc) btnInc.disabled = true;
    if (btnFull) btnFull.disabled = true;
    
    try {
        const res = await fetch('/api/sync/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ mode: mode })
        });
        const data = await res.json();
        if (data.success) {
            pollErpSyncStatus();
            if (erpSyncInterval) clearInterval(erpSyncInterval);
            erpSyncInterval = setInterval(pollErpSyncStatus, 2000);
        } else {
            alert('Error starting sync: ' + (data.error || 'Unknown error'));
            if (btnInc) btnInc.disabled = false;
            if (btnFull) btnFull.disabled = false;
        }
    } catch (e) {
        alert('Network error: ' + e.message);
        if (btnInc) btnInc.disabled = false;
        if (btnFull) btnFull.disabled = false;
    }
}
window.triggerErpSync = triggerErpSync;

async function pollErpSyncStatus() {
    const container = document.getElementById('erp-sync-status-container');
    const statusVal = document.getElementById('erp-sync-status-val');
    const modeVal = document.getElementById('erp-sync-mode-val');
    const timeVal = document.getElementById('erp-sync-time-val');
    const errorRow = document.getElementById('erp-sync-error-row');
    const errorVal = document.getElementById('erp-sync-error-val');
    const btnInc = document.getElementById('btn-sync-incremental');
    const btnFull = document.getElementById('btn-sync-full');
    
    if (!container) return;
    
    try {
        const res = await fetch('/api/sync/status');
        const status = await res.json();
        
        container.style.display = status.status !== 'idle' ? 'block' : 'none';
        
        if (status.status !== 'idle') {
            statusVal.textContent = status.status.toUpperCase();
            if (status.status === 'running') {
                statusVal.style.color = 'var(--accent)';
                if (btnInc) btnInc.disabled = true;
                if (btnFull) btnFull.disabled = true;
            } else if (status.status === 'success') {
                statusVal.style.color = 'var(--success)';
                if (btnInc) btnInc.disabled = false;
                if (btnFull) btnFull.disabled = false;
                if (erpSyncInterval) {
                    clearInterval(erpSyncInterval);
                    erpSyncInterval = null;
                }
            } else if (status.status === 'failed') {
                statusVal.style.color = 'var(--danger)';
                if (btnInc) btnInc.disabled = false;
                if (btnFull) btnFull.disabled = false;
                if (erpSyncInterval) {
                    clearInterval(erpSyncInterval);
                    erpSyncInterval = null;
                }
            }
            
            modeVal.textContent = status.mode === 'full' ? 'Full Sync' : 'Incremental Sync (1-Week)';
            
            const start = status.started_at ? new Date(status.started_at) : null;
            const end = status.finished_at ? new Date(status.finished_at) : null;
            if (start) {
                let timeText = start.toLocaleTimeString();
                if (end) {
                    const duration = Math.round((end - start) / 1000);
                    timeText += ` (took ${duration}s)`;
                }
                timeVal.textContent = timeText;
            } else {
                timeVal.textContent = '—';
            }
            
            if (status.error) {
                errorRow.style.display = 'block';
                errorVal.textContent = status.error;
            } else {
                errorRow.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Error polling sync status:', e);
    }
}
window.pollErpSyncStatus = pollErpSyncStatus;

/* ============================================================
   ANALYTICS DASHBOARD PAGE
   ============================================================ */

let _analyticsTargetData = null;
let _analyticsOutturnData = null;
let _analyticsPrevOutturnData = null;
let _analyticsLiveData = null;

async function loadAnalytics() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">📈 Analytics Dashboard</h1>
                <p class="page-subtitle">Visual performance indicators, outturn trend charts, and workshop operational analytics.</p>
            </div>

            <!-- Filters Bar -->
            <div class="card card-no-hover" style="padding:16px;margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;background:var(--bg-secondary);border:1px solid var(--border);">
                <div>
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Financial Year</label>
                    <select class="filter-select" id="analytics-fy" style="width:140px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 10px;" onchange="fetchAnalyticsData()">
                        <option value="2026-27" selected>2026-27</option>
                        <option value="2025-26">2025-26</option>
                        <option value="2024-25">2024-25</option>
                        <option value="2023-24">2023-24</option>
                        <option value="2022-23">2022-23</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Filter Coach Category</label>
                    <select class="filter-select" id="analytics-family" style="width:200px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 10px;" onchange="renderAnalyticsCharts()">
                        <!-- Dynamic categories populated from synced target list -->
                    </select>
                </div>
                <div style="margin-left:auto;display:flex;gap:10px;align-self:flex-end;">
                    <button class="btn btn-secondary btn-sm" onclick="fetchAnalyticsData()">🔄 Refresh Data</button>
                </div>
            </div>

            <!-- Charts Grid (Target vs Achievement & Cycle Time) -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(450px, 1fr));gap:20px;margin-bottom:20px;">
                <div class="card card-no-hover" style="padding:20px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;">
                    <h3 id="analytics-title-target" style="font-size:15px;font-weight:600;margin-bottom:16px;color:var(--text-primary);">🆚 Target vs Achievement Trend</h3>
                    <div style="position:relative;height:300px;width:100%;">
                        <canvas id="chart-target-vs-achievement"></canvas>
                    </div>
                </div>

                <div class="card card-no-hover" style="padding:20px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;">
                    <h3 id="analytics-title-cycle" style="font-size:15px;font-weight:600;margin-bottom:16px;color:var(--text-primary);">📊 Monthly Outturn Achievement</h3>
                    <div style="position:relative;height:300px;width:100%;">
                        <canvas id="chart-cycle-time"></canvas>
                    </div>
                </div>
            </div>

            <!-- Cumulative Outturn Comparison & Required Rate (Cricket Worm Chart) -->
            <div class="card card-no-hover" style="padding:20px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;margin-bottom:20px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;">
                    <div>
                        <h3 style="font-size:15px;font-weight:600;color:var(--text-primary);margin:0;">📈 Cumulative Outturn & Required Rate (Cricket Comparison)</h3>
                        <p style="font-size:12px;color:var(--text-secondary);margin:4px 0 0;">Compare cumulative outturn progress against target and previous year</p>
                    </div>
                    <div id="analytics-required-rate-badge" style="background:rgba(79, 140, 255, 0.15);border:1px solid var(--accent);color:var(--accent);padding:6px 12px;border-radius:6px;font-size:13px;font-weight:600;">
                        Required Rate: -- coaches/month
                    </div>
                </div>
                <div style="display:grid;grid-template-columns: 2fr 1fr; gap:20px; min-height: 320px; align-items: start;">
                    <div style="position:relative;height:320px;width:100%;">
                        <canvas id="chart-cumulative-comparison"></canvas>
                    </div>
                    <div style="overflow-x:auto;max-height:320px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;padding:10px;">
                        <table class="summary-mini-table" style="font-size:12px;width:100%;border-collapse:collapse;" id="cumulative-comparison-table">
                            <thead>
                                <tr style="border-bottom:1px solid var(--border);font-weight:600;color:var(--text-primary);">
                                    <th style="padding:6px;text-align:left;">Month</th>
                                    <th style="padding:6px;text-align:right;">Target (Cum)</th>
                                    <th style="padding:6px;text-align:right;">Actual (Cum)</th>
                                    <th style="padding:6px;text-align:right;">Prev Actual (Cum)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Rendered dynamically -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Charts Grid (Coach Mix & Division Share) -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(450px, 1fr));gap:20px;">
                <div class="card card-no-hover" style="padding:20px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;">
                    <h3 id="analytics-title-mix" style="font-size:15px;font-weight:600;margin-bottom:16px;color:var(--text-primary);">📊 Current Shop Load - Coach Family</h3>
                    <div style="position:relative;height:300px;width:100%;display:flex;justify-content:center;align-items:center;">
                        <div style="height:100%;width:80%;">
                            <canvas id="chart-coach-mix"></canvas>
                        </div>
                    </div>
                </div>

                <div class="card card-no-hover" style="padding:20px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;">
                    <h3 id="analytics-title-div" style="font-size:15px;font-weight:600;margin-bottom:16px;color:var(--text-primary);">🏢 Current Shop Load - Division Share</h3>
                    <div style="position:relative;height:300px;width:100%;">
                        <canvas id="chart-division-share"></canvas>
                    </div>
                </div>
            </div>
        </div>
    `;

    await fetchAnalyticsData();
}
window.loadAnalytics = loadAnalytics;

async function fetchAnalyticsData() {
    showLoading();
    const fyEl = document.getElementById('analytics-fy');
    if (!fyEl) return;
    const fyVal = fyEl.value;

    const startYear = parseInt(fyVal.split('-')[0]);
    const start_date = `${startYear}-04-01`;
    const end_date = `${startYear + 1}-03-31`;

    const prevStartYear = startYear - 1;
    const prev_start_date = `${prevStartYear}-04-01`;
    const prev_end_date = `${prevStartYear + 1}-03-31`;

    try {
        // Fetch target vs achievement comparison data
        _analyticsTargetData = await api('poh/targets', { fy: fyVal });
        
        // Populate category dropdown dynamically from actual targets present
        populateAnalyticsFamilyDropdown(_analyticsTargetData || []);
        
        // Fetch outturns for the selected financial year
        const outturnRes = await api('outturn', { start_date: start_date, end_date: end_date });
        _analyticsOutturnData = outturnRes ? outturnRes.coaches : [];

        // Fetch outturns for the previous financial year
        const prevOutturnRes = await api('outturn', { start_date: prev_start_date, end_date: prev_end_date });
        _analyticsPrevOutturnData = prevOutturnRes ? prevOutturnRes.coaches : [];

        // Fetch live active coaches
        const liveRes = await api('live');
        _analyticsLiveData = liveRes ? liveRes.coaches : [];

        renderAnalyticsCharts();
    } catch (e) {
        console.error('Failed to fetch analytics data', e);
    } finally {
        hideLoading();
    }
}

function populateAnalyticsFamilyDropdown(targetsData) {
    const selectEl = document.getElementById('analytics-family');
    if (!selectEl) return;
    const currentVal = selectEl.value;
    
    // Gather unique category names from target data (like 'LHB SS1 AC', 'ICF POH NAC', etc.)
    const uniqueCats = [...new Set(targetsData.map(r => r.family))].sort();
    
    let html = '<option value="ALL">All Categories</option>';
    uniqueCats.forEach(cat => {
        html += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
    });
    
    selectEl.innerHTML = html;
    if (currentVal && uniqueCats.includes(currentVal)) {
        selectEl.value = currentVal;
    } else {
        selectEl.value = "ALL";
    }
}
window.fetchAnalyticsData = fetchAnalyticsData;

function renderAnalyticsCharts() {
    window.myCharts = window.myCharts || {};
    const fyVal = document.getElementById('analytics-fy').value;
    const familyFilter = document.getElementById('analytics-family').value;
    const isCurrentYear = (fyVal === '2026-27');

    const colors = {
        accent: '#4f8cff',
        success: '#2ecc71',
        info: '#3498db',
        warning: '#f1c40f',
        purple: '#9b59b6',
        danger: '#e74c3c',
        gray: '#95a5a6'
    };

    // Helper to diff dates
    function getDaysDiff(d1Str, d2Str) {
        if (!d1Str || !d2Str) return 0;
        const parse = (s) => {
            if (s.includes('-')) return new Date(s);
            if (s.includes('/')) {
                const parts = s.split('/');
                let yr = parseInt(parts[2], 10);
                if (yr < 100) yr += 2000;
                return new Date(yr, parts[1] - 1, parts[0]);
            }
            return new Date(s);
        };
        const d1 = parse(d1Str);
        const d2 = parse(d2Str);
        const diffTime = Math.abs(d2 - d1);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }

    // Update Card Titles dynamically for Year Context
    const tTarget = document.getElementById('analytics-title-target');
    const tCycle = document.getElementById('analytics-title-cycle');
    const tMix = document.getElementById('analytics-title-mix');
    const tDiv = document.getElementById('analytics-title-div');

    if (tTarget) {
        tTarget.innerHTML = isCurrentYear 
            ? `🆚 Target vs Achievement Trend (FY ${escapeHtml(fyVal)})` 
            : `🆚 Annual Target vs Achievement Summary (FY ${escapeHtml(fyVal)})`;
    }
    if (tCycle) {
        tCycle.innerHTML = `📊 Monthly Outturn Achievement — FY ${escapeHtml(fyVal)}`;
    }
    if (tMix) {
        tMix.innerHTML = isCurrentYear 
            ? `📊 Current Shop Load - Coach Family` 
            : `📊 Outturned Coaches - Coach Family (FY ${escapeHtml(fyVal)})`;
    }
    if (tDiv) {
        tDiv.innerHTML = isCurrentYear 
            ? `🏢 Current Shop Load - Division Share` 
            : `🏢 Outturned Coaches - Division Share (FY ${escapeHtml(fyVal)})`;
    }

    const filteredTargets = (_analyticsTargetData || []).filter(r => {
        if (familyFilter === 'ALL') return true;
        return r.family === familyFilter;
    });

    // 1. Render Target vs Achievement
    const ctxTarget = document.getElementById('chart-target-vs-achievement');
    if (ctxTarget && _analyticsTargetData) {
        if (window.myCharts['chart-target-vs-achievement']) {
            window.myCharts['chart-target-vs-achievement'].destroy();
        }

        const hasMonthly = filteredTargets.some(r => r.type === 'monthly');

        if (hasMonthly) {
            // Group targets and actuals by month name chronologically April to March
            const monthNames = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];
            const targetMap = {};
            const actualMap = {};
            monthNames.forEach(m => {
                targetMap[m] = 0;
                actualMap[m] = 0;
            });

            filteredTargets.forEach(r => {
                if (r.type === 'monthly') {
                    targetMap[r.month_name] = (targetMap[r.month_name] || 0) + r.target;
                    actualMap[r.month_name] = (actualMap[r.month_name] || 0) + r.actual;
                }
            });

            const targets = monthNames.map(m => targetMap[m]);
            const actuals = monthNames.map(m => actualMap[m]);

            window.myCharts['chart-target-vs-achievement'] = new Chart(ctxTarget, {
                type: 'line',
                data: {
                    labels: monthNames,
                    datasets: [
                        {
                            label: 'Target Outturn',
                            data: targets,
                            borderColor: colors.accent,
                            backgroundColor: 'transparent',
                            borderWidth: 2,
                            tension: 0.2,
                            pointRadius: 4
                        },
                        {
                            label: 'Actual Outturn',
                            data: actuals,
                            borderColor: colors.success,
                            backgroundColor: 'transparent',
                            borderWidth: 2,
                            tension: 0.2,
                            pointRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#9aa0b0' } }
                    },
                    scales: {
                        x: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' } },
                        y: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' }, beginAtZero: true }
                    }
                }
            });
        } else {
            // Prior Year - Group by Family
            const familyMap = {};
            filteredTargets.forEach(r => {
                if (r.type === 'yearly') {
                    if (!familyMap[r.family]) {
                        familyMap[r.family] = { target: 0, actual: 0 };
                    }
                    familyMap[r.family].target += r.target;
                    familyMap[r.family].actual += r.actual;
                }
            });

            const families = Object.keys(familyMap).sort();
            const targets = families.map(f => familyMap[f].target);
            const actuals = families.map(f => familyMap[f].actual);

            window.myCharts['chart-target-vs-achievement'] = new Chart(ctxTarget, {
                type: 'bar',
                data: {
                    labels: families,
                    datasets: [
                        {
                            label: 'Annual Target',
                            data: targets,
                            backgroundColor: colors.accent,
                            borderWidth: 0
                        },
                        {
                            label: 'Annual Achieved',
                            data: actuals,
                            backgroundColor: colors.success,
                            borderWidth: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#9aa0b0' } }
                    },
                    scales: {
                        x: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' } },
                        y: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' }, beginAtZero: true }
                    }
                }
            });
        }
    }

    // 2. Render Monthly Outturn Achievement (replacing Cycle Time chart)
    const ctxCycle = document.getElementById('chart-cycle-time');
    if (ctxCycle && _analyticsTargetData) {
        if (window.myCharts['chart-cycle-time']) {
            window.myCharts['chart-cycle-time'].destroy();
        }

        const monthNames = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];
        
        // Sum achieved outturns (actuals) by month from Google Sheets targets/achievements
        const monthlyAchieved = monthNames.map(m => {
            let sum = 0;
            filteredTargets.forEach(r => {
                if (r.type === 'monthly' && r.month_name === m) {
                    sum += r.actual;
                }
            });
            return sum;
        });

        window.myCharts['chart-cycle-time'] = new Chart(ctxCycle, {
            type: 'bar',
            data: {
                labels: monthNames,
                datasets: [{
                    label: 'Coaches Outturned',
                    data: monthlyAchieved,
                    backgroundColor: colors.info,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#9aa0b0' } }
                },
                scales: {
                    x: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' } },
                    y: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' }, beginAtZero: true }
                }
            }
        });
    }

    // 3. Render Shop Load / Outturn Coach Family Mix
    const ctxMix = document.getElementById('chart-coach-mix');
    const mixData = isCurrentYear ? _analyticsLiveData : _analyticsOutturnData;
    if (ctxMix && mixData) {
        if (window.myCharts['chart-coach-mix']) {
            window.myCharts['chart-coach-mix'].destroy();
        }

        const famCounts = {};
        mixData.forEach(c => {
            let fam = c.family || 'OTHER';
            if (fam === 'LHB') {
                fam = window.getCoachCategoryString(c);
            }
            famCounts[fam] = (famCounts[fam] || 0) + 1;
        });

        const labels = Object.keys(famCounts).sort();
        const data = labels.map(l => famCounts[l]);

        const chartColors = [
            colors.accent,
            colors.success,
            colors.info,
            colors.warning,
            colors.purple,
            colors.danger,
            '#e67e22',
            '#1abc9c',
            '#2c3e50',
            '#d35400',
            '#7f8c8d',
            '#16a085',
            '#27ae60',
            '#2980b9',
            '#8e44ad',
            colors.gray
        ];

        window.myCharts['chart-coach-mix'] = new Chart(ctxMix, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: chartColors.slice(0, labels.length),
                    borderWidth: 1,
                    borderColor: '#1e2130'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'right',
                        labels: { color: '#9aa0b0', boxWidth: 12 }
                    }
                }
            }
        });
    }

    // 4. Render Shop Load / Outturn Division Share
    const ctxDiv = document.getElementById('chart-division-share');
    const divData = isCurrentYear ? _analyticsLiveData : _analyticsOutturnData;
    if (ctxDiv && divData) {
        if (window.myCharts['chart-division-share']) {
            window.myCharts['chart-division-share'].destroy();
        }

        const divCounts = {};
        divData.forEach(c => {
            const div = c.division || 'OTHER';
            divCounts[div] = (divCounts[div] || 0) + 1;
        });

        const sortedDivs = Object.keys(divCounts).sort((a,b) => divCounts[b] - divCounts[a]);
        const data = sortedDivs.map(d => divCounts[d]);

        window.myCharts['chart-division-share'] = new Chart(ctxDiv, {
            type: 'bar',
            data: {
                labels: sortedDivs,
                datasets: [{
                    label: isCurrentYear ? 'Coaches Inside' : 'Coaches Outturned',
                    data: data,
                    backgroundColor: colors.purple,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' } },
                    y: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' }, beginAtZero: true }
                }
            }
        });
    }

    // 5. Render Cumulative Comparison (Cricket Worm Chart)
    const ctxCum = document.getElementById('chart-cumulative-comparison');
    if (ctxCum) {
        if (window.myCharts['chart-cumulative-comparison']) {
            window.myCharts['chart-cumulative-comparison'].destroy();
        }

        const startYear = parseInt(fyVal.split('-')[0]);
        const prevFyYear = String(startYear - 1) + '-' + String(startYear).slice(2);
        const monthNames = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];

        // Determine current month index to cap cumulative actual for current financial year
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;
        const currentFYStart = currentMonth >= 4 ? currentYear : currentYear - 1;
        
        let maxMonthIdx = 11;
        if (fyVal === `${currentFYStart}-${String(currentFYStart + 1).slice(2)}`) {
            maxMonthIdx = (currentMonth - 4 + 12) % 12;
        }

        function getFinMonthIndex(dateStr) {
            if (!dateStr) return -1;
            try {
                const parse = (s) => {
                    if (s.includes('-')) return new Date(s);
                    if (s.includes('/')) {
                        const parts = s.split('/');
                        let yr = parseInt(parts[2], 10);
                        if (yr < 100) yr += 2000;
                        return new Date(yr, parts[1] - 1, parts[0]);
                    }
                    return new Date(s);
                };
                const d = parse(dateStr);
                if (isNaN(d.getTime())) return -1;
                const month = d.getMonth() + 1;
                return (month - 4 + 12) % 12;
            } catch (e) {
                return -1;
            }
        }

        // Map actual outturn coach to target categories (LHB SS1 AC, ICF POH NAC, etc.)
        const getCoachCategoryString = window.getCoachCategoryString;

        // Selected Targets
        const selectedMonthlyTargets = new Array(12).fill(0);
        const hasMonthlyTargets = filteredTargets.some(r => r.type === 'monthly');

        if (hasMonthlyTargets) {
            filteredTargets.forEach(r => {
                if (r.type === 'monthly') {
                    const idx = monthNames.indexOf(r.month_name);
                    if (idx >= 0) {
                        selectedMonthlyTargets[idx] += r.target;
                    }
                }
            });
        } else {
            let totalAnnualTarget = 0;
            filteredTargets.forEach(r => {
                totalAnnualTarget += r.target;
            });
            const monthlyShare = Math.round(totalAnnualTarget / 12);
            for (let i = 0; i < 12; i++) {
                selectedMonthlyTargets[i] = monthlyShare;
            }
        }

        // Selected Year Actuals (sync from GSheet targets/achievements database)
        const selectedMonthlyActuals = new Array(12).fill(0);
        if (hasMonthlyTargets) {
            filteredTargets.forEach(r => {
                if (r.type === 'monthly') {
                    const idx = monthNames.indexOf(r.month_name);
                    if (idx >= 0) {
                        selectedMonthlyActuals[idx] += r.actual;
                    }
                }
            });
        }

        // Previous Year Actuals
        const prevMonthlyActuals = new Array(12).fill(0);
        const filteredPrevOutturns = (_analyticsPrevOutturnData || []).filter(c => {
            if (familyFilter === 'ALL') return true;
            return getCoachCategoryString(c) === familyFilter;
        });
        filteredPrevOutturns.forEach(c => {
            const idx = getFinMonthIndex(c.desp_date);
            if (idx >= 0 && idx < 12) {
                prevMonthlyActuals[idx]++;
            }
        });

        // Accumulate lists
        const selectedCumTargets = [];
        const selectedCumActuals = [];
        const prevCumActuals = [];

        let runningTarget = 0;
        let runningActual = 0;
        let runningPrevActual = 0;

        for (let i = 0; i < 12; i++) {
            runningTarget += selectedMonthlyTargets[i];
            selectedCumTargets.push(runningTarget);
            
            if (i <= maxMonthIdx) {
                runningActual += selectedMonthlyActuals[i];
                selectedCumActuals.push(runningActual);
            } else {
                selectedCumActuals.push(null);
            }
            
            runningPrevActual += prevMonthlyActuals[i];
            prevCumActuals.push(runningPrevActual);
        }

        // Render Chart.js
        window.myCharts['chart-cumulative-comparison'] = new Chart(ctxCum, {
            type: 'line',
            data: {
                labels: monthNames,
                datasets: [
                    {
                        label: `FY ${fyVal} Target (Cumulative)`,
                        data: selectedCumTargets,
                        borderColor: colors.accent,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        tension: 0.1,
                        pointRadius: 3
                    },
                    {
                        label: `FY ${fyVal} Actual (Cumulative)`,
                        data: selectedCumActuals,
                        borderColor: colors.success,
                        backgroundColor: 'transparent',
                        borderWidth: 3,
                        tension: 0.1,
                        pointRadius: 4,
                        spanGaps: false
                    },
                    {
                        label: `FY ${prevFyYear} Actual (Cumulative)`,
                        data: prevCumActuals,
                        borderColor: colors.purple,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.1,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#9aa0b0' } },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' } },
                    y: { grid: { color: '#2a2d3e' }, ticks: { color: '#9aa0b0' }, beginAtZero: true }
                }
            }
        });

        // Update Required / Average Rate Badge
        const badgeEl = document.getElementById('analytics-required-rate-badge');
        if (badgeEl) {
            if (familyFilter === 'ALL') {
                badgeEl.style.display = 'none';
            } else {
                badgeEl.style.display = '';
                if (fyVal === `${currentFYStart}-${String(currentFYStart + 1).slice(2)}`) {
                    const totalTarget = selectedCumTargets[11];
                    const totalActualYtd = runningActual;
                    const remainingMonths = 12 - (maxMonthIdx + 1);
                    
                    let reqRate = '0.0';
                    if (remainingMonths > 0 && totalTarget > totalActualYtd) {
                        reqRate = ((totalTarget - totalActualYtd) / remainingMonths).toFixed(1);
                    }
                    
                    // Calculate current month's actual daily outturn rate using working days from Google Sheet
                    const currentMonthActual = selectedMonthlyActuals[maxMonthIdx] || 0;
                    const currentMonthName = monthNames[maxMonthIdx];
                    let workingDays = 0;
                    if (_analyticsTargetData) {
                        let monthRec = _analyticsTargetData.find(r => r.type === 'monthly' && r.month_name === currentMonthName && r.family === familyFilter);
                        if (!monthRec) {
                            monthRec = _analyticsTargetData.find(r => r.type === 'monthly' && r.month_name === currentMonthName);
                        }
                        if (monthRec) {
                            workingDays = monthRec.working_days || 0;
                        }
                    }
                    
                    const now = new Date();
                    const currentDay = now.getDate();
                    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
                    
                    let elapsedWorkingDays = currentDay;
                    if (workingDays > 0) {
                        elapsedWorkingDays = Math.min(workingDays, Math.max(1, Math.round((currentDay / daysInMonth) * workingDays)));
                    }
                    
                    const divisor = elapsedWorkingDays;
                    const dailyRate = (currentMonthActual / divisor).toFixed(2);
                    const rateLabel = workingDays > 0 ? `coaches/working-day (${elapsedWorkingDays} elapsed of ${workingDays} working days)` : 'coaches/day';
                    
                    badgeEl.innerHTML = `🎯 Req. Rate: ${reqRate} coaches/mo | 📅 Daily Rate (Current Mo): ${dailyRate} ${rateLabel}`;
                } else {
                    let selectedTotalActual = 0;
                    for (let i = 0; i < 12; i++) {
                        selectedTotalActual += selectedMonthlyActuals[i];
                    }
                    const avgRate = (selectedTotalActual / 12).toFixed(1);
                    badgeEl.innerHTML = `📋 Average Rate: ${avgRate} coaches/month`;
                }
            }
        }

        // Populate Cumulative Comparison Table
        const tbody = document.querySelector('#cumulative-comparison-table tbody');
        if (tbody) {
            let tbodyHtml = '';
            for (let i = 0; i < 12; i++) {
                const targetVal = selectedCumTargets[i];
                const actualVal = i <= maxMonthIdx ? selectedCumActuals[i] : '—';
                const prevVal = prevCumActuals[i];
                
                tbodyHtml += `
                    <tr style="border-bottom:1px solid var(--border);">
                        <td style="padding:6px;color:var(--text-secondary);">${monthNames[i]}</td>
                        <td style="padding:6px;text-align:right;font-weight:500;">${targetVal}</td>
                        <td style="padding:6px;text-align:right;font-weight:600;">${actualVal}</td>
                        <td style="padding:6px;text-align:right;font-weight:500;">${prevVal}</td>
                    </tr>
                `;
            }
            tbody.innerHTML = tbodyHtml;
        }
    }
}
window.fetchAnalyticsData = fetchAnalyticsData;
window.renderAnalyticsCharts = renderAnalyticsCharts;

window.closeAnalyticsModal = function() {
    const modal = document.getElementById('analytics-coaches-modal');
    if (modal) modal.style.display = 'none';
};

window.showOutturnedCoachesList = async function(yearType, monthName, category, fyVal = null) {
    if (!fyVal) {
        const fyEl = document.getElementById('analytics-fy') || document.getElementById('pf-fy');
        if (fyEl) fyVal = fyEl.value;
    }
    if (!fyVal) fyVal = '2026-27';
    
    const startYear = parseInt(fyVal.split('-')[0]);
    
    const start_date = `${startYear}-04-01`;
    const end_date = `${startYear + 1}-03-31`;
    
    const prevStartYear = startYear - 1;
    const prev_start_date = `${prevStartYear}-04-01`;
    const prev_end_date = `${prevStartYear + 1}-03-31`;
    
    showLoading();
    
    try {
        let coachesList = [];
        if (yearType === 'prev') {
            const res = await api('outturn', { start_date: prev_start_date, end_date: prev_end_date });
            coachesList = res ? res.coaches : [];
        } else {
            const res = await api('outturn', { start_date: start_date, end_date: end_date });
            coachesList = res ? res.coaches : [];
        }
        
        const monthNames = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];
        const monthIdx = monthNames.indexOf(monthName);
        
        function getFinMonthIndex(dateStr) {
            if (!dateStr) return -1;
            try {
                const parse = (s) => {
                    if (s.includes('-')) return new Date(s);
                    if (s.includes('/')) {
                        const parts = s.split('/');
                        let yr = parseInt(parts[2], 10);
                        if (yr < 100) yr += 2000;
                        return new Date(yr, parts[1] - 1, parts[0]);
                    }
                    return new Date(s);
                };
                const d = parse(dateStr);
                if (isNaN(d.getTime())) return -1;
                const month = d.getMonth() + 1;
                return (month - 4 + 12) % 12;
            } catch (e) {
                return -1;
            }
        }
        
        const getCoachCategoryString = window.getCoachCategoryString;
        
        const filteredCoaches = coachesList.filter(c => {
            const mIdx = getFinMonthIndex(c.desp_date);
            if (mIdx < 0 || mIdx > monthIdx) return false; // YTD Cumulative
            if (category === 'ALL') return true;
            return getCoachCategoryString(c) === category;
        });
        
        const modal = document.getElementById('analytics-coaches-modal');
        const titleEl = document.getElementById('modal-title');
        const container = document.getElementById('modal-table-container');
        
        if (modal && titleEl && container) {
            const titleFy = (yearType === 'prev') ? `FY ${prevStartYear}-${String(prevStartYear + 1).slice(2)}` : `FY ${fyVal}`;
            titleEl.innerHTML = `📋 Cumulative YTD Outturned Coaches — ${escapeHtml(category)} (up to ${escapeHtml(monthName)} of ${escapeHtml(titleFy)})`;
            
            if (filteredCoaches.length === 0) {
                container.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-secondary);">No coaches found for this category and month.</div>`;
            } else {
                let tableHtml = `
                    <table class="summary-mini-table" style="width:100%;font-size:12px;border-collapse:collapse;">
                        <thead>
                            <tr style="border-bottom:1px solid var(--border);font-weight:600;color:var(--text-primary);text-align:left;">
                                <th style="padding:8px;">Coach No</th>
                                <th style="padding:8px;">Description</th>
                                <th style="padding:8px;">Repair Type</th>
                                <th style="padding:8px;">Division</th>
                                <th style="padding:8px;">Despatch Date</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                filteredCoaches.forEach(c => {
                    tableHtml += `
                        <tr style="border-bottom:1px solid var(--border);">
                            <td style="padding:8px;font-weight:600;"><a href="javascript:void(0)" onclick="closeAnalyticsModal(); window.navigateToSearch('${escapeHtml(c.coachno)}')" class="table-link">${escapeHtml(c.coachno)}</a></td>
                            <td style="padding:8px;color:var(--text-secondary);">${escapeHtml(c.coach_desc)}</td>
                            <td style="padding:8px;">${escapeHtml(c.repair_type)}</td>
                            <td style="padding:8px;">${escapeHtml(c.division)}</td>
                            <td style="padding:8px;color:var(--text-secondary);">${formatDate(c.desp_date)}</td>
                        </tr>
                    `;
                });
                
                tableHtml += `
                        </tbody>
                    </table>
                `;
                container.innerHTML = tableHtml;
            }
            modal.style.display = 'flex';
        }
    } catch (err) {
        console.error("Failed to load coaches for modal", err);
    } finally {
        hideLoading();
    }
};

/* ============================================================
   AC LOCO POSITION DASHBOARD
   ============================================================ */

let _acLocoData = null;

async function loadAcLoco() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">⚡ AC Loco Position</h1>
                <p class="page-subtitle">Real-time milestones tracking, shed assignments, and repair progress for locomotives in the workshop.</p>
            </div>

            <!-- Metrics grid -->
            <div class="metrics-grid" style="margin-bottom: 20px;">
                <div class="metric-card bg-info">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="loco-metric-total">—</div>
                    <div class="metric-label">Locomotives Inside</div>
                </div>
                <div class="metric-card bg-danger">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="loco-metric-dewheeled">—</div>
                    <div class="metric-label">Dewheeled</div>
                </div>
                <div class="metric-card bg-warning">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="loco-metric-wheeling">—</div>
                    <div class="metric-label">Wheeling Completed</div>
                </div>
                <div class="metric-card bg-success">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="loco-metric-trial">—</div>
                    <div class="metric-label">Ready / In Trial</div>
                </div>
            </div>

            <!-- Filters Bar -->
            <div class="card card-no-hover" style="padding:16px;margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;background:var(--bg-secondary);border:1px solid var(--border);">
                <div style="flex:1;min-width:200px;">
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Search Loco Number</label>
                    <input type="text" class="filter-input" id="loco-search" placeholder="Search number..." style="background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 12px;width:100%;" oninput="renderAcLocoGrid()">
                </div>
                <div>
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Home Shed</label>
                    <select class="filter-select" id="loco-filter-shed" style="width:140px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 10px;" onchange="renderAcLocoGrid()">
                        <option value="ALL" selected>All Sheds</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Milestone Status</label>
                    <select class="filter-select" id="loco-filter-status" style="width:180px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 10px;" onchange="renderAcLocoGrid()">
                        <option value="ALL" selected>All Stages</option>
                        <option value="recd_on">Received</option>
                        <option value="stripping">Stripping</option>
                        <option value="dewheel">Dewheeled</option>
                        <option value="wheeling">Wheeling Done</option>
                        <option value="test_trial">Test Trial</option>
                        <option value="traffic">Traffic Despatch</option>
                    </select>
                </div>
                <div style="align-self:flex-end;">
                    <button class="btn btn-secondary btn-sm" onclick="fetchAcLocoData()">🔄 Refresh</button>
                </div>
            </div>

            <!-- Locomotives Cards Grid -->
            <div class="loco-grid" id="loco-cards-grid"></div>
        </div>
    `;

    await fetchAcLocoData();
}
window.loadAcLoco = loadAcLoco;

async function fetchAcLocoData() {
    showLoading();
    try {
        const res = await api('acloco/position');
        _acLocoData = res ? res.coaches : [];
        
        // Populate Shed Dropdown Filter dynamically
        const shedSelect = document.getElementById('loco-filter-shed');
        if (shedSelect && _acLocoData) {
            const sheds = [...new Set(_acLocoData.map(l => l.shed).filter(Boolean))].sort();
            
            // Clear but keep ALL option
            shedSelect.innerHTML = '<option value="ALL" selected>All Sheds</option>';
            sheds.forEach(s => {
                shedSelect.innerHTML += `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`;
            });
        }

        renderAcLocoGrid();
    } catch (e) {
        console.error('Failed to fetch AC Loco position data', e);
        const grid = document.getElementById('loco-cards-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="card card-no-hover" style="grid-column:1/-1;text-align:center;padding:48px;">
                    <div style="font-size:32px;color:var(--danger);margin-bottom:12px;">⚠️</div>
                    <div style="color:var(--text-primary);font-weight:600;">Failed to load AC locomotive position data</div>
                    <div style="color:var(--text-muted);font-size:13px;margin-top:8px;">${escapeHtml(e.message)}</div>
                </div>
            `;
        }
    } finally {
        hideLoading();
    }
}
window.fetchAcLocoData = fetchAcLocoData;

function renderAcLocoGrid() {
    const grid = document.getElementById('loco-cards-grid');
    if (!grid || !_acLocoData) return;

    const searchVal = document.getElementById('loco-search').value.toLowerCase().trim();
    const shedFilter = document.getElementById('loco-filter-shed').value;
    const stageFilter = document.getElementById('loco-filter-status').value;

    // Filter Locos
    const filtered = _acLocoData.filter(l => {
        const matchesSearch = !searchVal || l.loco_no.toLowerCase().includes(searchVal) || (l.loco_desc || '').toLowerCase().includes(searchVal);
        const matchesShed = shedFilter === 'ALL' || l.shed === shedFilter;
        
        let matchesStage = true;
        if (stageFilter !== 'ALL') {
            matchesStage = !!l[stageFilter] && l[stageFilter] !== '—' && l[stageFilter] !== '';
        }
        
        return matchesSearch && matchesShed && matchesStage;
    });

    // Compute metrics
    let total = _acLocoData.length;
    let dewheeled = _acLocoData.filter(l => l.dewheel && l.dewheel !== '—' && l.dewheel !== '').length;
    let wheeling = _acLocoData.filter(l => l.wheeling && l.wheeling !== '—' && l.wheeling !== '').length;
    let trial = _acLocoData.filter(l => l.test_trial && l.test_trial !== '—' && l.test_trial !== '').length;

    document.getElementById('loco-metric-total').textContent = total;
    document.getElementById('loco-metric-dewheeled').textContent = dewheeled;
    document.getElementById('loco-metric-wheeling').textContent = wheeling;
    document.getElementById('loco-metric-trial').textContent = trial;

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="card card-no-hover" style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-secondary);">
                🔍 No locomotives match your filters.
            </div>
        `;
        return;
    }

    // List of chronological milestones to track
    const milestonesList = [
        { key: 'recd_on', label: 'Arrived' },
        { key: 'stripping', label: 'Stripping' },
        { key: 'dewheel', label: 'Dewheeled' },
        { key: 'wheeling', label: 'Wheeling' },
        { key: 'test_trial', label: 'Test Trial' },
        { key: 'traffic', label: 'Ready / Desp' }
    ];

    let cardsHtml = '';
    filtered.forEach(l => {
        // Find current step index
        let currentStepIdx = -1;
        for (let i = milestonesList.length - 1; i >= 0; i--) {
            const mKey = milestonesList[i].key;
            if (l[mKey] && l[mKey] !== '—' && l[mKey] !== '') {
                currentStepIdx = i;
                break;
            }
        }

        // Days inside calculation
        let daysInside = '—';
        if (l.date_recd || l.recd_on) {
            const recd = l.date_recd || l.recd_on;
            const parse = (s) => {
                if (s.includes('-')) return new Date(s);
                if (s.includes('/')) {
                    const parts = s.split('/');
                    const year = parts[2].length === 2 ? '20' + parts[2] : parts[2];
                    return new Date(year, parts[1] - 1, parts[0]);
                }
                return new Date(s);
            };
            try {
                const recdDt = parse(recd);
                const today = new Date();
                const diffTime = Math.abs(today - recdDt);
                daysInside = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + ' Days';
            } catch (err) {
                daysInside = '—';
            }
        }

        let milestoneRowsHtml = '';
        milestonesList.forEach((m, idx) => {
            const isCompleted = idx <= currentStepIdx;
            const isCurrent = idx === currentStepIdx + 1 && idx < milestonesList.length; // Next pending is active
            
            let dotClass = '';
            let labelClass = '';
            let dateClass = '';
            
            if (isCompleted) {
                dotClass = 'completed';
                labelClass = 'completed';
                dateClass = 'completed';
            } else if (isCurrent) {
                dotClass = 'current';
                labelClass = 'current';
                dateClass = 'current';
            }

            const mDate = l[m.key] || '';
            const dateStr = (isCompleted && mDate && mDate !== '—') ? mDate : (isCurrent ? 'In Progress' : 'Pending');

            milestoneRowsHtml += `
                <div class="loco-milestone-row">
                    <div class="loco-milestone-dot ${dotClass}"></div>
                    <div class="loco-milestone-info">
                        <div class="loco-milestone-label ${labelClass}">${escapeHtml(m.label)}</div>
                        <div class="loco-milestone-date ${dateClass}">${escapeHtml(dateStr)}</div>
                    </div>
                </div>
            `;
        });

        const locationLabel = l.pitnum ? `Pit ${l.pitnum.replace('ACB/', 'AC/').replace('AC/', '')}` : 'Yard / Off Pit';
        const locationColor = l.pitnum ? 'var(--accent)' : 'var(--text-muted)';
        
        cardsHtml += `
            <div class="loco-card">
                <div class="loco-card-header">
                    <div class="loco-card-title-block">
                        <div class="loco-card-number">${escapeHtml(l.loco_no)}</div>
                        <div class="loco-card-type">${escapeHtml(l.loco_desc || 'WAP7')}</div>
                    </div>
                    <div style="font-size:12px;font-weight:700;color:${locationColor};background:var(--bg-secondary);padding:3px 8px;border-radius:20px;border:1px solid var(--border);">
                        📍 ${escapeHtml(locationLabel)}
                    </div>
                </div>

                <div class="loco-card-body">
                    <div class="loco-meta-grid">
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">Home Shed</span>
                            <span class="loco-meta-value">${escapeHtml(l.shed || '—')}</span>
                        </div>
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">Days Inside</span>
                            <span class="loco-meta-value" style="color:var(--warning);">${escapeHtml(daysInside)}</span>
                        </div>
                        <div class="loco-meta-item" style="grid-column:1/-1;border-top:1px solid var(--border);padding-top:6px;margin-top:4px;display:flex;flex-direction:row;justify-content:space-between;align-items:center;">
                            <span class="loco-meta-label">PDC Target</span>
                            <span class="loco-meta-value" style="color:var(--danger);">${escapeHtml(l.pdc || 'Not Assigned')}</span>
                        </div>
                    </div>

                    <div style="font-weight:600;font-size:12px;color:var(--text-secondary);margin-top:6px;">📈 Repair Milestones Tracker</div>
                    <div class="loco-milestones-container">
                        ${milestoneRowsHtml}
                    </div>
                </div>
            </div>
        `;
    });

    grid.innerHTML = cardsHtml;
}
window.renderAcLocoGrid = renderAcLocoGrid;
window.fetchAcLocoData = fetchAcLocoData;


/* ============================================================
   COACH PROGRESS TRACKER VIEW
   ============================================================ */

let _coachesProgressData = null;
let _activeProgressTab = 'LHB';

async function loadCoachProgress() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">🔄 Coach Progress Tracker</h1>
                <p class="page-subtitle">Real-time milestones, stage tracking, and physical positions for coaches currently under repair.</p>
            </div>

            <!-- Tabs Navigation -->
            <div class="tabs-nav-container progress-tabs" style="margin-bottom: 20px;">
                <button class="tab-nav-btn active" data-tab="LHB" onclick="window.switchProgressTab('LHB')">LHB Progress</button>
                <button class="tab-nav-btn" data-tab="ICF NAC" onclick="window.switchProgressTab('ICF NAC')">ICF NAC Progress</button>
                <button class="tab-nav-btn" data-tab="MEMU/EMU TC" onclick="window.switchProgressTab('MEMU/EMU TC')">MEMU/EMU TC Progress</button>
            </div>

            <!-- Metrics grid -->
            <div class="metrics-grid" style="margin-bottom: 20px;">
                <div class="metric-card bg-info">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="progress-metric-total">—</div>
                    <div class="metric-label">Total Under Progress</div>
                </div>
                <div class="metric-card bg-danger">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="progress-metric-corrosion">—</div>
                    <div class="metric-label">In Corrosion Shop</div>
                </div>
                <div class="metric-card bg-warning">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="progress-metric-lowering">—</div>
                    <div class="metric-label">In Lowering Shop</div>
                </div>
                <div class="metric-card bg-success">
                    <div class="metric-accent"></div>
                    <div class="metric-value" id="progress-metric-furnishing">—</div>
                    <div class="metric-label">In Furnishing Shop</div>
                </div>
            </div>

            <!-- Filters Bar -->
            <div class="card card-no-hover" style="padding:16px;margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;background:var(--bg-secondary);border:1px solid var(--border);">
                <div style="flex:1;min-width:200px;">
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Search Coach</label>
                    <input type="text" class="filter-input" id="progress-search" placeholder="Search number, description, remarks..." style="background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 12px;width:100%;" oninput="renderProgressGrid()">
                </div>
                <div>
                    <label style="font-weight:600;font-size:12px;margin-bottom:6px;display:block;color:var(--text-secondary);">Active Stage</label>
                    <select class="filter-select" id="progress-filter-stage" style="width:200px;background:var(--bg-card);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;padding:6px 10px;" onchange="renderProgressGrid()">
                        <option value="ALL">All Stages</option>
                        <option value="Corrosion">Corrosion Shop</option>
                        <option value="Bio Tank Loading">Bio Tank Loading</option>
                        <option value="Lowering">Lowering Shop</option>
                        <option value="Furnishing">Furnishing Shop</option>
                        <option value="Despatch">Despatch Shop</option>
                    </select>
                </div>
                <div style="align-self:flex-end;margin-left:auto;">
                    <button class="btn btn-secondary btn-sm" onclick="fetchProgressData()">🔄 Refresh Data</button>
                </div>
            </div>

            <!-- Grid of Cards -->
            <div class="loco-grid" id="progress-cards-grid">
                <div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-secondary);">
                    Loading progress data...
                </div>
            </div>
        </div>
    `;

    await fetchProgressData();
    hideLoading();
}
window.loadCoachProgress = loadCoachProgress;

async function fetchProgressData() {
    try {
        const data = await api('coaches/progress');
        _coachesProgressData = data;
        renderProgressGrid();
    } catch (err) {
        console.error('Failed to fetch progress data', err);
        const grid = document.getElementById('progress-cards-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="card card-no-hover" style="grid-column:1/-1;text-align:center;padding:48px;color:var(--danger);">
                    ⚠️ Failed to load progress tracker data: ${escapeHtml(err.message)}
                </div>
            `;
        }
    }
}
window.fetchProgressData = fetchProgressData;

window.switchProgressTab = function(tabId) {
    _activeProgressTab = tabId;
    document.querySelectorAll('.progress-tabs .tab-nav-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    renderProgressGrid();
};

function renderProgressGrid() {
    const grid = document.getElementById('progress-cards-grid');
    if (!grid || !_coachesProgressData) return;

    const searchVal = document.getElementById('progress-search').value.toLowerCase().trim();
    const stageFilter = document.getElementById('progress-filter-stage').value;

    // Filter coaches by active tab (source_tab)
    const tabCoaches = _coachesProgressData.filter(c => c.source_tab === _activeProgressTab);

    // Apply search and stage filters
    const filtered = tabCoaches.filter(c => {
        const matchesSearch = !searchVal || 
            c.coachno.toLowerCase().includes(searchVal) || 
            (c.coach_desc || '').toLowerCase().includes(searchVal) || 
            (c.remarks || '').toLowerCase().includes(searchVal);
            
        let matchesStage = true;
        if (stageFilter !== 'ALL') {
            const activeStage = c.stages.find(s => s.status === 'IN_PROGRESS');
            if (activeStage) {
                matchesStage = activeStage.name === stageFilter;
            } else {
                matchesStage = false;
            }
        }
        
        return matchesSearch && matchesStage;
    });

    // Compute tab-specific metrics
    const total = tabCoaches.length;
    const inCorrosion = tabCoaches.filter(c => c.stages[1] && c.stages[1].status === 'IN_PROGRESS').length;
    const inLowering = tabCoaches.filter(c => c.stages[3] && c.stages[3].status === 'IN_PROGRESS').length;
    const inFurnishing = tabCoaches.filter(c => c.stages[4] && c.stages[4].status === 'IN_PROGRESS').length;

    const totalEl = document.getElementById('progress-metric-total');
    const corrEl = document.getElementById('progress-metric-corrosion');
    const lowEl = document.getElementById('progress-metric-lowering');
    const furnEl = document.getElementById('progress-metric-furnishing');

    if (totalEl) totalEl.textContent = total;
    if (corrEl) corrEl.textContent = inCorrosion;
    if (lowEl) lowEl.textContent = inLowering;
    if (furnEl) furnEl.textContent = inFurnishing;

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="card card-no-hover" style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-secondary);">
                🔍 No coaches under progress match your filters.
            </div>
        `;
        return;
    }

    let cardsHtml = '';
    filtered.forEach(c => {
        let milestoneRowsHtml = '';
        
        c.stages.forEach((s, idx) => {
            let dotClass = '';
            let labelClass = '';
            let dateClass = '';
            
            if (s.status === 'COMPLETED') {
                dotClass = 'completed';
                labelClass = 'completed';
                dateClass = 'completed';
            } else if (s.status === 'IN_PROGRESS') {
                dotClass = 'current';
                labelClass = 'current';
                dateClass = 'current';
            }
            
            let dateStr = 'Pending';
            if (s.status === 'COMPLETED') {
                if (s.date) {
                    dateStr = formatDate(s.date);
                } else if (s.detail && s.detail !== 'Under progress' && s.detail !== 'Yet to be taken') {
                    dateStr = s.detail;
                } else {
                    dateStr = 'Completed';
                }
            } else if (s.status === 'IN_PROGRESS') {
                dateStr = s.detail ? s.detail : 'In Progress';
            }
            
            milestoneRowsHtml += `
                <div class="loco-milestone-row">
                    <div class="loco-milestone-dot ${dotClass}"></div>
                    <div class="loco-milestone-info">
                        <div class="loco-milestone-label ${labelClass}">${escapeHtml(s.name)}</div>
                        <div class="loco-milestone-date ${dateClass}">${escapeHtml(dateStr)}</div>
                    </div>
                </div>
            `;
        });

        const locationLabel = c.pitnum ? `Pit ${escapeHtml(c.pitnum)}` : 'Yard / Off Pit';
        const locationColor = c.pitnum ? 'var(--accent)' : 'var(--text-muted)';
        const daysInsideText = c.in_days !== null ? `${c.in_days} Days` : '—';
        
        cardsHtml += `
            <div class="loco-card">
                <div class="loco-card-header">
                    <div class="loco-card-title-block">
                        <div class="loco-card-number">
                            <a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(c.coachno)}')" class="table-link">${escapeHtml(c.coachno)}</a>
                        </div>
                        <div class="loco-card-type">${escapeHtml(c.coach_desc || c.family || 'Coach')}</div>
                    </div>
                    <div style="font-size:12px;font-weight:700;color:${locationColor};background:var(--bg-secondary);padding:3px 8px;border-radius:20px;border:1px solid var(--border);">
                        📍 ${escapeHtml(locationLabel)}
                    </div>
                </div>

                <div class="loco-card-body">
                    <div class="loco-meta-grid">
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">Family</span>
                            <span class="loco-meta-value">${escapeHtml(c.family || '—')}</span>
                        </div>
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">Repair Type</span>
                            <span class="loco-meta-value">${escapeHtml(c.repair_type || '—')}</span>
                        </div>
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">Days Inside</span>
                            <span class="loco-meta-value" style="color:var(--warning);">${escapeHtml(daysInsideText)}</span>
                        </div>
                        <div class="loco-meta-item">
                            <span class="loco-meta-label">PDC Target</span>
                            <span class="loco-meta-value" style="color:var(--danger);">${escapeHtml(c.pdc || 'Not Assigned')}</span>
                        </div>
                        <div class="loco-meta-item" style="grid-column:1/-1;border-top:1px solid var(--border);padding-top:6px;margin-top:4px;">
                            <span class="loco-meta-label">Remarks</span>
                            <span class="loco-meta-value" style="font-size:11px;color:var(--text-secondary);word-break:break-word;">${escapeHtml(c.remarks || '—')}</span>
                        </div>
                    </div>

                    <div style="font-weight:600;font-size:12px;color:var(--text-secondary);margin-top:8px;">📈 Stage Progress Tracker</div>
                    <div class="loco-milestones-container">
                        ${milestoneRowsHtml}
                    </div>
                </div>
            </div>
        `;
    });

    grid.innerHTML = cardsHtml;
}
window.renderProgressGrid = renderProgressGrid;


/* ============================================================
   AUDIT & ANALYSIS MODULE
   ============================================================ */

let _auditData = null;
let _activeAuditTab = 'fnd';

const AUDIT_SUBTYPES = {
    ICF: ["CN", "GS", "CZ", "SLR", "CZJ", "GSLRD", "GSRD", "CZRJ", "WCB", "VPH"],
    LHB: ["LWSCN", "LWACCN", "LWS", "LWSCZ", "LWACCW", "LS5", "LS", "LWSCNA", "LWFCWAC", "LWCBAC", "LSLRD", "LSCN", "LVPH"],
    DEMU: ["TC", "DPC", "DTC", "DTCS"],
    NMG: ["NMG", "NMGHS", "NMGH", "NMGHS_Conv", "NMGHSR"],
    MEMU: ["MEMUTC", "MEMUMC"],
    EMU: ["YSY", "YSD", "YFSY", "YZZS", "DMSC"],
    VB: ["TSMC", "TSMC2", "TSTC", "TSDTC", "TSNDTC", "TSNDTC2"],
    SPECIAL: ["ART", "ARMV", "SPART", "SPIC", "ARTConv", "VPH", "VPU"],
    LOCO: ["WAP4", "WAP7", "WAG7"]
};

function populateAuditCoachTypes() {
    const familyEl = document.getElementById('audit-family');
    const typeEl = document.getElementById('audit-type');
    if (!familyEl || !typeEl) return;
    
    const selectedFamily = familyEl.value;
    const subtypes = AUDIT_SUBTYPES[selectedFamily] || [];
    
    typeEl.innerHTML = `
        <option value="ALL">All Types</option>
        ${subtypes.map(t => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join('')}
    `;
}
window.populateAuditCoachTypes = populateAuditCoachTypes;

function onAuditFamilyChange() {
    populateAuditCoachTypes();
    fetchAuditData();
}
window.onAuditFamilyChange = onAuditFamilyChange;

async function loadAuditModule() {
    const container = document.getElementById('main-content');
    if (!container) return;

    showLoading();

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth(); 
    const currentFYYear = currentMonth >= 3 ? currentYear : currentYear - 1;

    // Generate recent 8 FYs
    const fys = [];
    for (let i = 0; i < 8; i++) {
        const y = currentFYYear - i;
        const fyStr = `${y}-${String(y + 1).slice(2)}`;
        fys.push(fyStr);
    }

    container.innerHTML = `
        <div class="anim-slide">
            <div class="page-header">
                <h1 class="page-title">📊 Audit & Analysis</h1>
                <p class="page-subtitle">Rank previous workshops and divisions by corrosion severity, audit missing corrosion hours, and manage First Despatch (FND) updates.</p>
            </div>

            <div class="live-layout" style="margin-top:20px;">
                <!-- Sidebar Filters -->
                <div class="live-sidebar">
                    <div class="card card-no-hover">
                        <div class="card-title">🎛️ Audit Filters</div>
                        <div style="display:flex;flex-direction:column;gap:12px;">
                            <div class="filter-group">
                                <label class="filter-label">Financial Year</label>
                                <select class="filter-select" id="audit-fy" style="width:100%" onchange="fetchAuditData()">
                                    <option value="ALL">All Years</option>
                                    ${fys.map(fy => `<option value="${fy}">${fy}</option>`).join('')}
                                </select>
                            </div>
                            <div class="filter-group">
                                <label class="filter-label">Coach Family</label>
                                <select class="filter-select" id="audit-family" style="width:100%" onchange="onAuditFamilyChange()">
                                    <option value="ALL">All Families</option>
                                    <option value="LHB">LHB</option>
                                    <option value="ICF">ICF</option>
                                    <option value="DEMU">DEMU</option>
                                    <option value="MEMU">MEMU</option>
                                    <option value="EMU">EMU</option>
                                    <option value="NMG">NMG</option>
                                    <option value="SPECIAL">SPECIAL</option>
                                    <option value="LOCO">LOCO</option>
                                </select>
                            </div>
                            <div class="filter-group">
                                <label class="filter-label">Coach Type</label>
                                <select class="filter-select" id="audit-type" style="width:100%" onchange="fetchAuditData()">
                                    <option value="ALL">All Types</option>
                                </select>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick="fetchAuditData()">Refresh Data</button>
                        </div>
                    </div>
                </div>

                <!-- Main Content Area -->
                <div style="flex:1;min-width:0;">
                    <!-- Navigation Tabs -->
                    <div class="tabs-nav-container" style="margin-bottom: 20px;">
                        <button class="tab-nav-btn active" id="audit-tab-btn-fnd" onclick="switchAuditTab('fnd')">📋 FND (Pending VG & Physical Despatch)</button>
                        <button class="tab-nav-btn" id="audit-tab-btn-rankings" onclick="switchAuditTab('rankings')">🏢 Workshop & Division Rankings</button>
                        <button class="tab-nav-btn" id="audit-tab-btn-missing" onclick="switchAuditTab('missing')">⚠️ Coaches Without Hours</button>
                        <button class="tab-nav-btn" id="audit-tab-btn-condemned" onclick="switchAuditTab('condemned')">🗑️ Condemned & Returned</button>
                    </div>

                    <!-- Tab Contents -->
                    <div id="audit-tab-fnd" class="audit-tab-content"></div>
                    <div id="audit-tab-rankings" class="audit-tab-content" style="display:none;"></div>
                    <div id="audit-tab-missing" class="audit-tab-content" style="display:none;"></div>
                    <div id="audit-tab-condemned" class="audit-tab-content" style="display:none;"></div>
                </div>
            </div>
        </div>
    `;

    populateAuditCoachTypes();

    await fetchAuditData();
    hideLoading();
}
window.loadAuditModule = loadAuditModule;

async function fetchAuditData() {
    const fy = document.getElementById('audit-fy').value || 'ALL';
    const family = document.getElementById('audit-family').value || 'ALL';
    const type = document.getElementById('audit-type').value || 'ALL';

    try {
        const res = await api('audit/data', { fy: fy, family: family, type: type });
        _auditData = res;
        renderActiveAuditTab();
    } catch (e) {
        console.error('Error fetching audit data:', e);
        const activeTab = document.getElementById('audit-tab-' + _activeAuditTab);
        if (activeTab) {
            activeTab.innerHTML = `<div class="card card-no-hover" style="color:var(--danger); padding:20px;">Error loading audit data: ${escapeHtml(e.message)}</div>`;
        }
    }
}
window.fetchAuditData = fetchAuditData;

function switchAuditTab(tab) {
    _activeAuditTab = tab;
    
    // Toggle active buttons
    document.querySelectorAll('.tabs-nav-container .tab-nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.getElementById('audit-tab-btn-' + tab);
    if (activeBtn) activeBtn.classList.add('active');
    
    // Toggle active views
    document.getElementById('audit-tab-fnd').style.display = tab === 'fnd' ? 'block' : 'none';
    document.getElementById('audit-tab-rankings').style.display = tab === 'rankings' ? 'block' : 'none';
    document.getElementById('audit-tab-missing').style.display = tab === 'missing' ? 'block' : 'none';
    document.getElementById('audit-tab-condemned').style.display = tab === 'condemned' ? 'block' : 'none';
    
    renderActiveAuditTab();
}
window.switchAuditTab = switchAuditTab;

function toggleAllFndCheckboxes(checked) {
    document.querySelectorAll('.fnd-checkbox:not(:disabled)').forEach(cb => {
        cb.checked = checked;
    });
}
window.toggleAllFndCheckboxes = toggleAllFndCheckboxes;

async function submitBatchDespatch() {
    const checkedBoxes = document.querySelectorAll('.fnd-checkbox:checked');
    if (checkedBoxes.length === 0) {
        alert('Please select at least one coach.');
        return;
    }
    
    const coachnos = Array.from(checkedBoxes).map(cb => cb.value);
    const dateInput = document.getElementById('batch-desp-date').value.trim();
    
    // Verify date format if entered
    if (dateInput) {
        const datePattern = /^\d{2}\/\d{2}\/\d{4}$/;
        if (!datePattern.test(dateInput)) {
            alert('Please enter date in DD/MM/YYYY format.');
            return;
        }
    }
    
    if (!confirm(`Are you sure you want to mark ${coachnos.length} coach(es) as VG Cleared & Physically Despatched?`)) {
        return;
    }
    
    showLoading();
    try {
        const response = await fetch('/api/audit/batch-despatch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ coachnos: coachnos, date: dateInput })
        });
        const res = await response.json();
        if (res.error) {
            alert('Batch update failed: ' + res.error);
        } else {
            alert(`Successfully updated ${res.updated_count} coach(es) in Supabase!`);
            // Refresh data
            await fetchAuditData();
        }
    } catch (e) {
        console.error(e);
        alert('Error submitting batch update.');
    } finally {
        hideLoading();
    }
}
window.submitBatchDespatch = submitBatchDespatch;

function renderActiveAuditTab() {
    if (!_auditData) return;
    
    if (_activeAuditTab === 'fnd') {
        const container = document.getElementById('audit-tab-fnd');
        const list = _auditData.fnd || [];
        
        if (list.length === 0) {
            container.innerHTML = `
                <div class="card card-no-hover" style="text-align: center; padding: 40px;">
                    <div style="font-size: 40px; margin-bottom: 12px;">🎉</div>
                    <h3 style="color: var(--text-primary);">All Cleared!</h3>
                    <p style="color: var(--text-secondary);">No coaches are currently pending VG clearance or physical despatch.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card card-no-hover" style="margin-bottom: 20px;">
                <div class="card-title">⚡ Batch VG Clearance & Physical Despatch</div>
                <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 13px;">
                    Select coaches below to mark them as <strong>VG Cleared</strong> and <strong>Physically Despatched</strong>. This will update Supabase and remove them from the active workshop view.
                </p>
                <div style="display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap;">
                    <div class="filter-group" style="margin-bottom: 0;">
                        <label class="filter-label">Despatch Date (DD/MM/YYYY)</label>
                        <input type="text" id="batch-desp-date" class="search-input" placeholder="e.g. 13/06/2026 (blank for today)" style="width: 260px;">
                    </div>
                    <button class="btn btn-primary" onclick="submitBatchDespatch()">Mark Selected as Completed</button>
                </div>
            </div>

            <div class="card card-no-hover">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                    <div class="card-title" style="margin-bottom: 0;">📋 Pending Coaches (${list.length})</div>
                    <div>
                        <button class="btn btn-secondary btn-sm" style="margin-right: 5px;" onclick="toggleAllFndCheckboxes(true)">Select All</button>
                        <button class="btn btn-secondary btn-sm" onclick="toggleAllFndCheckboxes(false)">Deselect All</button>
                    </div>
                </div>
                
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 50px; text-align: center;">Select</th>
                                <th>Coach No</th>
                                <th>Description</th>
                                <th>Family</th>
                                <th>Location</th>
                                <th>Recd Date</th>
                                <th>Paper Outturn</th>
                                <th>VG Status</th>
                                <th>Physical Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${list.map(c => {
                                const vgBadge = c.vg_status === 'Completed' 
                                    ? '<span class="badge badge-success">Completed</span>' 
                                    : '<span class="badge badge-danger">Pending</span>';
                                const physBadge = c.physical_status === 'Despatched'
                                    ? '<span class="badge badge-success">Despatched</span>'
                                    : '<span class="badge badge-danger">Pending</span>';
                                    
                                // Dynamic current month detection
                                const now = new Date();
                                const currentMonthStr = '/' + String(now.getMonth() + 1).padStart(2, '0') + '/' + now.getFullYear();
                                const currentMonthStrShort = '/' + String(now.getMonth() + 1).padStart(2, '0') + '/' + String(now.getFullYear()).slice(-2);
                                const currentMonthIso = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');
                                
                                const isCurrentMonth = 
                                    (c.desp_date && (c.desp_date.includes(currentMonthStr) || c.desp_date.includes(currentMonthStrShort) || c.desp_date.includes(currentMonthIso))) ||
                                    (c.recd_date && (c.recd_date.includes(currentMonthStr) || c.recd_date.includes(currentMonthStrShort) || c.recd_date.includes(currentMonthIso)));
                                    
                                const checkboxHtml = isCurrentMonth 
                                    ? `<input type="checkbox" class="fnd-checkbox" disabled title="Current month outturns must be updated manually" value="${escapeHtml(c.coachno)}">`
                                    : `<input type="checkbox" class="fnd-checkbox" value="${escapeHtml(c.coachno)}">`;
                                    
                                const coachNoLabel = isCurrentMonth
                                    ? `${escapeHtml(c.coachno)} <span class="badge badge-warning" style="font-size: 10px; margin-left: 5px; vertical-align: middle;">Manual Only</span>`
                                    : escapeHtml(c.coachno);
                                    
                                return `
                                    <tr>
                                        <td style="text-align: center; vertical-align: middle;">
                                            ${checkboxHtml}
                                        </td>
                                        <td style="font-weight: 600; color: var(--accent);">${coachNoLabel}</td>
                                        <td>${escapeHtml(c.coach_desc)}</td>
                                        <td><span class="badge badge-info">${escapeHtml(c.family)}</span></td>
                                        <td><span style="font-family: var(--font-mono); font-size: 12px;">${escapeHtml(c.pitnum || '—')}</span></td>
                                        <td>${escapeHtml(c.recd_date || '—')}</td>
                                        <td>${escapeHtml(c.desp_date || '—')}</td>
                                        <td>${vgBadge}</td>
                                        <td>${physBadge}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } 
    else if (_activeAuditTab === 'rankings') {
        const container = document.getElementById('audit-tab-rankings');
        const wRankings = _auditData.workshop_rankings || [];
        const dRankings = _auditData.division_rankings || [];
        
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px;">
                <!-- Workshop Rankings -->
                <div class="card card-no-hover">
                    <div class="card-title">🏢 Previous Workshop Rankings</div>
                    <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 13px;">
                        Workshops ranked by average corrosion hours of received coaches (highest first).
                    </p>
                    <div style="overflow-x: auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Workshop</th>
                                    <th>Received</th>
                                    <th>With Hours</th>
                                    <th>Avg Hours</th>
                                    <th>Max Hours</th>
                                    <th>Heavy %</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${wRankings.map((w, i) => `
                                    <tr>
                                        <td><strong>${i + 1}</strong></td>
                                        <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(w.workshop)}</td>
                                        <td>${w.total_received}</td>
                                        <td>${w.coaches_with_hours}</td>
                                        <td style="font-weight: 600; color: ${w.avg_hours > 500 ? 'var(--danger)' : 'var(--accent)'};">${w.avg_hours}</td>
                                        <td>${w.max_hours}</td>
                                        <td><span class="badge ${w.heavy_pct > 30 ? 'badge-danger' : 'badge-info'}">${w.heavy_pct}%</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Division Rankings -->
                <div class="card card-no-hover">
                    <div class="card-title">🗺️ Division Rankings</div>
                    <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 13px;">
                        Divisions ranked by average corrosion hours of received coaches (highest first).
                    </p>
                    <div style="overflow-x: auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Division</th>
                                    <th>Received</th>
                                    <th>With Hours</th>
                                    <th>Avg Hours</th>
                                    <th>Max Hours</th>
                                    <th>Heavy %</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${dRankings.map((d, i) => `
                                    <tr>
                                        <td><strong>${i + 1}</strong></td>
                                        <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(d.division)}</td>
                                        <td>${d.total_received}</td>
                                        <td>${d.coaches_with_hours}</td>
                                        <td style="font-weight: 600; color: ${d.avg_hours > 500 ? 'var(--danger)' : 'var(--accent)'};">${d.avg_hours}</td>
                                        <td>${d.max_hours}</td>
                                        <td><span class="badge ${d.heavy_pct > 30 ? 'badge-danger' : 'badge-info'}">${d.heavy_pct}%</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    else if (_activeAuditTab === 'missing') {
        const container = document.getElementById('audit-tab-missing');
        const list = _auditData.missing_hours || [];
        
        if (list.length === 0) {
            container.innerHTML = `
                <div class="card card-no-hover" style="text-align: center; padding: 40px;">
                    <div style="font-size: 40px; margin-bottom: 12px;">🎉</div>
                    <h3 style="color: var(--text-primary);">All Filled!</h3>
                    <p style="color: var(--text-secondary);">Every active coach inside the workshop has corrosion hours filled.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card card-no-hover">
                <div class="card-title">⚠️ Active Coaches Missing Corrosion Hours (${list.length})</div>
                <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 13px;">
                    Coaches currently inside the workshop that do not have corrosion hours (Pre-survey and Final hours are empty or 0).
                </p>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Coach No</th>
                                <th>Description</th>
                                <th>Family</th>
                                <th>Division</th>
                                <th>Recd Date</th>
                                <th>Status</th>
                                <th>Pit Location</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${list.map(c => `
                                <tr>
                                    <td style="font-weight: 600; color: var(--accent);">${escapeHtml(c.coachno)}</td>
                                    <td>${escapeHtml(c.coach_desc)}</td>
                                    <td><span class="badge badge-info">${escapeHtml(c.family)}</span></td>
                                    <td>${escapeHtml(c.division || '—')}</td>
                                    <td>${escapeHtml(c.recd_date || '—')}</td>
                                    <td><span class="badge badge-purple">${escapeHtml(c.status)}</span></td>
                                    <td><span style="font-family: var(--font-mono); font-size: 12px;">${escapeHtml(c.pitnum || '—')}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
    else if (_activeAuditTab === 'condemned') {
        const container = document.getElementById('audit-tab-condemned');
        const list = _auditData.condemned_returned || [];
        
        if (list.length === 0) {
            container.innerHTML = `
                <div class="card card-no-hover" style="text-align: center; padding: 40px;">
                    <div style="font-size: 40px; margin-bottom: 12px;">🎉</div>
                    <h3 style="color: var(--text-primary);">No Coaches</h3>
                    <p style="color: var(--text-secondary);">No condemned or returned coaches found for this period.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="card card-no-hover">
                <div class="card-title">🗑️ Condemned & Returned Coaches (${list.length})</div>
                <p style="color: var(--text-secondary); margin-bottom: 15px; font-size: 13px;">
                    Coaches that have been marked with status <strong>COND</strong>, <strong>BHOPAL</strong>, or <strong>RETURN</strong>. These are excluded from all operational outturn and corrosion rankings.
                </p>
                <div style="overflow-x: auto;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Coach No</th>
                                <th>Description</th>
                                <th>Family</th>
                                <th>Division</th>
                                <th>Recd Date</th>
                                <th>Paper Outturn</th>
                                <th>Actual Despatch</th>
                                <th>Status</th>
                                <th>Pit Location</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${list.map(c => `
                                <tr>
                                    <td style="font-weight: 600; color: var(--accent);">${escapeHtml(c.coachno)}</td>
                                    <td>${escapeHtml(c.coach_desc)}</td>
                                    <td><span class="badge badge-info">${escapeHtml(c.family)}</span></td>
                                    <td>${escapeHtml(c.division || '—')}</td>
                                    <td>${escapeHtml(c.recd_date || '—')}</td>
                                    <td>${escapeHtml(c.desp_date || '—')}</td>
                                    <td>${escapeHtml(c.actualdespdate || '—')}</td>
                                    <td><span class="badge badge-danger">${escapeHtml(c.status)}</span></td>
                                    <td><span style="font-family: var(--font-mono); font-size: 12px;">${escapeHtml(c.pitnum || '—')}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }
}
window.renderActiveAuditTab = renderActiveAuditTab;


/* ============================================================
   INIT ON DOM READY
   ============================================================ */

document.addEventListener('DOMContentLoaded', init);
