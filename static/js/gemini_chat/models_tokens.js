/**
 * TRẦN BÌNH AUTO - Quản lý Model & Tài nguyên Token (models_tokens.js)
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import { MODEL_SHORT_NAMES } from './state.js';
import { showToast } from './chat_ui.js';

export function openModelManagerModal() {
    const modal = document.getElementById('modelManagerModal');
    if (modal) modal.style.display = 'flex';
    refreshModelAndUsageStats(true);
}

export function closeModelManagerModal() {
    const modal = document.getElementById('modelManagerModal');
    if (modal) modal.style.display = 'none';
}

export async function refreshModelAndUsageStats(showToastMsg = false) {
    try {
        const [resModels, resUsage] = await Promise.all([
            fetch('/api/ai/models'),
            fetch('/api/ai/usage')
        ]);

        if (resModels.ok) {
            const data = await resModels.json();
            renderModelsList(data);
            updateActiveModelUI(data.active_model);
        }

        if (resUsage.ok) {
            const usage = await resUsage.json();
            renderUsageStats(usage);
        }

        if (showToastMsg) {
            showToast('📊 Đã cập nhật số liệu token & model mới nhất!');
        }
    } catch (err) {
        console.error('Lỗi nạp thông tin model/token:', err);
    }
}

export function updateActiveModelUI(modelId) {
    const label = document.getElementById('activeModelLabel');
    if (!label) return;
    label.innerText = MODEL_SHORT_NAMES[modelId] || modelId;
}

export function renderModelsList(data) {
    const container = document.getElementById('modelsListContainer');
    if (!container || !data || !data.models) return;

    const active = data.active_model || 'gemini-3.5-flash-lite';
    container.innerHTML = data.models.map(m => {
        const isActive = m.id === active;
        const recommendedBadge = m.recommended ? '<span class="badge bg-primary" style="font-size:0.65rem;">Khuyên dùng</span>' : '';
        const activeBadge = isActive ? '<span class="badge bg-success" style="font-size:0.65rem;">● Đang Kích Hoạt</span>' : '';
        const btnClass = isActive ? 'btn-success' : 'btn-outline-primary';
        const btnText = isActive ? 'Đang Dùng' : 'Chọn Model';

        return `
            <div class="model-card-item ${isActive ? 'active' : ''}" onclick="selectGeminiModel('${m.id}')">
                <div style="flex:1;">
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <span style="font-weight:700; color:#fff; font-size:0.95rem;">${m.name}</span>
                        ${recommendedBadge}
                        ${activeBadge}
                    </div>
                    <div style="font-size:0.75rem; color:var(--text-secondary); line-height:1.4;">${m.desc}</div>
                    <div class="d-flex gap-3 mt-2" style="font-size:0.7rem; color:var(--text-muted);">
                        <span>Tốc độ: <strong class="text-white">${m.speed}</strong></span>
                        <span>Chi phí token: <strong class="text-white">${m.cost}</strong></span>
                    </div>
                </div>
                <div>
                    <button class="btn btn-sm ${btnClass} rounded-pill px-3" style="font-size:0.75rem; font-weight:600;" onclick="event.stopPropagation(); selectGeminiModel('${m.id}')">
                        ${btnText}
                    </button>
                </div>
            </div>`;
    }).join('');
}

export function renderUsageStats(usage) {
    if (!usage) return;
    const badge = document.getElementById('tokenCountBadge');
    if (badge) {
        const tot = usage.today_tokens || 0;
        badge.innerText = tot > 1000 ? (tot / 1000).toFixed(1) + 'k tokens' : tot + ' tokens';
    }

    const elTodayTok = document.getElementById('statTodayTokens');
    if (elTodayTok) elTodayTok.innerText = (usage.today_tokens || 0).toLocaleString();

    const elTodayReqs = document.getElementById('statTodayReqs');
    if (elTodayReqs) elTodayReqs.innerText = (usage.today_requests || 0) + ' lệnh';

    const elTotTok = document.getElementById('statTotalTokens');
    if (elTotTok) elTotTok.innerText = (usage.total_tokens || 0).toLocaleString();

    const elTotReqs = document.getElementById('statTotalReqs');
    if (elTotReqs) elTotReqs.innerText = (usage.total_requests || 0) + ' lượt gọi';

    const elRatio = document.getElementById('statRatioTokens');
    if (elRatio) {
        const p = usage.prompt_tokens || 0;
        const r = usage.response_tokens || 0;
        const pStr = p > 1000 ? (p / 1000).toFixed(1) + 'k' : p;
        const rStr = r > 1000 ? (r / 1000).toFixed(1) + 'k' : r;
        elRatio.innerText = `${pStr} / ${rStr}`;
    }

    const elLocal = document.getElementById('statLocalSaved');
    if (elLocal) elLocal.innerText = (usage.saved_local_requests || 0) + ' lượt';

    const lastBox = document.getElementById('lastCallBox');
    if (lastBox && usage.last_call && usage.last_call.time) {
        const lc = usage.last_call;
        lastBox.innerHTML = `
            ⚡ <strong>Lượt gọi gần nhất:</strong> ${lc.time} | <strong>Model:</strong> <code>${lc.model}</code> | <strong>Đầu vào:</strong> ${lc.prompt_tokens} tok | <strong>Phản hồi:</strong> ${lc.response_tokens} tok (<strong>Tổng:</strong> ${lc.total_tokens} tokens)`;
    }
}

export async function selectGeminiModel(modelId) {
    try {
        const res = await fetch('/api/ai/models/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelId })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✨ ${data.message}`);
            refreshModelAndUsageStats();
        } else {
            alert('Lỗi: ' + data.message);
        }
    } catch (err) {
        alert('Lỗi kết nối khi đổi model: ' + err);
    }
}

export async function resetTokenCounter() {
    if (!confirm('Anh có chắc muốn đặt lại bộ đếm token về 0? (Dữ liệu lịch sử trò chuyện vẫn được giữ nguyên)')) return;
    try {
        const res = await fetch('/api/ai/usage/reset', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('🧹 Đã đặt lại bộ đếm token về 0!');
            refreshModelAndUsageStats();
        }
    } catch (err) {
        alert('Lỗi reset token: ' + err);
    }
}
