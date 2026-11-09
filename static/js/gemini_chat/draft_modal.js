/**
 * TRẦN BÌNH AUTO - Modal Chỉnh Sửa Đơn Đèn Trực Quan (draft_modal.js)
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    setLastAIMeta,
    setCurrentDraftMeta,
    getActiveSessionId
} from './state.js';
import { appendMessageUI } from './chat_ui.js';

export function openGarageDraftEditModal(meta) {
    meta = meta || state.lastAIMeta || (typeof window !== 'undefined' ? window.lastAIMeta : null) || {};
    setCurrentDraftMeta(meta);

    const custInput = document.getElementById('gdem_customer');
    const phoneInput = document.getElementById('gdem_phone');
    const carInput = document.getElementById('gdem_car');
    const plateInput = document.getElementById('gdem_plate');
    const dateInput = document.getElementById('gdem_date');
    const discInput = document.getElementById('gdem_discount');

    if (custInput) custInput.value = meta.customer || meta.cust_name || '';
    if (phoneInput) phoneInput.value = meta.phone || '';
    if (carInput) carInput.value = meta.car || meta.found_car || '';
    if (plateInput) plateInput.value = meta.plate || '';
    if (dateInput) dateInput.value = meta.order_date || new Date().toISOString().slice(0, 10);
    if (discInput) discInput.value = meta.discount_k || 0;

    const container = document.getElementById('gdem_items_container');
    if (container) {
        container.innerHTML = '';
        const items = (meta.items && meta.items.length > 0) ? meta.items : [{ product_name: 'BI LED', quantity: 1, unit_price_k: 4500 }];
        items.forEach(it => {
            const q = it.quantity || 1;
            const up = it.unit_price_k || (it.final_price_k ? it.final_price_k / q : 4500);
            gdemAddItemRow(it.product_name, q, up);
        });
    }
    gdemRecalcTotal();

    const modal = document.getElementById('garageDraftEditModal');
    if (modal) {
        modal.style.display = 'flex';
        modal.style.zIndex = '10000000';
    }
}

export function closeGarageDraftEditModal() {
    const modal = document.getElementById('garageDraftEditModal');
    if (modal) modal.style.display = 'none';
}

export function gdemAddItemRow(name = '', qty = 1, unitPriceK = 4500) {
    const container = document.getElementById('gdem_items_container');
    if (!container) return;
    const row = document.createElement('div');
    row.className = 'gdem-item-row';
    row.style.cssText = 'background:#0f172a; border-radius:8px; padding:8px 10px; border:1px solid rgba(255,255,255,0.08); display:grid; grid-template-columns:1.6fr 1fr 1.2fr auto; gap:8px; align-items:center;';
    const safeName = (name || '').replace(/"/g, '&quot;');
    row.innerHTML = `
        <div><input type="text" class="gdem-item-name" value="${safeName}" placeholder="Mã đèn..." style="width:100%; box-sizing:border-box; background:#1e293b; border:1px solid rgba(255,255,255,0.15); border-radius:6px; padding:6px 8px; color:#fff; font-size:16px;"></div>
        <div style="display:flex; align-items:center; gap:3px;">
            <button type="button" onclick="gdemChangeQty(this, -1)" style="background:#334155; color:#fff; border:none; border-radius:4px; width:26px; height:28px; font-weight:bold; cursor:pointer; font-size:16px;">-</button>
            <input type="number" class="gdem-item-qty" value="${qty}" min="1" max="50" oninput="gdemRecalcTotal()" style="width:36px; text-align:center; background:#1e293b; border:1px solid rgba(255,255,255,0.15); border-radius:6px; padding:4px 0; color:#fff; font-weight:bold; font-size:16px;">
            <button type="button" onclick="gdemChangeQty(this, 1)" style="background:#334155; color:#fff; border:none; border-radius:4px; width:26px; height:28px; font-weight:bold; cursor:pointer; font-size:16px;">+</button>
        </div>
        <div style="position:relative;">
            <input type="number" class="gdem-item-unitprice" value="${unitPriceK}" step="50" min="0" oninput="gdemRecalcTotal()" style="width:100%; box-sizing:border-box; background:#1e293b; border:1px solid rgba(255,255,255,0.15); border-radius:6px; padding:6px 22px 6px 6px; color:#facc15; font-weight:bold; font-size:16px;">
            <span style="position:absolute; right:6px; top:6px; color:#94a3b8; font-size:0.75rem;">k</span>
        </div>
        <div><button type="button" onclick="gdemRemoveItemRow(this)" style="background:#ef4444; color:#fff; border:none; border-radius:6px; width:28px; height:28px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:14px;" title="Xóa món">✕</button></div>`;
    container.appendChild(row);
    gdemRecalcTotal();
}

export function gdemChangeQty(btn, delta) {
    const row = btn.closest('.gdem-item-row');
    if (!row) return;
    const inp = row.querySelector('.gdem-item-qty');
    if (inp) {
        inp.value = Math.max(1, (parseInt(inp.value) || 1) + delta);
        gdemRecalcTotal();
    }
}

export function gdemRemoveItemRow(btn) {
    const row = btn.closest('.gdem-item-row');
    const container = document.getElementById('gdem_items_container');
    if (!container || !row) return;

    if (container.querySelectorAll('.gdem-item-row').length <= 1) {
        const nameInp = row.querySelector('.gdem-item-name');
        const qtyInp = row.querySelector('.gdem-item-qty');
        const priceInp = row.querySelector('.gdem-item-unitprice');
        if (nameInp) nameInp.value = '';
        if (qtyInp) qtyInp.value = 1;
        if (priceInp) priceInp.value = 0;
    } else {
        row.remove();
    }
    gdemRecalcTotal();
}

export function gdemRecalcTotal() {
    let sumBaseK = 0;
    document.querySelectorAll('.gdem-item-row').forEach(row => {
        const qty = Math.max(1, parseInt(row.querySelector('.gdem-item-qty')?.value) || 1);
        const unitK = Math.max(0, parseFloat(row.querySelector('.gdem-item-unitprice')?.value) || 0);
        sumBaseK += (qty * unitK);
    });

    const discInput = document.getElementById('gdem_discount');
    const discK = Math.max(0, parseFloat(discInput?.value) || 0);
    const totalFinalK = Math.max(0, sumBaseK - discK);

    const totEl = document.getElementById('gdem_total_display');
    const baseEl = document.getElementById('gdem_base_display');
    if (totEl) totEl.innerText = (totalFinalK * 1000).toLocaleString('vi-VN') + ' đ';
    if (baseEl) baseEl.innerText = 'Tiền gốc: ' + (sumBaseK * 1000).toLocaleString('vi-VN') + ' đ' + (discK > 0 ? ` (Bớt ${discK}k)` : '');
}

export function gdemGetPayload() {
    const items = [];
    document.querySelectorAll('.gdem-item-row').forEach(row => {
        const name = (row.querySelector('.gdem-item-name')?.value || '').trim() || 'ĐÈN';
        const qty = Math.max(1, parseInt(row.querySelector('.gdem-item-qty')?.value) || 1);
        const unitK = Math.max(0, parseFloat(row.querySelector('.gdem-item-unitprice')?.value) || 0);
        const finalK = unitK * qty;
        items.push({
            product_name: name,
            quantity: qty,
            unit_price_k: unitK,
            final_price_k: finalK,
            base_price_k: finalK
        });
    });

    const discK = Math.max(0, parseFloat(document.getElementById('gdem_discount')?.value) || 0);
    const sumBaseK = items.reduce((s, it) => s + it.final_price_k, 0);
    const totalFinalK = Math.max(0, sumBaseK - discK);
    const sessId = getActiveSessionId() || 'default_user';

    return {
        session_id: sessId,
        cust_name: (document.getElementById('gdem_customer')?.value || '').trim() || 'Khách lẻ',
        customer: (document.getElementById('gdem_customer')?.value || '').trim() || 'Khách lẻ',
        phone: (document.getElementById('gdem_phone')?.value || '').trim(),
        found_car: (document.getElementById('gdem_car')?.value || '').trim().toUpperCase() || 'XE Ô TÔ',
        car: (document.getElementById('gdem_car')?.value || '').trim().toUpperCase() || 'XE Ô TÔ',
        plate: (document.getElementById('gdem_plate')?.value || '').trim().toUpperCase(),
        order_date: document.getElementById('gdem_date')?.value || new Date().toISOString().slice(0, 10),
        discount_k: discK,
        total_base_k: sumBaseK,
        total_final_k: totalFinalK,
        items: items
    };
}

export async function gdemSubmitSaveImmediately() {
    const payload = gdemGetPayload();
    closeGarageDraftEditModal();
    try {
        const res = await fetch('/api/ai/draft/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        appendMessageUI('bot', data.message || '✅ Đã lưu đơn thành công!', true, null, null);
    } catch (err) {
        alert('Lỗi khi lưu đơn: ' + err);
    }
}

export async function gdemSubmitUpdateCard() {
    const payload = gdemGetPayload();
    closeGarageDraftEditModal();
    try {
        const res = await fetch('/api/ai/draft/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        setLastAIMeta(data.meta || payload);
        appendMessageUI('bot', data.message || 'Đã cập nhật thông tin!', true, null, data.buttons);
    } catch (err) {
        alert('Lỗi cập nhật: ' + err);
    }
}
