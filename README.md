# 🔐 AI Incident Response Copilot

AI-powered assistant that helps turn raw security alerts and logs into actionable response steps.

✅ Built with **React (frontend)**, **FastAPI (backend)**, **Pinecone (vector DB)**, and **OpenAI GPT-4o**.  
✅ Used internally by me and my coworkers at companies I have worked at to log and track common cybersecurity issues.  
✅ Plans to ship soon with production features (see roadmap).

---

## 🚀 Features
- Paste alerts or upload JSON logs → get **context + step-by-step response**.  
- RAG pipeline: Pinecone + OpenAI for trusted MITRE/NIST-based guidance.  
- Built-in **metrics dashboard** (latency, success rate, errors).  
- Clean UI with loader animations + results formatting.

---

## 🛠️ Tech Stack
- **Frontend:** React + Vite  
- **Backend:** FastAPI (Python)  
- **Vector DB:** Pinecone  
- **LLM:** OpenAI GPT-4o + embeddings  
- **DB:** SQLite (for analytics logging)

---

## ⚡ Quickstart
# Backend
- cd backend
- pip install -r requirements.txt
- uvicorn main:app --reload --port 8000

# Frontend
- cd frontend
- npm install
- npm run dev

#Add .env files with your keys (not committed to GitHub):
- OPENAI_API_KEY=sk-...
- PINECONE_API_KEY=pcsk-...

---

## 📍 Roadmap
-Swap SQLite → PostgreSQL for persistence.
-Deploy backend (Render) + frontend (Vercel).
-Secure /metrics with auth.
-Add charts for latency trends.
