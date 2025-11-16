// SYNTHWAVE TERMINAL 2085 - NEURAL INTERFACE SYSTEM
const API_BASE_URL = "http://127.0.0.1:8000";

// DOM Elements
const sessionIdEl = document.getElementById('session-id');
const chatHistoryEl = document.getElementById('chat-history');
const questionInput = document.getElementById('question-input');
const sendBtn = document.getElementById('send-btn');
const clearSessionBtn = document.getElementById('clear-session-btn');
const fileInput = document.getElementById('file-input');
const uploadArea = document.getElementById('upload-area');
const uploadBtn = document.getElementById('upload-btn');
const fileListEl = document.getElementById('file-list');
const fileCountEl = document.getElementById('file-count');
const errorToastContainer = document.getElementById('error-toast-container');
const currentTimeEl = document.getElementById('current-time');

// State Management
let currentSessionId = null;
let selectedFiles = [];
const MAX_FILES_PER_SESSION = 5;

// === SYNTHWAVE EFFECTS ===
function initSynthwaveEffects() {
    // Update clock
    setInterval(() => {
        const now = new Date();
        currentTimeEl.textContent = now.toLocaleTimeString('en-US', { 
            hour12: false, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
    }, 1000);

    // Add typing effect to messages
    document.addEventListener('DOMContentLoaded', () => {
        typeWriterEffect('INITIALIZING NEURAL INTERFACE...', 'system');
    });

    // Add hover sound effects (visual feedback instead of actual sound)
    document.querySelectorAll('.neon-button, .send-button').forEach(button => {
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'scale(1.02)';
        });
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1)';
        });
    });
}

// === UTILITY FUNCTIONS ===
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.innerHTML = `<span>${message}</span>`;
    errorToastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toast-slide-out 0.5s ease';
        setTimeout(() => toast.remove(), 500);
    }, 5000);
}

function scrollToBottom() {
    setTimeout(() => {
        chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    }, 100);
}

function typeWriterEffect(text, type, callback) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${type}-message`;

    let prefix = '';
    if (type === 'user') {
        prefix = '[USER] ';
    } else if (type === 'assistant') {
        prefix = '[NEURAL-NET] ';
    } else if (type === 'system') {
        prefix = '[SYSTEM] ';
    }

    messageEl.innerHTML = prefix;
    chatHistoryEl.appendChild(messageEl);

    let index = 0;
    const typingSpeed = 30; // Faster typing for that retro feel

    function typeChar() {
        if (index < text.length) {
            messageEl.innerHTML = prefix + text.substring(0, index + 1) + 
                '<span class="terminal-cursor"></span>';
            index++;
            setTimeout(typeChar, typingSpeed);
            scrollToBottom();
        } else {
            messageEl.innerHTML = prefix + text;
            if (callback) callback();
        }
    }

    typeChar();
}

function renderMessage(type, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${type}-message`;

    let prefix = '';
    if (type === 'user') {
        prefix = '[USER] ';
    } else if (type === 'assistant') {
        prefix = '[NEURAL-NET] ';
    } else if (type === 'system') {
        prefix = '[SYSTEM] ';
    }

    // Add glitch effect randomly to system messages
    if (type === 'system' && Math.random() > 0.7) {
        messageEl.classList.add('glitch');
        messageEl.setAttribute('data-text', prefix + content);
    }

    const formattedContent = content.replace(/\n/g, '<br>');
    messageEl.innerHTML = prefix + formattedContent;
    chatHistoryEl.appendChild(messageEl);
    scrollToBottom();

    // Add fade-in effect
    messageEl.style.animation = 'message-appear 0.5s ease';
}

function updateFileList() {
    fileListEl.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.style.animationDelay = `${index * 0.1}s`;

        const nameEl = document.createElement('span');
        nameEl.className = 'file-name';
        nameEl.textContent = file.name;

        const statusEl = document.createElement('span');
        statusEl.className = 'file-status status-pending';
        statusEl.textContent = 'READY';
        file.statusEl = statusEl;

        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '✖';
        removeBtn.className = 'neon-button';
        removeBtn.style.width = '30px';
        removeBtn.style.height = '30px';
        removeBtn.style.padding = '0';
        removeBtn.style.fontSize = '1.2em';
        removeBtn.style.marginBottom = '0';
        removeBtn.onclick = () => removeFile(index);

        item.appendChild(nameEl);
        item.appendChild(statusEl);
        item.appendChild(removeBtn);
        fileListEl.appendChild(item);
    });

    fileCountEl.textContent = `${selectedFiles.length}/${MAX_FILES_PER_SESSION}`;
    uploadBtn.disabled = selectedFiles.length === 0;
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();

    if (selectedFiles.length === 0) {
        renderMessage('system', 'Data buffer cleared.');
    }
}

// === API CALLS ===
async function getNewSession() {
    try {
        renderMessage('system', 'ESTABLISHING QUANTUM LINK...');

        const response = await fetch(`${API_BASE_URL}/session`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        currentSessionId = data.session_id;
        sessionIdEl.textContent = currentSessionId.toUpperCase();
        questionInput.disabled = false;
        sendBtn.disabled = false;

        setTimeout(() => {
            renderMessage('system', `✓ NEURAL LINK ESTABLISHED`);
            renderMessage('system', `SESSION ID: ${currentSessionId.toUpperCase()}`);
        }, 500);

    } catch (error) {
        console.error('Error getting new session:', error);
        showToast(`CONNECTION FAILED: ${error.message}`);
        renderMessage('system', '✗ UNABLE TO ESTABLISH NEURAL LINK');
        questionInput.disabled = true;
        sendBtn.disabled = true;
    }
}

async function handleUploadFiles() {
    if (selectedFiles.length === 0) return;

    uploadBtn.disabled = true;
    questionInput.disabled = true;
    sendBtn.disabled = true;

    renderMessage('system', `UPLOADING ${selectedFiles.length} FILE(S) TO NEURAL MATRIX...`);

    const formData = new FormData();
    formData.append('session_id', currentSessionId);

    selectedFiles.forEach(file => {
        formData.append('files', file, file.name);
        file.statusEl.textContent = 'UPLOADING';
        file.statusEl.className = 'file-status status-pending';
    });

    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update file status
        selectedFiles.forEach((file, index) => {
            if (index < data.success_count) {
                file.statusEl.textContent = 'INTEGRATED';
                file.statusEl.className = 'file-status status-success';
            }
        });

        if (data.success_count > 0) {
            renderMessage('system', `✓ ${data.success_count} FILE(S) INTEGRATED INTO NEURAL MATRIX`);
        }

        if (data.errors.length > 0) {
            data.errors.forEach(err => {
                renderMessage('system', `⚠ ERROR: ${err}`);
            });
            showToast(`UPLOAD COMPLETED WITH ${data.errors.length} ERROR(S)`);
        }

        // Clear files after successful upload
        setTimeout(() => {
            selectedFiles = [];
            updateFileList();
        }, 2000);

    } catch (error) {
        console.error('Error during upload:', error);
        showToast(`UPLOAD FAILED: ${error.message}`);
        renderMessage('system', `✗ NEURAL INTEGRATION FAILED: ${error.message}`);

        selectedFiles.forEach(file => {
            file.statusEl.textContent = 'FAILED';
            file.statusEl.className = 'file-status status-error';
        });

    } finally {
        uploadBtn.disabled = false;
        questionInput.disabled = false;
        sendBtn.disabled = false;
    }
}

async function handleSendQuestion(question) {
    if (!question.trim()) return;

    questionInput.disabled = true;
    sendBtn.disabled = true;

    renderMessage('user', question);
    questionInput.value = '';

    // Add thinking animation
    const thinkingEl = document.createElement('div');
    thinkingEl.className = 'chat-message assistant-message';
    thinkingEl.innerHTML = '[NEURAL-NET] PROCESSING<span class="thinking-dots"></span>';
    chatHistoryEl.appendChild(thinkingEl);
    scrollToBottom();

    // Animate dots
    let dots = 0;
    const dotsInterval = setInterval(() => {
        dots = (dots + 1) % 4;
        thinkingEl.querySelector('.thinking-dots').textContent = '.'.repeat(dots);
    }, 500);

    try {
        const response = await fetch(`${API_BASE_URL}/question`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                session_id: currentSessionId,
            }),
        });

        clearInterval(dotsInterval);
        thinkingEl.remove();

        if (response.status === 400) {
            const errorData = await response.json();
            renderMessage('system', `✗ VALIDATION ERROR: ${errorData.detail}`);
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderMessage('assistant', data.answer);

    } catch (error) {
        clearInterval(dotsInterval);
        thinkingEl.remove();

        console.error('Error during question:', error);
        showToast(`TRANSMISSION FAILED: ${error.message}`);
        renderMessage('assistant', '✗ NEURAL PROCESSING ERROR. PLEASE RETRY TRANSMISSION.');

    } finally {
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

async function handleClearSession() {
    if (!currentSessionId) {
        chatHistoryEl.innerHTML = '';
        await getNewSession();
        return;
    }

    clearSessionBtn.disabled = true;
    questionInput.disabled = true;
    sendBtn.disabled = true;

    renderMessage('system', 'INITIATING SYSTEM RESET...');

    try {
        const response = await fetch(`${API_BASE_URL}/clear`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: currentSessionId,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        renderMessage('system', `✓ NEURAL MATRIX CLEARED: ${data.deleted_count} FILE(S) PURGED`);

        setTimeout(() => {
            chatHistoryEl.innerHTML = '';
            getNewSession();
        }, 1500);

    } catch (error) {
        console.error('Error during clear session:', error);
        showToast(`RESET FAILED: ${error.message}`);
        renderMessage('system', `✗ SYSTEM RESET ERROR: ${error.message}`);
        await getNewSession();

    } finally {
        clearSessionBtn.disabled = false;
        questionInput.disabled = false;
        sendBtn.disabled = false;
    }
}

// === EVENT LISTENERS ===
fileInput.addEventListener('change', (event) => {
    const newFiles = Array.from(event.target.files);
    const validFiles = newFiles.filter(file => file.name.endsWith('.txt'));
    const invalidFiles = newFiles.filter(file => !file.name.endsWith('.txt'));

    if (invalidFiles.length > 0) {
        showToast(`REJECTED ${invalidFiles.length} NON-.TXT FILE(S)`);
    }

    const remainingSlots = MAX_FILES_PER_SESSION - selectedFiles.length;
    const filesToAdd = validFiles.slice(0, remainingSlots);

    if (validFiles.length > remainingSlots) {
        showToast(`BUFFER LIMIT: ONLY ${remainingSlots} FILE(S) ADDED`);
    }

    selectedFiles.push(...filesToAdd);
    updateFileList();
    fileInput.value = '';
});

// Drag and Drop
uploadArea.addEventListener('dragover', (event) => {
    event.preventDefault();
    uploadArea.style.borderColor = 'var(--neon-cyan)';
    uploadArea.style.boxShadow = '0 0 30px var(--neon-cyan)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '';
    uploadArea.style.boxShadow = '';
});

uploadArea.addEventListener('drop', (event) => {
    event.preventDefault();
    uploadArea.style.borderColor = '';
    uploadArea.style.boxShadow = '';

    const newFiles = Array.from(event.dataTransfer.files);
    const validFiles = newFiles.filter(file => file.name.endsWith('.txt'));
    const invalidFiles = newFiles.filter(file => !file.name.endsWith('.txt'));

    if (invalidFiles.length > 0) {
        showToast(`REJECTED ${invalidFiles.length} NON-.TXT FILE(S)`);
    }

    const remainingSlots = MAX_FILES_PER_SESSION - selectedFiles.length;
    const filesToAdd = validFiles.slice(0, remainingSlots);

    if (validFiles.length > remainingSlots) {
        showToast(`BUFFER LIMIT: ONLY ${remainingSlots} FILE(S) ADDED`);
    }

    selectedFiles.push(...filesToAdd);
    updateFileList();
});

// Click on upload area to trigger file input
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Button event listeners
uploadBtn.addEventListener('click', handleUploadFiles);

sendBtn.addEventListener('click', () => {
    handleSendQuestion(questionInput.value);
});

questionInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        handleSendQuestion(questionInput.value);
    }
});

clearSessionBtn.addEventListener('click', handleClearSession);

// === INITIALIZATION ===
document.addEventListener('DOMContentLoaded', () => {
    initSynthwaveEffects();
    getNewSession();
});

// Add CSS for thinking dots animation
const style = document.createElement('style');
style.textContent = `
    .thinking-dots {
        display: inline-block;
        width: 30px;
        text-align: left;
    }
`;
document.head.appendChild(style);