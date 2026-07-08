# RAG Chatbot — Frontend

React + Vite + Tailwind chat interface for the RAG backend.

## Local development

```bash
npm install
cp .env.example .env     # then fill in VITE_API_URL and VITE_API_KEY
npm run dev
```

Opens at http://localhost:5173 — make sure the backend is running first (see ../backend/README.md).

## Build for production

```bash
npm run build
```

Outputs static files to `dist/`, ready to deploy to Vercel, Netlify, or any static host.
