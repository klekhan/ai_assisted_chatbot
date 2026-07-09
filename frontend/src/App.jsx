import { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import { listDocuments, uploadDocument, deleteDocument, askQuestion } from "./lib/api";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      setError(`Couldn't reach the backend: ${err.message}`);
    } finally {
      setDocsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const handleUpload = async (file) => {
    setUploading(true);
    setUploadProgress(0);
    setError(null);
    try {
      await uploadDocument(file, setUploadProgress);
      await refreshDocuments();
    } catch (err) {
      setError(`Upload failed for "${file.name}": ${err.message}`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (documentId) => {
    setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
    try {
      await deleteDocument(documentId);
    } catch (err) {
      setError(`Couldn't delete document: ${err.message}`);
      refreshDocuments();
    }
  };

  const handleSend = async (question) => {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setSending(true);
    setError(null);
    try {
      const res = await askQuestion(question);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, sources: res.sources }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Something went wrong: ${err.message}` },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-screen bg-base text-ink font-sans overflow-hidden">
      <Sidebar
        documents={documents}
        loading={docsLoading}
        uploading={uploading}
        uploadProgress={uploadProgress}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />
      <ChatPanel
        messages={messages}
        sending={sending}
        hasDocuments={documents.length > 0}
        onSend={handleSend}
      />

      {error && (
        <div className="fixed bottom-4 right-4 max-w-sm rounded-xl border border-danger/30 bg-surface shadow-card px-4 py-3 text-[13px] text-ink">
          <button
            onClick={() => setError(null)}
            className="float-right text-muted hover:text-ink ml-2"
            aria-label="Dismiss"
          >
            ×
          </button>
          {error}
        </div>
      )}
    </div>
  );
}
