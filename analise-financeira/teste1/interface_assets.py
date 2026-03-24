ST_STYLE = """
<style>
    .pivot-container { 
        font-family: 'Segoe UI', sans-serif; border: 1px solid #ccc; background: white; 
        margin-top: 10px; overflow: auto; position: relative; max-height: 850px; 
    }
    .pivot-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; table-layout: auto; }
    
    .pivot-table th { 
        background-color: #f8f9fa; padding: 12px 15px; border: 1px solid #ddd; 
        position: sticky; top: 0; z-index: 100; white-space: nowrap; cursor: pointer;
        user-select: none;
    }
    
    .sort-icon { font-size: 10px; margin-left: 5px; color: #999; }
    .filter-trigger { margin-left: 8px; color: #007bff; cursor: pointer; font-size: 14px; }
    
    .filter-menu {
        display: none; position: fixed; background: white; border: 1px solid #ccc;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2); z-index: 1000001; width: 300px;
        max-height: 400px; overflow-y: auto; padding: 10px; border-radius: 4px;
    }
    .filter-menu-item { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 12px; }
    .filter-actions { border-top: 1px solid #eee; padding-top: 10px; margin-top: 10px; display: flex; justify-content: space-between; }
    .btn-filter { padding: 4px 8px; font-size: 11px; cursor: pointer; border-radius: 3px; border: 1px solid #ddd; }
    .btn-apply { background: #007bff; color: white; border: none; }

    .cc-row { background-color: #ffffff; cursor: pointer; font-weight: bold; border-bottom: 2px solid #dee2e6; transition: background 0.2s; }
    .class-row { background-color: #fafafa; display: none; font-size: 12px; border-bottom: 1px solid #eee; transition: background 0.2s; }
    
    /* Destaque da Célula Individual */
    .pivot-table td { 
        padding: 10px 15px; border: 1px solid #eee; text-align: center; 
        position: relative; overflow: visible !important; white-space: nowrap;
        transition: all 0.2s ease;
    }
    .pivot-table td:not(.label-col):hover { 
        background-color: #e3f2fd !important; color: #0d47a1 !important; 
        font-weight: 800 !important; box-shadow: inset 0 0 0 2px #2196f3; z-index: 10 !important;
    }

    .label-col { text-align: left !important; min-width: 350px; padding-left: 15px !important; }
    .total-cell { background-color: #f8f9fa; font-weight: bold; border-left: 2px solid #ddd !important; }
    .val-pos { color: #d9534f; } .val-neg { color: #28a745; }
    
    .tt-text {
        visibility: hidden; width: 320px; background-color: #1e1e26; color: #ffffff; text-align: left;
        border-radius: 8px; padding: 15px; position: fixed; z-index: 999999 !important;
        opacity: 0; transition: opacity 0.2s ease-in-out; font-size: 11px; line-height: 1.6; 
        box-shadow: 0px 8px 24px rgba(0,0,0,0.5); pointer-events: none; border: 1px solid #444;
        white-space: normal;
    }
    .tooltip:hover .tt-text { visibility: visible; opacity: 1; }
    .exp-icon { color: #007bff; font-family: monospace; margin-right: 10px; font-weight: bold; }
</style>

<script>
let sortDirections = {};

function sortTable(colIndex) {
    const tableBody = document.querySelector(".pivot-table tbody");
    const headers = document.querySelectorAll(".pivot-table th");
    const direction = sortDirections[colIndex] === 'asc' ? 'desc' : 'asc';
    sortDirections[colIndex] = direction;

    headers.forEach(h => { if(h.querySelector(".sort-icon")) h.querySelector(".sort-icon").innerText = "↕"; });
    const currentIcon = headers[colIndex].querySelector(".sort-icon");
    if(currentIcon) currentIcon.innerText = direction === 'asc' ? "▲" : "▼";

    const ccRows = Array.from(document.querySelectorAll(".cc-row"));
    const sortedCCs = ccRows.sort((a, b) => {
        let valA = getCellValue(a, colIndex);
        let valB = getCellValue(b, colIndex);
        return direction === 'asc' ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    });

    sortedCCs.forEach(ccRow => {
        tableBody.appendChild(ccRow);
        const ccId = ccRow.getAttribute("onclick").match(/'([^']+)'/)[1];
        const children = Array.from(document.querySelectorAll(".child-" + ccId));
        children.forEach(child => tableBody.appendChild(child));
    });
}

function getCellValue(row, index) {
    const cell = row.cells[index];
    if (index === 0) return cell.innerText.toLowerCase();
    let text = cell.innerText.split('\\n')[0];
    text = text.replace(/[R$ %.]/g, '').replace(',', '.');
    return parseFloat(text) || 0;
}

function toggleFilterMenu(e) {
    e.stopPropagation();
    const menu = document.getElementById('ccFilterMenu');
    const isVisible = menu.style.display === 'block';
    menu.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
        const rect = e.target.getBoundingClientRect();
        menu.style.top = (rect.bottom + 5) + 'px';
        menu.style.left = rect.left + 'px';
    }
}

function applyCCFilter() {
    const selected = Array.from(document.querySelectorAll('#ccList input:checked')).map(cb => cb.value);
    document.querySelectorAll(".cc-row").forEach(row => {
        const ccName = row.getAttribute("data-cc-name");
        const ccId = row.getAttribute("onclick").match(/'([^']+)'/)[1];
        const children = document.querySelectorAll(".child-" + ccId);
        row.style.display = selected.includes(ccName) ? "" : "none";
        if (row.style.display === "none") children.forEach(c => c.style.display = "none");
    });
    document.getElementById('ccFilterMenu').style.display = 'none';
}

function toggleGroup(id) {
    const rows = document.getElementsByClassName('child-' + id);
    const icon = document.getElementById('icon-' + id);
    for (let i = 0; i < rows.length; i++) {
        const isHidden = rows[i].style.display === 'none' || rows[i].style.display === '';
        rows[i].style.display = isHidden ? 'table-row' : 'none';
    }
    icon.innerText = (icon.innerText === '[+]') ? '[-]' : '[+]';
}

document.addEventListener('mouseover', function(e) {
    const trigger = e.target.closest('.tooltip');
    if (trigger) {
        const tip = trigger.querySelector('.tt-text');
        if (!tip) return;
        tip.style.visibility = 'visible';
        tip.style.opacity = '1';
        const trigRect = trigger.getBoundingClientRect();
        const tipRect = tip.getBoundingClientRect();
        let top = trigRect.top - tipRect.height - 15;
        if (top < 80) top = trigRect.bottom + 15;
        let left = trigRect.left + (trigRect.width / 2) - (tipRect.width / 2);
        if (left < 10) left = 10;
        if (left + tipRect.width > window.innerWidth - 10) left = window.innerWidth - tipRect.width - 10;
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
    }
});

document.addEventListener('mouseout', function(e) {
    const trigger = e.target.closest('.tooltip');
    if (trigger) {
        if (!e.relatedTarget || !trigger.contains(e.relatedTarget)) {
            const tip = trigger.querySelector('.tt-text');
            if (tip) { tip.style.visibility = 'hidden'; tip.style.opacity = '0'; }
        }
    }
});

window.onclick = function(e) {
    if (!e.target.closest('.filter-menu') && !e.target.closest('.filter-trigger')) {
        document.getElementById('ccFilterMenu').style.display = 'none';
    }
}
</script>
"""