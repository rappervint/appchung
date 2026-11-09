/**
 * TRẦN BÌNH AUTO - Entry Point & Window Bridge cho Gemini Chat (main.js)
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    SESSIONS_STORAGE_KEY,
    ACTIVE_SESSION_ID_KEY,
    LEGACY_STORAGE_KEY,
    MODEL_SHORT_NAMES,
    setActiveSessionId,
    getActiveSessionId,
    setSelectedImage,
    clearSelectedImageState,
    setLastAIMeta,
    setCurrentDraftMeta
} from './state.js';

import {
    getAllSessions,
    saveSessions,
    getActiveSession,
    renderSidebarSessionsList,
    switchSession,
    createNewChatSession,
    startNewChat,
    deleteChatSession,
    clearAllChatSessions,
    toggleSidebar
} from './sessions.js';

import {
    handleGeminiImageSelected,
    compressImageFile,
    processGeminiImageFile,
    clearSelectedImage,
    initImageEventListeners
} from './image_handler.js';

import {
    toggleSpeechRecognition
} from './speech.js';

import {
    showToast,
    handleTextareaInput,
    handleTextareaKeydown,
    useSuggestion,
    sendQuickMessage,
    appendMessageUI,
    fetchWithAutoRetry,
    sendMessage
} from './chat_ui.js';

import {
    openModelManagerModal,
    closeModelManagerModal,
    refreshModelAndUsageStats,
    updateActiveModelUI,
    renderModelsList,
    renderUsageStats,
    selectGeminiModel,
    resetTokenCounter
} from './models_tokens.js';

import {
    openGarageDraftEditModal,
    closeGarageDraftEditModal,
    gdemAddItemRow,
    gdemChangeQty,
    gdemRemoveItemRow,
    gdemRecalcTotal,
    gdemGetPayload,
    gdemSubmitSaveImmediately,
    gdemSubmitUpdateCard
} from './draft_modal.js';

// ── CẦU NỐI WINDOW (WINDOW BRIDGE) CHO TƯƠNG THÍCH INLINE ONCLICK ──
if (typeof window !== 'undefined') {
    // State & Storage
    window.geminiChatState = state;
    window.SESSIONS_STORAGE_KEY = SESSIONS_STORAGE_KEY;
    window.ACTIVE_SESSION_ID_KEY = ACTIVE_SESSION_ID_KEY;
    window.LEGACY_STORAGE_KEY = LEGACY_STORAGE_KEY;
    window.MODEL_SHORT_NAMES = MODEL_SHORT_NAMES;

    // Sessions
    window.getAllSessions = getAllSessions;
    window.saveSessions = saveSessions;
    window.getActiveSession = getActiveSession;
    window.renderSidebarSessionsList = renderSidebarSessionsList;
    window.switchSession = switchSession;
    window.createNewChatSession = createNewChatSession;
    window.startNewChat = startNewChat;
    window.deleteChatSession = deleteChatSession;
    window.clearAllChatSessions = clearAllChatSessions;
    window.toggleSidebar = toggleSidebar;

    // Image & Vision
    window.handleGeminiImageSelected = handleGeminiImageSelected;
    window.compressImageFile = compressImageFile;
    window.processGeminiImageFile = processGeminiImageFile;
    window.clearSelectedImage = clearSelectedImage;

    // Voice & Speech
    window.toggleSpeechRecognition = toggleSpeechRecognition;

    // Chat UI & Messaging
    window.showToast = showToast;
    window.handleTextareaInput = handleTextareaInput;
    window.handleTextareaKeydown = handleTextareaKeydown;
    window.useSuggestion = useSuggestion;
    window.sendQuickMessage = sendQuickMessage;
    window.appendMessageUI = appendMessageUI;
    window.fetchWithAutoRetry = fetchWithAutoRetry;
    window.sendMessage = sendMessage;

    // Models & Tokens
    window.openModelManagerModal = openModelManagerModal;
    window.closeModelManagerModal = closeModelManagerModal;
    window.refreshModelAndUsageStats = refreshModelAndUsageStats;
    window.updateActiveModelUI = updateActiveModelUI;
    window.renderModelsList = renderModelsList;
    window.renderUsageStats = renderUsageStats;
    window.selectGeminiModel = selectGeminiModel;
    window.resetTokenCounter = resetTokenCounter;

    // Draft Invoice Modal
    window.openGarageDraftEditModal = openGarageDraftEditModal;
    window.closeGarageDraftEditModal = closeGarageDraftEditModal;
    window.gdemAddItemRow = gdemAddItemRow;
    window.gdemChangeQty = gdemChangeQty;
    window.gdemRemoveItemRow = gdemRemoveItemRow;
    window.gdemRecalcTotal = gdemRecalcTotal;
    window.gdemGetPayload = gdemGetPayload;
    window.gdemSubmitSaveImmediately = gdemSubmitSaveImmediately;
    window.gdemSubmitUpdateCard = gdemSubmitUpdateCard;
}

// ── KHỞI CHẠY HỆ THỐNG KHI TẢI XONG TRANG ──
function initApp() {
    if (typeof marked !== 'undefined' && marked.setOptions) {
        marked.setOptions({
            breaks: true,
            gfm: true
        });
    }

    initImageEventListeners();

    const sess = getActiveSession();
    renderSidebarSessionsList();
    if (sess && sess.id) {
        switchSession(sess.id);
    }
    refreshModelAndUsageStats(false);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
