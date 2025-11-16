// src/App.tsx
import React, { useState } from "react";
import "./App.css";

type MessageRole = "user" | "assistant" | "system";

interface ChatMessage {
  role: MessageRole;
  content: string;
}

function generateSessionId() {
  // browser-safe session id similar to your Python helper
  if ("randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
}

const MAX_FILES_PER_SESSION = 5; // match your backend config if needed

const App: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>(generateSessionId());
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState<string>("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // --- Handlers ---

  const handleUpload = async () => {
    if (!files || files.length === 0) {
      setHistory((prev) => [
        ...prev,
        { role: "system", content: "Please select at least one file to upload." },
      ]);
      return;
    }

    setIsUploading(true);
    try {
      // TODO: call your real backend /upload endpoint here
      // Example:
      // const formData = new FormData();
      // Array.from(files).forEach((file) => formData.append("files", file));
      // formData.append("session_id", sessionId);
      // const res = await fetch("http://localhost:8000/upload", { method: "POST", body: formData });
      // const data = await res.json();
      // const { success_count, errors } = data;

      // Placeholder behavior (no real backend):
      const success_count = Math.min(files.length, MAX_FILES_PER_SESSION);
      const errors: string[] = [];
      let msg: string;

      if (success_count > 0 && errors.length === 0) {
        msg = `✓ Successfully uploaded ${success_count} file(s).`;
      } else if (success_count > 0 && errors.length > 0) {
        msg =
          `✓ Successfully uploaded ${success_count} file(s).\n\n` +
          "⚠ Errors:\n" +
          errors.map((e) => `  • ${e}`).join("\n");
      } else {
        msg = "✗ Upload failed:\n" + errors.map((e) => `  • ${e}`).join("\n");
      }

      if (files.length > MAX_FILES_PER_SESSION) {
        msg += `\n\nNote: Only the first ${MAX_FILES_PER_SESSION} files were processed.`;
      }

      setHistory((prev) => [...prev, { role: "system", content: msg }]);
      setFiles(null); // clear file input visually
      (document.getElementById("file-input") as HTMLInputElement | null)?.value &&
        ((document.getElementById("file-input") as HTMLInputElement).value = "");
    } catch (err: any) {
      setHistory((prev) => [
        ...prev,
        {
          role: "system",
          content: `✗ An unexpected error occurred during upload: ${String(err)}`,
        },
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    if (!question.trim()) return;

    const userMessage: ChatMessage = { role: "user", content: question.trim() };

    setHistory((prev) => [...prev, userMessage]);
    setQuestion("");
    setIsSending(true);

    try {
      // TODO: call your backend /question endpoint
      // Example:
      // const res = await fetch("http://localhost:8000/question", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify({ session_id: sessionId, message: userMessage.content }),
      // });
      // const data = await res.json();
      // const answer = data.answer;

      // Placeholder answer:
      const answer = `Echo from fake backend for session ${sessionId}: ${userMessage.content}`;

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: answer,
      };
      setHistory((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMsg =
        "✗ I apologize, but I encountered an error while processing your question. Please try again.";
      setHistory((prev) => [
        ...prev,
        { role: "assistant", content: errorMsg },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearSession = async () => {
    // TODO: call your backend /clear-session endpoint if needed
    // Example:
    // const res = await fetch("http://localhost:8000/clear-session", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ session_id: sessionId }),
    // });
    // const data = await res.json();
    // const deletedCount = data.deleted_count;

    const deletedCount = 0; // placeholder
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    setHistory([
      {
        role: "system",
        content: `Session cleared: ${deletedCount} document(s) deleted. New session: ${newSessionId}`,
      },
    ]);
  };

  // --- UI rendering ---

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>Title Place Holder</h1>
        <p>
          Upload text documents and ask questions about their content. You can
          upload up to {MAX_FILES_PER_SESSION} files per session.
        </p>
        <p className="session-id">
          Session ID: <code>{sessionId}</code>
        </p>
      </header>

      <main className="app-main">
        {/* Left: Chat */}
        <section className="left-pane">
          <div className="chatbox">
            {history.length === 0 && (
              <div className="empty-chat">No messages yet. Ask a question!</div>
            )}
            {history.map((msg, idx) => (
              <div
                key={idx}
                className={`chat-message chat-${msg.role}`}
              >
                {msg.role !== "system" && (
                  <div className="chat-role">
                    {msg.role === "user" ? "You" : "Assistant"}
                  </div>
                )}
                <div className="chat-content">
                  {msg.content.split("\n").map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="chat-input-row">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Type your question here..."
              rows={2}
              className="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={isSending || !question.trim()}
              className="btn btn-primary"
            >
              {isSending ? "Sending..." : "Send"}
            </button>
          </div>
        </section>

        {/* Right: Upload + controls */}
        <section className="right-pane">
          <div className="card">
            <label className="card-label">
              Upload Documents (max {MAX_FILES_PER_SESSION} files)
            </label>
            <input
              id="file-input"
              type="file"
              multiple
              accept=".txt"
              onChange={(e) => setFiles(e.target.files)}
            />
            <button
              onClick={handleUpload}
              disabled={isUploading || !files || files.length === 0}
              className="btn btn-secondary"
            >
              {isUploading ? "Uploading..." : "Upload Files"}
            </button>
          </div>

          <hr />

          <div className="card">
            <button
              onClick={handleClearSession}
              className="btn btn-danger"
            >
              Clear Session
            </button>
            <p className="hint">
              Clearing session will delete your uploaded documents (on the
              backend) and reset the conversation.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
};

export default App;
