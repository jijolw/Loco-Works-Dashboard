/* ============================================================
   LW/PER Workshop Intelligence — Aerial View Module
   ============================================================ */

window.filterAerialByFamily = function(family) {
    const el = document.getElementById('af-family');
    if (el) {
        el.value = family;
        applyAerialFilters();
    }
};

window.filterAerialByType = function(type) {
    const el = document.getElementById('af-coachtype');
    if (el) {
        el.value = type;
        applyAerialFilters();
    }
};

window.filterAerialDetail = function(text) {
    const table = document.querySelector('#aerial-detail-table');
    if (table) {
        const input = table.closest('.table-container').previousElementSibling?.querySelector('.search-input');
        if (input) {
            input.value = text;
            filterTable('aerial-detail-table', text);
        }
    }
};

/* ---------- Zone CSS class map ---------- */
const ZONE_CSS = {
    'PAINT':        'paint',
    'LBR':          'lbr',
    'INCOMING':     'incoming',
    'AUG':          'aug',
    'DEMU_WASH':    'demu-wash',
    'DEMU':         'demu',
    'STABLING':     'stabling',
    'LCB':          'lcb',
    'CENTRAL_WEST': 'hcb',
    'CENTRAL_EAST': 'lcb',
    'HCB':          'hcb',
    'AC':           'ac',
    'DESP':         'desp',
    'YARD':         'yard',
    // Abbreviations from topology.py
    'PS':           'paint',
    'SY':           'lbr',
    'AS':           'aug',
    'DM':           'demu',
    'OT':           'yard',
};

/* ---------- Pit display name overrides ---------- */
const PIT_DISPLAY_NAMES = {
    'LBR/WP': 'Pit 2',
    'LBR/P1': 'Pit 1',
};

/* ---------- Two-slot custom sub-labels ---------- */
const TWO_SLOT_LABELS = {
    'LBR/WP': ['WP', 'WP2'],
};

/* ---------- Zone display names ---------- */
const ZONE_NAMES = {
    'PAINT':        'PAINT SHOP',
    'LBR':          'LBR SHED',
    'INCOMING':     'INCOMING LINE',
    'AUG':          'AUG SHOP',
    'DEMU_WASH':    'DEMU WASH',
    'DEMU':         'DEMU SHED',
    'STABLING':     'STABLING LINE',
    'LCB':          'LCB SHOP',
    'CENTRAL_WEST': 'CENTRAL WEST',
    'CENTRAL_EAST': 'CENTRAL EAST',
    'HCB':          'HCB SHOP',
    'AC':           'AC SHOP',
    'DESP':         'DESPATCH LINE',
    'YARD':         'YARD',
    // Abbreviations from topology.py
    'PS':           'PAINT SHOP',
    'LBR':          'LBR SHED',
    'AS':           'AUG SHOP',
    'DM':           'DEMU SHOP',
    'OT':           'YARD / OTHER',
};

/* ---------- Status helpers ---------- */

function getStatusClass(coach) {
    if (!coach) return 's-normal';
    const s = (coach.AERIAL_STATUS || coach.status || '').toUpperCase();
    if (s.includes('DANGER')) return 's-danger';
    if (s.includes('UNDER CORROSION')) return 's-corr';
    if (s.includes('CORROSION DONE')) return 's-cdone';
    if (s.includes('OUTTURNED')) return 's-outturned';
    return 's-normal';
}

function getStatusLabel(coach) {
    const cls = getStatusClass(coach);
    if (cls === 's-danger') return 'Danger: VG Pending';
    if (cls === 's-corr') return 'Under Corrosion';
    if (cls === 's-cdone') return 'Corrosion Completed';
    if (cls === 's-outturned') return 'Outturn Taken';
    return 'Routine POH';
}

/* ---------- Coach lookup helpers ---------- */

/**
 * Find coaches sitting at a given pit prefix.
 * Handles PITNUM_ALIASES (e.g. 'P1' might also be 'PT1').
 */
function getCoachesForPit(prefix, coaches, aliases) {
    if (!coaches || !coaches.length) return [];

    if (prefix === 'OT/YD') {
        const shopPrefixes = [
            'PS/P2', 'PS/L2', 'PS/L1', 'PS/P1',
            'LBR/WP', 'LBR/L4', 'LBR/L3', 'LBR/L2', 'LBR/P1', 'LBR/L1', 'LBR/P2',
            'AS/L6', 'AS/L5', 'AS/P4', 'AS/P3', 'AS/P2', 'AS/L1',
            'DM/L32A', 'DM/L32', 'DM/L31', 'DM/L30', 'DM/L29', 'DM/L28', 'DM/L27', 'DM/C', 'DM/B', 'DM/BL',
            'LCB/L16A', 'LCB/L16', 'LCB/L15', 'LCB/P14', 'LCB/L13', 'LCB/L12', 'LCB/L11', 'LCB/C',
            'HCB/L26', 'HCB/L25', 'HCB/L24', 'HCB/L23', 'HCB/L22', 'HCB/L21', 'HCB/L20', 'HCB/L19', 'HCB/L18', 'HCB/L17', 'HCB/DESP',
            'AC/P10', 'AC/P9', 'AC/L8', 'AC/L7', 'AC/L6', 'AC/L5', 'AC/L4', 'AC/L3', 'AC/L2', 'AC/L1',
            'ACB/P10', 'ACB/P9', 'ACB/L8', 'ACB/L7', 'ACB/L6', 'ACB/L5', 'ACB/L4', 'ACB/L3', 'ACB/L2', 'ACB/L1',
            'OT/IN', 'DESP', 'OT/DESP', 'HCB/DESP'
        ];
        return coaches.filter(c => {
            const pit = (c.pitnum || c.pit_num || c.location || '').toUpperCase().trim();
            if (!pit) return true;
            if (pit.startsWith('OT/YD') || pit.includes('YARD') || pit.includes('YD')) return true;
            const isShop = shopPrefixes.some(pfx => {
                const up = pfx.toUpperCase();
                if (pit === up) return true;
                if (pit === up + '_1' || pit === up + '_2') return true;
                if (pit.startsWith(up) && /^_?\d?$/.test(pit.slice(up.length))) return true;
                return false;
            });
            return !isShop;
        });
    }

    // Gather all possible prefixes (including aliases)
    const prefixes = [prefix];
    if (aliases) {
        for (const [alias, canonical] of Object.entries(aliases)) {
            if (canonical === prefix) prefixes.push(alias);
            if (alias === prefix) prefixes.push(canonical);
        }
    }

    return coaches.filter(c => {
        const pit = (c.pitnum || c.pit_num || c.location || '').toUpperCase().trim();
        
        // If the coach's exact location is aliased to a different prefix, exclude it.
        if (aliases) {
            const aliasKey = Object.keys(aliases).find(k => k.toUpperCase() === pit.toUpperCase());
            if (aliasKey && aliases[aliasKey].toUpperCase() !== prefix.toUpperCase()) {
                return false;
            }
        }

        for (const pfx of prefixes) {
            const up = pfx.toUpperCase();
            if (pit === up) return true;
            if (pit === up + '_1' || pit === up + '_2') return true;
            // Numeric suffix match: P1 matches P1, but not P10
            if (pit.startsWith(up) && /^_?\d?$/.test(pit.slice(up.length))) return true;
        }
        return false;
    });
}

/**
 * Get coach at a specific two-slot position (slot 1 or 2).
 */
function getCoachAtSlot(prefix, slot, coaches, aliases) {
    const all = getCoachesForPit(prefix, coaches, aliases);
    const slotStr = prefix.toUpperCase() + '_' + slot;
    // Try exact slot match first
    const exact = all.find(c => {
        const pit = (c.pitnum || c.pit_num || c.location || '').toUpperCase().trim();
        return pit === slotStr;
    });
    if (exact) return exact;

    // If slot is 1, try plain prefix or plain alias (without slot suffix)
    if (slot === 1) {
        const plain = all.find(c => {
            const pit = (c.pitnum || c.pit_num || c.location || '').toUpperCase().trim();
            if (pit === prefix.toUpperCase()) return true;
            if (aliases) {
                // Find case-insensitive alias match
                const aliasKey = Object.keys(aliases).find(k => k.toUpperCase() === pit);
                if (aliasKey && aliases[aliasKey].toUpperCase() === prefix.toUpperCase() && !pit.includes('_')) {
                    return true;
                }
            }
            return false;
        });
        if (plain) return plain;
    }

    // Try alias matching (e.g. SY/P2_1 matches slot 1 of canonical SY/P1)
    if (aliases) {
        for (const [alias, canonical] of Object.entries(aliases)) {
            if (canonical.toUpperCase() === prefix.toUpperCase()) {
                const parts = alias.split('_');
                const aliasSlot = parts.length > 1 ? parts[parts.length - 1] : '';
                if (aliasSlot === String(slot)) {
                    const match = all.find(c => {
                        const pit = (c.pitnum || c.pit_num || c.location || '').toUpperCase().trim();
                        return pit === alias.toUpperCase();
                    });
                    if (match) return match;
                }
            }
        }
    }

    return null;
}

/* ---------- Coach box HTML ---------- */

function coachBoxHtml(coach, searchText, filteredSet) {
    if (!coach) return '';

    const num = coach.coachno || coach.coach_num || '?';
    const statusCls = getStatusClass(coach);
    const coachType = coach.coach_desc || coach.coach_type || '';
    const repairType = coach.repair_type || '';
    const days = coach.IN_DAYS;
    const daysStr = (days !== null && days !== undefined && days !== '') ? days + 'd' : '';
    const subParts = [coachType, repairType, daysStr].filter(Boolean);
    const subText = subParts.join(' | ');

    // Highlight
    let hlClass = '';
    if (searchText && String(num).toLowerCase().includes(searchText.toLowerCase())) {
        hlClass = 'hl';
    }

    // Dimmed if filter active but this coach not in set
    let dimClass = '';
    if (filteredSet && !filteredSet.has(num)) {
        dimClass = 'cb-dimmed';
    }

    // Resolve Family Badge (LHB, TC, TW, ICF, NMG)
    const family = (coach.family || '').toUpperCase();
    const desc = (coach.coach_desc || coach.coach_type || '').toUpperCase();
    let familyBadgeHtml = '';
    
    if (family === 'LHB') {
        familyBadgeHtml = '<span class="c-badge badge-lhb">LHB</span>';
    } else if (family === 'TW') {
        familyBadgeHtml = '<span class="c-badge badge-tw">TW</span>';
    } else if (family === 'ICF') {
        familyBadgeHtml = '<span class="c-badge badge-icf">ICF</span>';
    } else if (family === 'NMG') {
        familyBadgeHtml = '<span class="c-badge badge-nmg">NMG</span>';
    } else if (family === 'DEMU' || family === 'EMU' || family === 'MEMU' || family.includes('TC') || desc.includes('DPC') || desc.includes('DTC') || desc.includes('YSY') || desc.includes('YSD') || desc.includes('MC') || desc.includes('TC')) {
        // Resolve sub-type within EMU/MEMU/DEMU/TC family
        let badgeText = 'TC';
        if (desc.includes('DPC')) {
            badgeText = 'DPC';
        } else if (desc.includes('DTC')) {
            badgeText = 'DTC';
        } else if (desc.includes('MEMUTC') || desc.includes('MEMU TC')) {
            badgeText = 'M TC';
        } else if (desc.includes('MEMUMC') || desc.includes('MEMU MC')) {
            badgeText = 'M MC';
        } else if (desc.includes('EMUTC') || desc.includes('EMU TC') || desc.includes('YSY') || desc.includes('YFSY') || desc.includes('YSD')) {
            badgeText = 'ETC';
        } else if (desc.includes('EMUMC') || desc.includes('EMU MC') || desc.includes('YZZS') || desc.includes('DMSC')) {
            badgeText = 'E MC';
        } else if (desc.includes('MC') || desc.includes('MOTOR')) {
            if (family === 'MEMU' || desc.includes('MEMU')) badgeText = 'M MC';
            else if (family === 'EMU' || desc.includes('EMU')) badgeText = 'E MC';
            else badgeText = 'MC';
        } else if (desc.includes('TC') || desc.includes('TRAILER')) {
            if (family === 'MEMU' || desc.includes('MEMU')) badgeText = 'M TC';
            else if (family === 'EMU' || desc.includes('EMU')) badgeText = 'ETC';
            else badgeText = 'TC';
        } else {
            // Defaults based on family
            if (family === 'MEMU') badgeText = 'M TC';
            else if (family === 'EMU') badgeText = 'ETC';
            else badgeText = 'TC';
        }
        familyBadgeHtml = `<span class="c-badge badge-tc">${badgeText}</span>`;
    }

    // Resolve Severity Badge (local rules: VH > 1000, H 500-1000, L < 500)
    let sevBadgeHtml = '';
    const hrs = parseFloat(coach.man_hours || coach.effective_hours || coach.eff_hours || 0);
    if (statusCls === 's-corr' || statusCls === 's-cdone') {
        if (hrs >= 1000) {
            sevBadgeHtml = '<span class="c-badge badge-vh" title="Very Heavy Corrosion (1000+ hrs)">VH</span>';
        } else if (hrs >= 500) {
            sevBadgeHtml = '<span class="c-badge badge-h" title="Heavy Corrosion (500-1000 hrs)">H</span>';
        } else {
            sevBadgeHtml = '<span class="c-badge badge-l" title="Light Corrosion (<500 hrs)">L</span>';
        }
    }

    let tooltip = `${escapeHtml(String(num))} — ${escapeHtml(getStatusLabel(coach))}&#10;` +
                  `${escapeHtml(coachType)} | ${escapeHtml(repairType)}&#10;` +
                  `Days Inside: ${escapeHtml(String(daysStr || '—'))}`;
    if (coach.corr_place) tooltip += `&#10;Corrosion In: ${escapeHtml(coach.corr_place)}`;
    if (coach.corr_comp) tooltip += `&#10;Corrosion Comp: ${escapeHtml(coach.corr_comp)}`;
    if (coach.lowering_status) tooltip += `&#10;Lowering: ${escapeHtml(coach.lowering_status)}`;
    if (coach.furnishing_status) tooltip += `&#10;Furnishing: ${escapeHtml(coach.furnishing_status)}`;
    if (coach.despatch_status) tooltip += `&#10;Despatch Stage: ${escapeHtml(coach.despatch_status)}`;
    if (coach.google_remarks) tooltip += `&#10;GS Remarks: ${escapeHtml(coach.google_remarks)}`;
    if (coach.remarks) tooltip += `&#10;ERP Remarks: ${escapeHtml(coach.remarks)}`;

    return `<div class="cb ${statusCls} ${hlClass} ${dimClass}" style="cursor: pointer;" title="${tooltip}" onclick="window.navigateToSearch('${escapeHtml(String(num))}')">
        <div style="display:flex; justify-content:space-between; align-items:center; width:100%; margin-bottom:4px;">
            <span style="font-weight:700;">${escapeHtml(String(num))}</span>
            <div class="cb-badges">
                ${familyBadgeHtml}
                ${sevBadgeHtml}
            </div>
        </div>
        <span class="cb-sub">${escapeHtml(subText)}</span>
    </div>`;
}

/* ---------- Render one shop zone ---------- */

function renderShop(title, pitLines, cssClass, coaches, searchText, filteredSet, twoSlotLines, aliases, nodeLabel) {
    const zoneName = nodeLabel || ZONE_NAMES[title] || title;
    const cls = ZONE_CSS[title] || cssClass || '';

    let html = `<div class="zone ${cls}">`;
    html += `<div class="zone-title">${escapeHtml(zoneName)}</div>`;

    if (pitLines && pitLines.length) {
        pitLines.forEach(pit => {
            const displayName = PIT_DISPLAY_NAMES[pit] || pit;
            const isTwoSlot = twoSlotLines && twoSlotLines.includes(pit);
            html += `<div class="line-row">`;
            html += `<div class="line-name">${escapeHtml(displayName)}</div>`;
            html += `<div class="coach-row">`;

            if (isTwoSlot) {
                // Two-slot line: show two fixed positions
                const labels = TWO_SLOT_LABELS[pit] || ['', ''];
                for (let slot = 1; slot <= 2; slot++) {
                    const c = getCoachAtSlot(pit, slot, coaches, aliases);
                    const label = labels[slot - 1] || '—';
                    if (c) {
                        html += coachBoxHtml(c, searchText, filteredSet);
                    } else {
                        html += `<div class="empty-box">${escapeHtml(label)}</div>`;
                    }
                }
            } else {
                // Normal: show all coaches on this line
                const lineCoaches = getCoachesForPit(pit, coaches, aliases);
                if (lineCoaches.length) {
                    lineCoaches.forEach(c => {
                        html += coachBoxHtml(c, searchText, filteredSet);
                    });
                } else {
                    html += `<div class="empty-box">—</div>`;
                }
            }

            html += `</div></div>`;
        });
    }

    html += `</div>`;
    return html;
}

/* ---------- Render flat line ---------- */

function renderFlat(title, pitnums, cssClass, coaches, searchText, filteredSet, aliases) {
    const zoneName = ZONE_NAMES[title] || title;
    const cls = ZONE_CSS[title] || cssClass || '';

    let html = `<div class="zone ${cls}">`;
    html += `<div class="zone-title">${escapeHtml(zoneName)}</div>`;
    html += `<div class="coach-row" style="flex-wrap:wrap;gap:4px;">`;

    if (pitnums && pitnums.length) {
        let hasAny = false;
        pitnums.forEach(pit => {
            const lineCoaches = getCoachesForPit(pit, coaches, aliases);
            lineCoaches.forEach(c => {
                html += coachBoxHtml(c, searchText, filteredSet);
                hasAny = true;
            });
        });
        if (!hasAny) {
            html += `<div class="empty-box">Empty</div>`;
        }
    } else {
        // Show all coaches whose pit starts with zone-related prefix
        html += `<div class="empty-box">Empty</div>`;
    }

    html += `</div></div>`;
    return html;
}

/* ---------- Render traverser ---------- */

function renderTraverser(label) {
    return `<div class="traverser">◂ ${escapeHtml(label || 'TRAVERSER')} ▸</div>`;
}

/* ---------- Render topology recursively ---------- */

function renderLayoutNode(node, coaches, searchText, filteredSet, twoSlotLines, aliases) {
    if (!node) return '';
    const type = node.type;

    if (type === 'row') {
        let html = `<div class="layout-row">`;
        const cols = node.cols || [];
        const zones = node.zones || [];
        zones.forEach((z, i) => {
            const colStyle = cols[i] ? ` style="flex:${cols[i]}"` : '';
            html += `<div class="layout-col"${colStyle}>`;
            html += renderLayoutNode(z, coaches, searchText, filteredSet, twoSlotLines, aliases);
            html += `</div>`;
        });
        html += `</div>`;
        return html;
    }

    if (type === 'shop') {
        return renderShop(node.zone, node.order || node.pits, null, coaches, searchText, filteredSet, twoSlotLines, aliases, node.label);
    }

    if (type === 'flat') {
        return renderFlat(node.zone, node.pitnums, null, coaches, searchText, filteredSet, aliases);
    }

    if (type === 'traverser') {
        return renderTraverser(node.label || 'TRAVERSER');
    }

    if (type === 'stack') {
        let html = '';
        (node.zones || []).forEach(z => {
            html += renderLayoutNode(z, coaches, searchText, filteredSet, twoSlotLines, aliases);
        });
        return html;
    }

    if (type === 'direction') {
        return `<div class="direction">${escapeHtml(node.label || '')}</div>`;
    }

    if (type === 'spring_placeholder' || type === 'stabling_placeholder') {
        const zoneName = ZONE_NAMES[node.zone] || node.zone || type;
        const cls = ZONE_CSS[node.zone] || '';
        return `<div class="zone ${cls}"><div class="zone-title">${escapeHtml(zoneName)}</div><div class="empty-box">—</div></div>`;
    }

    return '';
}

/* ---------- Build filter controls ---------- */

function buildFilterControls(coaches) {
    // Gather unique values
    const families = new Set();
    const statuses = new Set();
    const coachTypes = new Set();
    const repairTypes = new Set();

    coaches.forEach(c => {
        if (c.family) families.add(c.family);
        const sl = getStatusLabel(c);
        statuses.add(sl);
        if (c.coach_desc) coachTypes.add(c.coach_desc);
        if (c.repair_type) repairTypes.add(c.repair_type);
    });

    function optionsHtml(set) {
        return Array.from(set).sort().map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');
    }

    return `
    <div class="filter-bar" id="aerialFilters">
        <div class="filter-group">
            <label class="filter-label">Family</label>
            <select class="filter-select" id="af-family">
                <option value="">All</option>
                ${optionsHtml(families)}
            </select>
        </div>
        <div class="filter-group">
            <label class="filter-label">Status</label>
            <select class="filter-select" id="af-status">
                <option value="">All</option>
                ${optionsHtml(statuses)}
            </select>
        </div>
        <div class="filter-group">
            <label class="filter-label">Coach Type</label>
            <select class="filter-select" id="af-coachtype">
                <option value="">All</option>
                ${optionsHtml(coachTypes)}
            </select>
        </div>
        <div class="filter-group">
            <label class="filter-label">Repair Type</label>
            <select class="filter-select" id="af-repair">
                <option value="">All</option>
                ${optionsHtml(repairTypes)}
            </select>
        </div>
        <div class="filter-group">
            <label class="filter-label">Search Coach</label>
            <input type="text" class="filter-input" id="af-search" placeholder="Coach number…" style="width:150px">
        </div>
        <div class="filter-group" style="align-self:flex-end;display:flex;gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="clearAerialFilters()">Clear</button>
            <a class="btn btn-secondary btn-sm" href="/report/aerial" target="_blank" style="text-decoration:none;display:inline-flex;align-items:center;height:32px;box-sizing:border-box;">📊 Monthly Report</a>
            <a class="btn btn-primary btn-sm" href="/coach/reports/aerialview/print.html" target="_blank" style="text-decoration:none;display:inline-flex;align-items:center;height:32px;box-sizing:border-box;">🖨️ Print Layout</a>
        </div>
    </div>`;
}

/* ---------- Build legend ---------- */

function buildLegend() {
    return `
    <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:rgba(139,0,0,0.95);border:1px solid #ff0000;box-shadow:0 0 4px rgba(255,0,0,0.6)"></div> Danger: VG Pending</div>
        <div class="legend-item"><div class="legend-dot" style="background:rgba(192,57,43,0.85)"></div> Under Corrosion</div>
        <div class="legend-item"><div class="legend-dot" style="background:#f1c40f"></div> Corrosion Completed</div>
        <div class="legend-item"><div class="legend-dot" style="background:rgba(22,163,74,0.85)"></div> Outturn Taken</div>
        <div class="legend-item"><div class="legend-dot" style="background:rgba(36,113,163,0.6)"></div> Routine POH</div>
        <div class="legend-item"><div class="legend-dot" style="background:transparent;border:1px dashed rgba(255,255,255,0.3)"></div> Empty Slot</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--gold)"></div> Search Match</div>
    </div>`;
}

/* ---------- Build detail table ---------- */

function buildDetailTable(coaches, filteredCoaches) {
    const data = filteredCoaches || coaches;
    if (!data || !data.length) return '';

    const columns = [
        { key: 'coachno', label: 'Coach No.', sortable: true,
          format: (v) => `<a href="javascript:void(0)" onclick="window.navigateToSearch('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>`
        },
        { key: 'coach_desc', label: 'Type', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterAerialByType('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'repair_type', label: 'Repair', sortable: true },
        { key: 'pitnum', label: 'Location', sortable: true },
        { key: 'AERIAL_STATUS', label: 'Status', sortable: true,
          format: (v, row) => {
              const cls = getStatusClass(row);
              const lbl = getStatusLabel(row);
              const badgeCls = cls === 's-danger' ? 'badge-danger' :
                               cls === 's-corr' ? 'badge-danger' :
                               cls === 's-cdone' ? 'badge-warning' :
                               cls === 's-outturned' ? 'badge-success' : 'badge-info';
              return `<span class="badge ${badgeCls}">${escapeHtml(lbl)}</span>`;
          }
        },
        { key: 'recd_date', label: 'Entry Date', sortable: true, format: v => formatDate(v) },
        { key: 'IN_DAYS', label: 'Days', sortable: true,
          format: (v) => {
              return (v !== null && v !== undefined) ? v : '—';
          }
        },
        { key: 'division', label: 'Division', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterAerialDetail('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
        { key: 'family', label: 'Family', sortable: true,
          format: (v) => v ? `<a href="javascript:void(0)" onclick="window.filterAerialByFamily('${escapeHtml(v)}')" class="table-link">${escapeHtml(v)}</a>` : '—'
        },
    ];

    const colorRowFn = (row) => {
        const cls = getStatusClass(row);
        if (cls === 's-danger') return 'row-danger';
        if (cls === 's-corr') return 'row-danger';
        if (cls === 's-cdone') return 'row-warning';
        if (cls === 's-outturned') return 'row-success';
        return 'row-info';
    };

    return `
    <div class="detail-panel">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
            <h3 style="font-size:15px;font-weight:600;color:var(--text-primary);">
                Coach Details (${data.length})
            </h3>
            <div style="display:flex;gap:8px;">
                <button class="btn btn-secondary btn-sm" onclick="downloadAerialCSV()">📥 Download CSV</button>
                <a class="btn btn-secondary btn-sm" href="/report/aerial" target="_blank" style="text-decoration:none;display:inline-flex;align-items:center;height:32px;box-sizing:border-box;">📊 Monthly Report</a>
                <button class="btn btn-primary btn-sm" onclick="openAerialPrintReport()" style="display:inline-flex;align-items:center;height:32px;box-sizing:border-box;border:none;cursor:pointer;">🖨️ Print Layout</button>
            </div>
        </div>
        ${createDataTable(data, columns, {
            id: 'aerial-detail-table',
            height: 400,
            colorRowFn: colorRowFn,
            searchable: true
        })}
    </div>`;
}

/* ============================================================
   MAIN RENDER FUNCTION
   ============================================================ */

/** Cached data for CSV download & re-renders */
let _aerialData = null;

function renderAerialView(data) {
    const acCoaches = (data.ac_locos || [])
        .filter(l => l.loco_no && String(l.loco_no).trim() !== '')
        .map(l => ({
            coachno: String(l.loco_no).trim(),
            coach_desc: String(l.loco_desc || 'WAP7').trim(),
            pitnum: String(l.pitnum || '').trim(),
            family: 'LOCO',
            recd_date: l.date_recd,
            AERIAL_STATUS: 'NORMAL',
            status: 'NORMAL',
            IN_DAYS: 0
        }));
    data.coaches = [...(data.coaches || []), ...acCoaches];

    _aerialData = data;

    const coaches = data.coaches;
    const topology = data.topology || {};
    const metrics = data.metrics || {};
    const layout = Array.isArray(topology) ? topology : (topology.LAYOUT || topology || []);
    const twoSlotLines = data.two_slot_lines || topology.TWO_SLOT_LINES || [];
    const aliases = data.pitnum_aliases || topology.PITNUM_ALIASES || {};

    const container = document.getElementById('main-content');
    if (!container) return;

    // Initial render with no filters
    _renderAerialFull(container, coaches, layout, twoSlotLines, aliases, metrics, '', null);

    // Attach filter listeners after DOM render
    setTimeout(() => {
        const ids = ['af-family', 'af-status', 'af-coachtype', 'af-repair'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => applyAerialFilters());
        });
        const searchEl = document.getElementById('af-search');
        if (searchEl) {
            searchEl.addEventListener('input', debounce(() => applyAerialFilters(), 250));
        }
    }, 50);
}

function _renderAerialFull(container, coaches, layout, twoSlotLines, aliases, metrics, searchText, filteredSet) {
    // Count metrics
    const total = coaches.length;
    const dangerCount = coaches.filter(c => getStatusClass(c) === 's-danger').length;
    const corrCount = coaches.filter(c => getStatusClass(c) === 's-corr').length;
    const doneCount = coaches.filter(c => getStatusClass(c) === 's-cdone').length;
    const outturnCount = coaches.filter(c => getStatusClass(c) === 's-outturned').length;
    const normalCount = coaches.filter(c => getStatusClass(c) === 's-normal').length;

    // Determine filtered coaches for detail table
    let filteredCoaches = coaches;
    if (filteredSet) {
        filteredCoaches = coaches.filter(c => filteredSet.has(c.coachno || c.coach_num));
    }
    if (searchText) {
        filteredCoaches = filteredCoaches.filter(c => {
            const num = String(c.coachno || c.coach_num || '').toLowerCase();
            return num.includes(searchText.toLowerCase());
        });
    }

    let html = '';

    // Page header
    html += `<div class="page-header anim-slide">
        <h1 class="page-title">🏭 Aerial View</h1>
        <p class="page-subtitle">Real-time workshop floor map — coach positions and status at a glance</p>
    </div>`;

    // Metrics
    html += `<div class="metrics-grid anim-slide">`;
    html += createMetricCard('Total Inside', metrics.total || total, '🚃', 'accent-blue');
    html += createMetricCard('Danger: VG Pending', metrics.danger || dangerCount, '🚨', 'accent-danger');
    html += createMetricCard('Under Corrosion', metrics.under_corrosion || corrCount, '🔴', 'accent-danger');
    html += createMetricCard('Corrosion Completed', metrics.corrosion_done || doneCount, '🟡', 'accent-warning');
    html += createMetricCard('Outturn Taken', metrics.outturned || outturnCount, '🟢', 'accent-success');
    html += createMetricCard('Routine POH', metrics.normal || normalCount, '🔵', 'accent-info');
    html += `</div>`;

    // Filters
    html += buildFilterControls(coaches);

    // Legend
    html += buildLegend();

    // PDF Report Overrides Card
    html += `
    <div class="card card-no-hover" style="padding: 16px; margin: 15px 0; border: 1px dashed var(--accent);">
        <div style="font-weight: 600; font-size: 14px; color: var(--accent); margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span>📝 PDF Report Customization</span>
            <span style="font-size: 11px; font-weight: normal; color: var(--text-secondary);">(Optional manual overrides for PDF print generation — does not change database)</span>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
            <div class="filter-group" style="margin: 0;">
                <label class="filter-label" style="color: #A04000; font-weight: 600;">Today's Planned Outturn</label>
                <input type="text" class="filter-input" id="rep-today-plan" placeholder="e.g. 231204,156448" style="width: 100%;">
            </div>
            <div class="filter-group" style="margin: 0;">
                <label class="filter-label" style="color: #1A4F9C; font-weight: 600;">Tomorrow's Plan</label>
                <input type="text" class="filter-input" id="rep-tmrw-plan" placeholder="e.g. 156440,231205" style="width: 100%;">
            </div>
            <div class="filter-group" style="margin: 0;">
                <label class="filter-label" style="color: var(--success); font-weight: 600;">Yesterday's Outturn</label>
                <input type="text" class="filter-input" id="rep-today-out" placeholder="e.g. 156440,156448" style="width: 100%;">
            </div>
            <div class="filter-group" style="margin: 0;">
                <label class="filter-label" style="color: #145A32; font-weight: 600;">Yesterday's WISE Despatch</label>
                <input type="text" class="filter-input" id="rep-wise-desp" placeholder="e.g. 086440,156448" style="width: 100%;">
            </div>
        </div>
    </div>
    `;

    // Workshop map
    html += `<div class="aerial-container anim-fade" id="aerial-map">`;
    layout.forEach(node => {
        html += renderLayoutNode(node, coaches, searchText, filteredSet, twoSlotLines, aliases);
    });
    html += `</div>`;

    // Detail table
    html += buildDetailTable(coaches, filteredCoaches);

    container.innerHTML = html;
}

/* ---------- Filter logic ---------- */

function applyAerialFilters() {
    if (!_aerialData) return;

    const coaches = _aerialData.coaches || [];
    const topology = _aerialData.topology || {};
    const metrics = _aerialData.metrics || {};
    const layout = topology.LAYOUT || [];
    const twoSlotLines = topology.TWO_SLOT_LINES || [];
    const aliases = topology.PITNUM_ALIASES || {};

    const family = (document.getElementById('af-family') || {}).value || '';
    const status = (document.getElementById('af-status') || {}).value || '';
    const coachType = (document.getElementById('af-coachtype') || {}).value || '';
    const repair = (document.getElementById('af-repair') || {}).value || '';
    const search = (document.getElementById('af-search') || {}).value || '';

    // Preserve search box focus and cursor selection
    const searchElBefore = document.getElementById('af-search');
    const isSearchFocused = (document.activeElement === searchElBefore);
    let selectionStart = 0;
    let selectionEnd = 0;
    if (searchElBefore) {
        selectionStart = searchElBefore.selectionStart;
        selectionEnd = searchElBefore.selectionEnd;
    }

    let filteredSet = null;
    const hasFilter = family || status || coachType || repair;

    if (hasFilter) {
        const filtered = coaches.filter(c => {
            if (family && (c.family || '') !== family) return false;
            if (status && getStatusLabel(c) !== status) return false;
            if (coachType && (c.coach_desc || '') !== coachType) return false;
            if (repair && (c.repair_type || '') !== repair) return false;
            return true;
        });
        filteredSet = new Set(filtered.map(c => c.coachno || c.coach_num));
    }

    const container = document.getElementById('main-content');
    _renderAerialFull(container, coaches, layout, twoSlotLines, aliases, metrics, search, filteredSet);

    // Restore filter values after re-render
    setTimeout(() => {
        if (family) { const el = document.getElementById('af-family'); if (el) el.value = family; }
        if (status) { const el = document.getElementById('af-status'); if (el) el.value = status; }
        if (coachType) { const el = document.getElementById('af-coachtype'); if (el) el.value = coachType; }
        if (repair) { const el = document.getElementById('af-repair'); if (el) el.value = repair; }
        
        // Always restore search value and focus if it was focused
        const searchEl = document.getElementById('af-search');
        if (searchEl) {
            searchEl.value = search;
            if (isSearchFocused) {
                searchEl.focus();
                try {
                    searchEl.setSelectionRange(selectionStart, selectionEnd);
                } catch (e) {}
            }
        }

        // Re-attach listeners
        ['af-family', 'af-status', 'af-coachtype', 'af-repair'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => applyAerialFilters());
        });
        if (searchEl) {
            searchEl.addEventListener('input', debounce(() => applyAerialFilters(), 250));
        }
    }, 30);
}

function clearAerialFilters() {
    ['af-family', 'af-status', 'af-coachtype', 'af-repair'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const searchEl = document.getElementById('af-search');
    if (searchEl) searchEl.value = '';
    applyAerialFilters();
}

/* ---------- CSV download for aerial ---------- */

function downloadAerialCSV() {
    if (!_aerialData || !_aerialData.coaches) return;
    const data = _aerialData.coaches.map(c => ({
        'Coach Number': c.coachno || '',
        'Coach Type': c.coach_desc || '',
        'Repair Type': c.repair_type || '',
        'Location': c.pitnum || '',
        'Status': getStatusLabel(c),
        'Entry Date': c.recd_date || '',
        'Days Inside': c.IN_DAYS || '',
        'Division': c.division || '',
        'Family': c.family || '',
        'Corrosion In Date': c.corr_place || '',
        'Corrosion Comp. Date': c.corr_comp || '',
        'Lowering Stage': c.lowering_status || '',
        'Furnishing Stage': c.furnishing_status || '',
        'Despatch Stage': c.despatch_status || '',
        'Google Sheet PDC': c.google_pdc || '',
        'Google Remarks': c.google_remarks || '',
    }));
    downloadCSV(data, 'aerial_view_coaches.csv');
}

function openAerialPrintReport() {
    const todayPlan = document.getElementById('rep-today-plan')?.value || '';
    const tmrwPlan = document.getElementById('rep-tmrw-plan')?.value || '';
    const todayOut = document.getElementById('rep-today-out')?.value || '';
    const wiseDesp = document.getElementById('rep-wise-desp')?.value || '';
    
    let url = '/reports/aerialview/print.html';
    if (window.location.pathname.startsWith('/coach') || window.location.pathname.includes('/cr')) {
        url = '/coach/reports/aerialview/print.html';
    }
    
    const params = [];
    if (todayPlan) params.push(`today_plan=${encodeURIComponent(todayPlan)}`);
    if (tmrwPlan) params.push(`tmrw_plan=${encodeURIComponent(tmrwPlan)}`);
    if (todayOut) params.push(`today_out=${encodeURIComponent(todayOut)}`);
    if (wiseDesp) params.push(`wise_desp=${encodeURIComponent(wiseDesp)}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    window.open(url, '_blank');
}
window.openAerialPrintReport = openAerialPrintReport;
