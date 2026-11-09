/**
 * TRẦN BÌNH AUTO - Quản lý State tập trung & Hằng số cho Gemini Chat
 * Tuân thủ quy chuẩn ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

// ── 1. HẰNG SỐ LƯU TRỮ (STORAGE KEYS) ──
export const SESSIONS_STORAGE_KEY = 'gemini_garage_sessions_v2';
export const ACTIVE_SESSION_ID_KEY = 'gemini_garage_active_session_id';
export const LEGACY_STORAGE_KEY = 'gemini_garage_chat_history';

// ── 2. HẰNG SỐ CẤU HÌNH & HIỂN THỊ MODEL AI ──
export const MODEL_SHORT_NAMES = {
    'gemini-3.8-flash': '⚡ 3.8 Flash',
    'gemini-3.5-flash-lite': '⚡ 3.5 Flash-Lite',
    'gemini-3.5-flash': '🚀 3.5 Flash',
    'gemini-3.7-flash': '🔥 3.7 Flash',
    'gemini-2.5-flash': '⏱️ 2.5 Flash',
    'gemini-2.5-pro': '🧠 2.5 Pro'
};

// ── 3. OBJECT STATE TẬP TRUNG TOÀN HỆ THỐNG ──
export const state = {
    // Phiên trò chuyện hiện tại
    activeSessionId: null,

    // Dữ liệu hình ảnh đính kèm (Vision)
    selectedImageDataUrl: null,
    selectedImageTimestamp: null,

    // Metadata đơn hàng từ phản hồi của Gemini
    lastAIMeta: null,
    currentDraftMeta: null,

    // Nhận diện giọng nói Web Speech API
    recognition: null,
    isRecording: false
};

// ── 4. CÁC HÀM GETTER / SETTER HỖ TRỢ STATE AN TOÀN ──

export function setActiveSessionId(id) {
    state.activeSessionId = id;
    if (id) {
        try {
            localStorage.setItem(ACTIVE_SESSION_ID_KEY, id);
        } catch (e) {
            console.error('Không thể lưu ACTIVE_SESSION_ID vào localStorage:', e);
        }
    }
}

export function getActiveSessionId() {
    if (!state.activeSessionId) {
        try {
            state.activeSessionId = localStorage.getItem(ACTIVE_SESSION_ID_KEY);
        } catch (e) {
            console.error('Không thể đọc ACTIVE_SESSION_ID từ localStorage:', e);
        }
    }
    return state.activeSessionId;
}

export function setSelectedImage(dataUrl, timestamp = null) {
    state.selectedImageDataUrl = dataUrl;
    state.selectedImageTimestamp = timestamp || (dataUrl ? Date.now() : null);
}

export function clearSelectedImageState() {
    state.selectedImageDataUrl = null;
    state.selectedImageTimestamp = null;
}

export function setLastAIMeta(meta) {
    state.lastAIMeta = meta;
    // Đồng bộ với window.lastAIMeta để đảm bảo tương thích ngược nếu có template dùng trực tiếp
    if (typeof window !== 'undefined') {
        window.lastAIMeta = meta;
    }
}

export function setCurrentDraftMeta(meta) {
    state.currentDraftMeta = meta;
    // Đồng bộ với window.currentDraftMeta
    if (typeof window !== 'undefined') {
        window.currentDraftMeta = meta;
    }
}

export function setRecordingState(isRec) {
    state.isRecording = !!isRec;
}

export function setRecognitionInstance(rec) {
    state.recognition = rec;
}
