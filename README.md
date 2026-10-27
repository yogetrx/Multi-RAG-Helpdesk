# Multi-RAG IT Helpdesk Agent

A learning project for building a multi-knowledge-base Retrieval-Augmented Generation (RAG) application.

## Current stage
Project scaffold only. The next milestones are:
1. Add sample documents to each knowledge base.
2. Implement ingestion, chunking, embeddings, and separate FAISS indexes.
3. Implement routing across knowledge bases.
4. Fuse retrieved evidence and generate cited answers.
5. Add evaluation tests and a Streamlit UI.

## Setup (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for this terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run the starter API

```powershell
python -m uvicorn helpdesk.main:app --app-dir src --reload
```

Open http://127.0.0.1:8000/docs.

This starter intentionally does not call an LLM or perform retrieval yet.
