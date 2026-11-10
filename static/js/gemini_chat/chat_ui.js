/**
 * TRẦN BÌNH AUTO - Giao diện Chat, Render tin nhắn & Gửi nhận tin (chat_ui.js)
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    setLastAIMeta,
    getActiveSessionId,
    setActiveSessionId
} from './state.js';
import {
    getAllSessions,
    saveSessions,
    createNewChatSession,
    renderSidebarSessionsList
} from './sessions.js';
import { clearSelectedImage } from './image_handler.js';

export function showToast(msg) {
    const toast = document.getElementById('geminiToast');
    if (!toast) return;
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => { toast.classList.remove('show'); }, 3000);
}

export function handleTextareaInput(textarea) {
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    const btnSend = document.getElementById('btnSend');
    if (btnSend) {
        btnSend.disabled = textarea.value.trim().length === 0 && !state.selectedImageDataUrl;
    }
}

export function handleTextareaKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

export function useSuggestion(promptText) {
    const inp = document.getElementById('userInput');
    if (!inp) return;
    inp.value = promptText;
    handleTextareaInput(inp);
    sendMessage();
}

export function sendQuickMessage(text) {
    const inp = document.getElementById('userInput');
    if (inp) inp.value = text;
    sendMessage();
}

export function appendMessageUI(role, content, shouldScroll = true, imageBase64 = null, buttons = null) {
    const welcome = document.getElementById('welcomeSection');
    if (welcome) welcome.style.display = 'none';
    const list = document.getElementById('messagesList');
    if (!list) return;

    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    if (role === 'user') {
        const imgHtml = imageBase64 ? `<div style="margin-bottom:8px;"><img src="${imageBase64}" style="max-width:280px; max-height:200px; border-radius:10px; object-fit:cover; border:1px solid rgba(255,255,255,0.25); box-shadow:0 4px 14px rgba(0,0,0,0.4);"></div>` : '';
        row.innerHTML = `
            <div class="msg-content-wrapper"><div class="msg-bubble-user">${imgHtml}${content ? `<div>${content}</div>` : ''}</div></div>
            <div class="msg-avatar avatar-user"><i class="bi bi-person-fill"></i></div>`;
    } else {
        const parsedHTML = (typeof marked !== 'undefined' && marked.parse) ? marked.parse(content) : content;
        let btnHtml = '';
        if (buttons && buttons.length > 0) {
            btnHtml = '<div class="d-flex flex-wrap gap-2 mt-3">';
            buttons.forEach(b => {
                let btnClass = 'btn-success', icon = 'bi-check-circle-fill', onclickCall = `sendQuickMessage('${b.value}')`;
                if (b.class === 'btn-danger') {
                    btnClass = 'btn-danger'; icon = 'bi-x-circle-fill';
                } else if (b.action === 'open_thuchi_modal') {
                    btnClass = 'btn-warning text-dark'; icon = 'bi-pencil-square'; onclickCall = `openThuchiDraftEditModal()`;
                } else if (b.class === 'btn-warning' || b.action === 'open_edit_modal') {
                    const isThuchi = state.lastAIMeta && (state.lastAIMeta.action_type === 'thuchi' || state.lastAIMeta.trans_type);
                    btnClass = 'btn-warning text-dark'; icon = 'bi-pencil-square'; onclickCall = isThuchi ? `openThuchiDraftEditModal()` : `openGarageDraftEditModal()`;
                }
                btnHtml += `<button class="btn btn-sm ${btnClass} px-3 py-1 font-weight-bold d-flex align-items-center gap-1" style="border-radius:20px; font-size:0.88rem; box-shadow:0 2px 6px rgba(0,0,0,0.3);" onclick="${onclickCall}"><i class="bi ${icon}"></i> ${b.text}</button>`;
            });
            btnHtml += '</div>';
        }
        row.innerHTML = `
            <div class="msg-avatar avatar-gemini"><i class="bi bi-stars"></i></div>
            <div class="msg-content-wrapper"><div class="msg-bubble-bot">${parsedHTML}${btnHtml}</div></div>`;
    }

    list.appendChild(row);
    if (shouldScroll) {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }
}

export async function fetchWithAutoRetry(url, options, maxRetries = 2) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fetch(url, options);
        } catch (err) {
            if (attempt === maxRetries) throw err;
            await new Promise(r => setTimeout(r, 150));
        }
    }
}

export async function sendMessage() {
    const input = document.getElementById('userInput');
    const btnSend = document.getElementById('btnSend');
    const text = input ? input.value.trim() : '';
    const hasImage = !!state.selectedImageDataUrl;
    if (!text && !hasImage) return;

    const imgToSend = state.selectedImageDataUrl;
    const tsToSend = state.selectedImageTimestamp;
    clearSelectedImage();
    appendMessageUI('user', text, true, imgToSend);

    const sessions = getAllSessions();
    let currentSess = sessions.find(s => s.id === getActiveSessionId());
    if (!currentSess) {
        currentSess = createNewChatSession(false);
        setActiveSessionId(currentSess.id);
    }

    if (currentSess.messages.length === 0 || currentSess.title === 'Cuộc trò chuyện mới') {
        currentSess.title = text ? (text.length > 34 ? text.substring(0, 34) + '...' : text) : 'Ảnh nghiệm thu xe';
    }

    const d = new Date();
    const timeStr = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    currentSess.messages.push({ role: 'user', content: text, image: !!imgToSend, time: timeStr });
    currentSess.updatedAt = Date.now();

    const filtered = sessions.filter(s => s.id !== currentSess.id);
    filtered.unshift(currentSess);
    saveSessions(filtered);
    renderSidebarSessionsList();

    if (input) { input.value = ''; handleTextareaInput(input); }
    if (btnSend) btnSend.disabled = true;

    const list = document.getElementById('messagesList');
    const thinkingRow = document.createElement('div');
    thinkingRow.className = 'msg-row bot';
    thinkingRow.id = 'thinkingIndicator';
    const thinkingMsg = imgToSend ? 'Gemini Vision đang thẩm định ảnh, đọc biển số xe & tra cứu giá...' : 'Gemini đang suy nghĩ & tra cứu dữ liệu gara...';
    thinkingRow.innerHTML = `
        <div class="msg-avatar avatar-gemini"><i class="bi bi-stars"></i></div>
        <div class="msg-content-wrapper"><div class="gemini-thinking"><i class="bi bi-stars thinking-sparkle"></i><span>${thinkingMsg}</span></div></div>`;
    if (list) list.appendChild(thinkingRow);
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });

    try {
        const res = await fetchWithAutoRetry('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, image: imgToSend, file_timestamp: tsToSend, session_id: getActiveSessionId() })
        });

        const data = await res.json();
        const thinkingEl = document.getElementById('thinkingIndicator');
        if (thinkingEl) thinkingEl.remove();

        if (data.meta) setLastAIMeta(data.meta);
        const botReply = data.message || 'Dạ em đã hoàn thành yêu cầu của anh!';
        appendMessageUI('bot', botReply, true, null, data.buttons);

        currentSess.messages.push({ role: 'bot', content: botReply, time: timeStr, usage: data.usage });
        currentSess.updatedAt = Date.now();
        saveSessions(filtered);
        renderSidebarSessionsList();

        if (typeof window.refreshModelAndUsageStats === 'function') {
            window.refreshModelAndUsageStats();
        }
    } catch (err) {
        const thinkingEl = document.getElementById('thinkingIndicator');
        if (thinkingEl) thinkingEl.remove();

        const isNetErr = (err + '').toLowerCase().includes('load failed') || (err + '').toLowerCase().includes('failed to fetch');
        let errMsg = '⚠️ Gặp lỗi kết nối tới máy chủ AI: ' + (err.message || err) + '\nAnh vui lòng thử lại nhé!';
        if (isNetErr) {
            errMsg = '❌ **MẤT KẾT NỐI TỚI MÁY CHỦ GARA!**\n\n• Vui lòng kiểm tra thiết bị đã kết nối đúng vào **Wi-Fi của Gara** chưa nhé (nếu máy đang bật mạng di động 4G/5G sẽ không vào được appchung.local).\n• Sau khi bật lại Wi-Fi, anh hãy thử gửi lại tin nhắn nhé!';
        }
        appendMessageUI('bot', errMsg);
    } finally {
        if (input) input.focus();
    }
}
