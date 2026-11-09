/**
 * TRẦN BÌNH AUTO - Quản lý Phiên trò chuyện (Sessions) cho Gemini Chat
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    SESSIONS_STORAGE_KEY,
    ACTIVE_SESSION_ID_KEY,
    LEGACY_STORAGE_KEY,
    setActiveSessionId,
    getActiveSessionId
} from './state.js';

function notifyToast(msg) {
    if (typeof window.showToast === 'function') {
        window.showToast(msg);
        return;
    }
    const toast = document.getElementById('geminiToast');
    if (toast) {
        toast.innerText = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }
}

function renderMessageItem(role, content, shouldScroll = false) {
    if (typeof window.appendMessageUI === 'function') {
        window.appendMessageUI(role, content, shouldScroll);
    }
}

export function getAllSessions() {
    try {
        const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
        if (raw) {
            const list = JSON.parse(raw);
            if (Array.isArray(list)) return list;
        } else {
            const oldRaw = localStorage.getItem(LEGACY_STORAGE_KEY);
            if (oldRaw) {
                const oldList = JSON.parse(oldRaw);
                if (Array.isArray(oldList) && oldList.length > 0) {
                    const firstUserMsg = oldList.find(m => m.role === 'user');
                    const title = firstUserMsg ? (firstUserMsg.content.substring(0, 34) + '...') : 'Cuộc trò chuyện trước';
                    const migratedSess = { id: 'legacy_sess_1', title: title, createdAt: Date.now() - 3600000, updatedAt: Date.now(), messages: oldList };
                    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify([migratedSess]));
                    return [migratedSess];
                }
            }
        }
    } catch (e) {
        console.error('Lỗi đọc sessions:', e);
    }
    return [];
}

export function saveSessions(sessions) {
    try {
        localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
    } catch (e) {}
}

export function getActiveSession() {
    const sessions = getAllSessions();
    let currentId = getActiveSessionId();
    let sess = sessions.find(s => s.id === currentId);
    if (!sess) {
        if (sessions.length > 0) {
            sess = sessions[0];
            setActiveSessionId(sess.id);
        } else {
            sess = createNewChatSession(false);
        }
    }
    return sess;
}

export function renderSidebarSessionsList() {
    const container = document.getElementById('sidebarSessionsList');
    const countLabel = document.getElementById('sessionsCountLabel');
    if (!container) return;

    const sessions = getAllSessions();
    if (countLabel) countLabel.innerText = `${sessions.length} cuộc trò chuyện`;

    if (sessions.length === 0) {
        container.innerHTML = `<div class="text-center py-4 text-muted" style="font-size:0.78rem;">Chưa có cuộc trò chuyện nào</div>`;
        return;
    }

    const currentId = getActiveSessionId();
    container.innerHTML = sessions.map(s => {
        const isActive = s.id === currentId;
        const d = new Date(s.updatedAt || s.createdAt || Date.now());
        const timeStr = d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
        const safeTitle = (s.title || 'Cuộc trò chuyện').replace(/"/g, '&quot;');
        return `
            <div class="session-item ${isActive ? 'active' : ''}" onclick="switchSession('${s.id}')">
                <div class="session-item-title" title="${safeTitle}"><i class="bi bi-chat-left-text" style="font-size:0.85rem; color:${isActive ? '#8ab4f8' : 'var(--text-muted)'};"></i><span>${s.title || 'Cuộc trò chuyện'}</span></div>
                <span class="session-item-time">${timeStr}</span>
                <button class="session-item-del" onclick="event.stopPropagation(); deleteChatSession('${s.id}')" title="Xóa cuộc trò chuyện này"><i class="bi bi-trash"></i></button>
            </div>`;
    }).join('');
}

export function switchSession(sessionId) {
    setActiveSessionId(sessionId);
    const sessions = getAllSessions();
    const sess = sessions.find(s => s.id === sessionId);

    const msgList = document.getElementById('messagesList');
    if (msgList) msgList.innerHTML = '';

    const welcome = document.getElementById('welcomeSection');
    if (sess && Array.isArray(sess.messages) && sess.messages.length > 0) {
        if (welcome) welcome.style.display = 'none';
        sess.messages.forEach(msg => renderMessageItem(msg.role, msg.content, false));
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    } else {
        if (welcome) welcome.style.display = 'block';
    }

    renderSidebarSessionsList();
    if (window.innerWidth <= 768) toggleSidebar(false);
    const inp = document.getElementById('userInput');
    if (inp) inp.focus();
}

export function createNewChatSession(shouldSwitch = true) {
    const sid = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    const newSess = { id: sid, title: 'Cuộc trò chuyện mới', createdAt: Date.now(), updatedAt: Date.now(), messages: [] };

    const sessions = getAllSessions();
    sessions.unshift(newSess);
    saveSessions(sessions);

    if (shouldSwitch) {
        switchSession(sid);
        notifyToast('✨ Đã tạo cuộc trò chuyện mới!');
    }
    return newSess;
}

export function startNewChat() {
    createNewChatSession(true);
}

export function deleteChatSession(sessionId) {
    if (!confirm('Xóa cuộc trò chuyện này?')) return;
    let sessions = getAllSessions();
    sessions = sessions.filter(s => s.id !== sessionId);
    saveSessions(sessions);

    if (getActiveSessionId() === sessionId) {
        if (sessions.length > 0) {
            switchSession(sessions[0].id);
        } else {
            createNewChatSession(true);
        }
    } else {
        renderSidebarSessionsList();
    }
    notifyToast('🗑️ Đã xóa cuộc trò chuyện!');
}

export function clearAllChatSessions() {
    if (!confirm('Anh có chắc muốn xóa TOÀN BỘ lịch sử các cuộc trò chuyện không?')) return;
    localStorage.removeItem(SESSIONS_STORAGE_KEY);
    localStorage.removeItem(ACTIVE_SESSION_ID_KEY);
    setActiveSessionId(null);
    createNewChatSession(true);
    notifyToast('🧹 Đã xóa toàn bộ lịch sử trò chuyện!');
}

export function toggleSidebar(forceState = null) {
    const sb = document.getElementById('geminiSidebar');
    const bd = document.getElementById('sidebarBackdrop');
    if (!sb) return;

    if (forceState === false) {
        sb.classList.add('collapsed');
        if (bd) bd.classList.remove('show');
    } else if (forceState === true) {
        sb.classList.remove('collapsed');
        if (bd && window.innerWidth <= 768) bd.classList.add('show');
    } else {
        sb.classList.toggle('collapsed');
        if (bd && window.innerWidth <= 768) bd.classList.toggle('show', !sb.classList.contains('collapsed'));
    }
}

if (typeof window !== 'undefined') {
    window.addEventListener('storage', (e) => {
        if (e.key === SESSIONS_STORAGE_KEY) renderSidebarSessionsList();
    });
}
