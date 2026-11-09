/**
 * TRẦN BÌNH AUTO - Nhận diện giọng nói Web Speech API (Tiếng Việt)
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    setRecordingState,
    setRecognitionInstance
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

function updateInputHeight(inp) {
    if (typeof window.handleTextareaInput === 'function') {
        window.handleTextareaInput(inp);
        return;
    }
    if (!inp) return;
    inp.style.height = 'auto';
    const newHeight = Math.min(inp.scrollHeight, 200);
    inp.style.height = newHeight + 'px';
    const btnSend = document.getElementById('btnSend');
    if (btnSend) {
        btnSend.disabled = inp.value.trim().length === 0;
    }
}

function triggerSendMessage() {
    if (typeof window.sendMessage === 'function') {
        window.sendMessage();
    }
}

export function toggleSpeechRecognition() {
    const btnMic = document.getElementById('btnMic');
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRec) {
        alert('Trình duyệt của bạn chưa hỗ trợ nhận diện giọng nói trực tiếp. Vui lòng dùng Chrome hoặc Edge mới nhất!');
        return;
    }

    if (state.isRecording) {
        if (state.recognition) {
            state.recognition.stop();
        }
        return;
    }

    const recognition = new SpeechRec();
    recognition.lang = 'vi-VN';
    recognition.continuous = false;
    recognition.interimResults = false;

    setRecognitionInstance(recognition);

    recognition.onstart = () => {
        setRecordingState(true);
        if (btnMic) {
            btnMic.classList.add('recording');
            btnMic.innerHTML = '<i class="bi bi-stop-circle-fill"></i>';
        }
        notifyToast('🎙️ Đang nghe giọng nói... Mời anh nói lệnh!');
    };

    recognition.onresult = (event) => {
        if (!event.results || !event.results[0] || !event.results[0][0]) return;
        const transcript = event.results[0][0].transcript;
        if (transcript) {
            const inp = document.getElementById('userInput');
            if (inp) {
                inp.value = transcript;
                updateInputHeight(inp);
            }
            notifyToast(`🗣️ Đã nhận: "${transcript}"`);
            setTimeout(() => {
                triggerSendMessage();
            }, 400);
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech error:', event.error);
        notifyToast('⚠️ Không nhận diện được âm thanh hoặc microphone bị chặn.');
    };

    recognition.onend = () => {
        setRecordingState(false);
        if (btnMic) {
            btnMic.classList.remove('recording');
            btnMic.innerHTML = '<i class="bi bi-mic"></i>';
        }
    };

    try {
        recognition.start();
    } catch (e) {
        console.error('Không thể kích hoạt nhận diện giọng nói:', e);
        setRecordingState(false);
        if (btnMic) {
            btnMic.classList.remove('recording');
            btnMic.innerHTML = '<i class="bi bi-mic"></i>';
        }
    }
}
