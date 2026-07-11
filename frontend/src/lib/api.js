const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "";

async function request(path, { adminKey, headers, ...options } = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(adminKey ? { "X-Admin-Key": adminKey } : { "X-API-Key": API_KEY }),
      ...headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new Error(detail);
  }

  return res.json();
}

// --- Public (no login required) ---

export function askQuestion(question) {
  return request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function getTopics() {
  return request("/topics");
}

// --- Admin (adminKey passed explicitly each call — never stored in the
// build, only ever in the browser's localStorage after manual login) ---

export function adminListDocuments(adminKey) {
  return request("/admin/documents", { adminKey });
}

export function adminUploadDocument(adminKey, file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/admin/documents/upload`);
    xhr.setRequestHeader("X-Admin-Key", adminKey);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body);
        } else {
          reject(new Error(body.detail || "Upload failed"));
        }
      } catch {
        reject(new Error("Upload failed"));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export function adminDeleteDocument(adminKey, documentId) {
  return request(`/admin/documents/${documentId}`, { method: "DELETE", adminKey });
}

export function adminDebugChat(adminKey, question) {
  return request("/admin/debug-chat", {
    method: "POST",
    adminKey,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}

export function adminGetStats(adminKey) {
  return request("/admin/stats", { adminKey });
}
