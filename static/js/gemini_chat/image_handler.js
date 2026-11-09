/**
 * TRẦN BÌNH AUTO - Xử lý hình ảnh & Gemini Vision
 * Tuân thủ ES Modules, Zero Logic Loss, Token Safety (< 200 dòng).
 */

import {
    state,
    setSelectedImage,
    clearSelectedImageState
} from './state.js';

export function handleGeminiImageSelected(event) {
    const file = event.target.files ? event.target.files[0] : null;
    if (!file) return;
    processGeminiImageFile(file);
}

// Nén ảnh thông minh trước khi tải lên (Hỗ trợ 100% iPhone Safari, chống lỗi TypeError Load failed)
export function compressImageFile(file, maxWidth = 1024, maxHeight = 1024, quality = 0.82) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                let w = img.width;
                let h = img.height;
                if (w > maxWidth || h > maxHeight) {
                    if (w / h > maxWidth / maxHeight) {
                        h = Math.round(h * (maxWidth / w));
                        w = maxWidth;
                    } else {
                        w = Math.round(w * (maxHeight / h));
                        h = maxHeight;
                    }
                }
                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, w, h);
                try {
                    const dataUrl = canvas.toDataURL('image/jpeg', quality);
                    resolve(dataUrl);
                } catch (err) {
                    resolve(e.target.result);
                }
            };
            img.onerror = function() {
                resolve(e.target.result);
            };
            img.src = e.target.result;
        };
        reader.onerror = function() {
            resolve(null);
        };
        reader.readAsDataURL(file);
    });
}

export async function processGeminiImageFile(file) {
    const isImg = (!file.type || file.type.startsWith('image/') || /\.(jpg|jpeg|png|heic|heif|webp|bmp)$/i.test(file.name || ''));
    if (!isImg) {
        alert('Vui lòng chọn một tệp hình ảnh hợp lệ!');
        return;
    }

    const fileTimestamp = file.lastModified || Date.now();
    const previewName = document.getElementById('imagePreviewName');
    const previewDate = document.getElementById('imagePreviewDate');
    const previewContainer = document.getElementById('imagePreviewContainer');

    if (previewName) previewName.textContent = file.name || 'Ảnh nghiệm thu xe';
    if (previewDate) previewDate.innerHTML = `<i class="bi bi-arrow-repeat"></i> Đang nén & tối ưu hóa ảnh...`;
    if (previewContainer) previewContainer.style.display = 'flex';

    const compressed = await compressImageFile(file, 1024, 1024, 0.82);
    if (!compressed) {
        alert('Không thể đọc hình ảnh. Vui lòng thử lại!');
        clearSelectedImage();
        return;
    }

    setSelectedImage(compressed, fileTimestamp);

    const previewImg = document.getElementById('imagePreviewImg');
    if (previewImg) previewImg.src = state.selectedImageDataUrl;

    const d = new Date(fileTimestamp);
    const dStr = d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    if (previewDate) {
        previewDate.innerHTML = `<i class="bi bi-clock-history"></i> Thời gian tệp: <strong>${dStr}</strong> • Gemini Vision sẵn sàng`;
    }

    const btnSend = document.getElementById('btnSend');
    if (btnSend) btnSend.disabled = false;

    const inp = document.getElementById('userInput');
    if (inp) inp.focus();
}

export function clearSelectedImage() {
    clearSelectedImageState();

    const previewContainer = document.getElementById('imagePreviewContainer');
    if (previewContainer) previewContainer.style.display = 'none';

    const fileInput = document.getElementById('geminiImageInput');
    if (fileInput) fileInput.value = '';

    const inp = document.getElementById('userInput');
    const btnSend = document.getElementById('btnSend');
    if (btnSend && inp) {
        btnSend.disabled = inp.value.trim().length === 0;
    }
}

// Khởi tạo các sự kiện lắng nghe Clipboard và Drag & Drop
export function initImageEventListeners() {
    if (typeof window === 'undefined') return;

    // Hỗ trợ dán ảnh trực tiếp từ Clipboard (Ctrl + V)
    window.addEventListener('paste', function(e) {
        if (e.clipboardData && e.clipboardData.items) {
            for (let i = 0; i < e.clipboardData.items.length; i++) {
                const item = e.clipboardData.items[i];
                if (item.type && item.type.indexOf('image') !== -1) {
                    const file = item.getAsFile();
                    if (file) {
                        processGeminiImageFile(file);
                        break;
                    }
                }
            }
        }
    });

    // Hỗ trợ kéo thả ảnh vào khung trò chuyện (Drag & Drop)
    window.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    window.addEventListener('drop', function(e) {
        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file && file.type && file.type.startsWith('image/')) {
                e.preventDefault();
                processGeminiImageFile(file);
            }
        }
    });
}
