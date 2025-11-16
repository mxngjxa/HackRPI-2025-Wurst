// Frontend logic for the Time Console RAG Terminal

const API_BASE_URL = "http://127.0.0.1:8000"; // Default FastAPI port

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

// State
let currentSessionId = null;
let selectedFiles = [];
const MAX_FILES_PER_SESSION = 5; // Must match backend/config.py

// --- Utility Functions ---

/**
 * Displays a retro-styled error toast.
 * @param {string} message - The error message.
 */
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.textContent = `[ERROR] ${message}`;
    errorToastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

/**
 * Scrolls the chat history to the bottom.
 */
function scrollToBottom() {
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
}

/**
 * Renders a message in the chat history.
 * @param {'user'|'assistant'|'system'} type - Type of message.
 * @param {string} content - Message content.
 */
function renderMessage(type, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${type}-message`;
    
    let prefix = '';
    if (type === 'user') {
        prefix = '<span class="neon-text-cyan">[USER]</span> ';
    } else if (type === 'assistant') {
        prefix = '<span class="neon-text-magenta">[ASSISTANT]</span> ';
    } else if (type === 'system') {
        prefix = '<span class="neon-text-cyan">[SYSTEM]</span> ';
    }

    // Simple markdown-like formatting for newlines
    const formattedContent = content.replace(/\n/g, '<br>');
    
    messageEl.innerHTML = prefix + formattedContent;
    chatHistoryEl.appendChild(messageEl);
    scrollToBottom();
}

/**
 * Updates the file list display in the Documents Bay.
 */
function updateFileList() {
    fileListEl.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        
        const nameEl = document.createElement('span');
        nameEl.className = 'file-name';
        nameEl.textContent = file.name;

        const statusEl = document.createElement('span');
        statusEl.className = 'file-status status-pending';
        statusEl.textContent = 'PENDING';
        file.statusEl = statusEl; // Store reference for later update

        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'X';
        removeBtn.className = 'retro-button stop-btn';
        removeBtn.style.padding = '2px 5px';
        removeBtn.style.fontSize = '0.8em';
        removeBtn.onclick = () => removeFile(index);

        item.appendChild(nameEl);
        item.appendChild(statusEl);
        item.appendChild(removeBtn);
        fileListEl.appendChild(item);
    });

    fileCountEl.textContent = `(${selectedFiles.length}/${MAX_FILES_PER_SESSION})`;
    uploadBtn.disabled = selectedFiles.length === 0;
}

/**
 * Removes a file from the selected list.
 * @param {number} index - Index of the file to remove.
 */
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

// --- API Calls ---

/**
 * Calls the /session endpoint to get a new session ID.
 */
async function getNewSession() {
    try {
        renderMessage('system', 'Requesting new session ID from Time Console...');
        const response = await fetch(`${API_BASE_URL}/session`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        currentSessionId = data.session_id;
        sessionIdEl.textContent = currentSessionId;
        questionInput.disabled = false;
        sendBtn.disabled = false;
        renderMessage('system', `New session established. ID: ${currentSessionId}`);
    } catch (error) {
        console.error('Error getting new session:', error);
        showToast(`Failed to establish session: ${error.message}`);
        questionInput.disabled = true;
        sendBtn.disabled = true;
    }
}

/**
 * Calls the /upload endpoint to process files.
 */
async function handleUploadFiles() {
    if (selectedFiles.length === 0) return;

    uploadBtn.disabled = true;
    questionInput.disabled = true;
    sendBtn.disabled = true;
    renderMessage('system', `Initiating upload of ${selectedFiles.length} file(s)...`);

    const formData = new FormData();
    formData.append('session_id', currentSessionId);
    
    // Append files to FormData
    selectedFiles.forEach(file => {
        formData.append('files', file, file.name);
        file.statusEl.textContent = 'UPLOADING...';
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
        
        // Update file list status based on backend response
        let successCount = 0;
        let errorMessages = [];
        
        // The backend returns a list of errors, one for each failed file.
        // Since the backend only processes the first MAX_FILES_PER_SESSION, 
        // we need to match the errors to the files. This is tricky without 
        // a file-specific ID in the response. We'll rely on the success_count 
        // and the error list to construct a system message.
        
        if (data.success_count > 0) {
            renderMessage('system', `✓ Successfully processed ${data.success_count} file(s).`);
        }
        
        if (data.errors.length > 0) {
            let errorMsg = "⚠ Upload Errors:\n";
            data.errors.forEach(err => {
                errorMsg += `  • ${err}\n`;
            });
            renderMessage('system', errorMsg);
            showToast(`Upload finished with ${data.errors.length} error(s).`);
        }
        
        // Clear selected files after processing
        selectedFiles = [];
        updateFileList();

    } catch (error) {
        console.error('Error during upload:', error);
        showToast(`Upload failed: ${error.message}`);
        renderMessage('system', `✗ Upload failed due to a network or server error: ${error.message}`);
    } finally {
        uploadBtn.disabled = false;
        questionInput.disabled = false;
        sendBtn.disabled = false;
    }
}

/**
 * Calls the /question endpoint to get an answer.
 * @param {string} question - The user's question.
 */
async function handleSendQuestion(question) {
    if (!question.trim()) return;

    questionInput.disabled = true;
    sendBtn.disabled = true;
    
    // Add user message to history
    renderMessage('user', question);
    questionInput.value = ''; // Clear input immediately

    // Placeholder for assistant's response
    const assistantMessageEl = document.createElement('div');
    assistantMessageEl.className = 'chat-message assistant-message';
    assistantMessageEl.innerHTML = '<span class="neon-text-magenta">[ASSISTANT]</span> <span class="typing-indicator">...</span>';
    chatHistoryEl.appendChild(assistantMessageEl);
    scrollToBottom();

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

        if (response.status === 400) {
            const errorData = await response.json();
            renderMessage('system', `✗ Validation Error: ${errorData.detail}`);
            assistantMessageEl.remove(); // Remove placeholder
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Replace placeholder with actual answer
        assistantMessageEl.innerHTML = `<span class="neon-text-magenta">[ASSISTANT]</span> ${data.answer.replace(/\n/g, '<br>')}`;
        scrollToBottom();

    } catch (error) {
        console.error('Error during question:', error);
        showToast(`Question failed: ${error.message}`);
        assistantMessageEl.innerHTML = '<span class="neon-text-magenta">[ASSISTANT]</span> ✗ I apologize, but I encountered a critical error while processing your question. Please try again.';
        scrollToBottom();
    } finally {
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

/**
 * Calls the /clear endpoint and starts a new session.
 */
async function handleClearSession() {
    if (!currentSessionId) {
        // If no session, just start a new one
        chatHistoryEl.innerHTML = '';
        await getNewSession();
        return;
    }
    
    clearSessionBtn.disabled = true;
    questionInput.disabled = true;
    sendBtn.disabled = true;
    
    renderMessage('system', `Initiating session reboot for ID: ${currentSessionId}...`);

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
        renderMessage('system', `✓ Session documents cleared: ${data.deleted_count} document(s) deleted.`);
        
        // Start a new session
        chatHistoryEl.innerHTML = '';
        await getNewSession();

    } catch (error) {
        console.error('Error during clear session:', error);
        showToast(`Session clear failed: ${error.message}`);
        renderMessage('system', `✗ Warning: Error clearing session documents: ${error.message}`);
        
        // Still attempt to get a new session ID to continue
        await getNewSession();
    } finally {
        clearSessionBtn.disabled = false;
        questionInput.disabled = false;
        sendBtn.disabled = false;
    }
}

// --- Event Listeners ---

// File selection via button click
fileInput.addEventListener('change', (event) => {
    const newFiles = Array.from(event.target.files);
    
    // Filter out non-.txt files and files exceeding the limit
    const validFiles = newFiles.filter(file => file.name.endsWith('.txt'));
    const invalidFiles = newFiles.filter(file => !file.name.endsWith('.txt'));
    
    if (invalidFiles.length > 0) {
        showToast(`Dropped ${invalidFiles.length} non-.txt files.`);
    }
    
    // Add valid files, respecting the MAX_FILES_PER_SESSION limit
    const remainingSlots = MAX_FILES_PER_SESSION - selectedFiles.length;
    const filesToAdd = validFiles.slice(0, remainingSlots);
    
    if (validFiles.length > remainingSlots) {
        showToast(`Only the first ${remainingSlots} valid files were added (max ${MAX_FILES_PER_SESSION} total).`);
    }
    
    selectedFiles.push(...filesToAdd);
    updateFileList();
    
    // Clear the input value so the same file can be selected again
    fileInput.value = '';
});

// Drag and Drop functionality
uploadArea.addEventListener('dragover', (event) => {
    event.preventDefault();
    uploadArea.style.boxShadow = '0 0 15px var(--color-neon-cyan)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.boxShadow = '0 0 5px var(--color-neon-purple)';
});

uploadArea.addEventListener('drop', (event) => {
    event.preventDefault();
    uploadArea.style.boxShadow = '0 0 5px var(--color-neon-purple)';
    
    const newFiles = Array.from(event.dataTransfer.files);
    
    // Filter out non-.txt files and files exceeding the limit
    const validFiles = newFiles.filter(file => file.name.endsWith('.txt'));
    const invalidFiles = newFiles.filter(file => !file.name.endsWith('.txt'));
    
    if (invalidFiles.length > 0) {
        showToast(`Dropped ${invalidFiles.length} non-.txt files.`);
    }
    
    // Add valid files, respecting the MAX_FILES_PER_SESSION limit
    const remainingSlots = MAX_FILES_PER_SESSION - selectedFiles.length;
    const filesToAdd = validFiles.slice(0, remainingSlots);
    
    if (validFiles.length > remainingSlots) {
        showToast(`Only the first ${remainingSlots} valid files were added (max ${MAX_FILES_PER_SESSION} total).`);
    }
    
    selectedFiles.push(...filesToAdd);
    updateFileList();
});

// Upload button click
uploadBtn.addEventListener('click', handleUploadFiles);

// Send button click
sendBtn.addEventListener('click', () => {
    handleSendQuestion(questionInput.value);
});

// Enter key in question input
questionInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        handleSendQuestion(questionInput.value);
    }
});

// Clear session button click
clearSessionBtn.addEventListener('click', handleClearSession);

// --- Initialization ---
document.addEventListener('DOMContentLoaded', getNewSession);