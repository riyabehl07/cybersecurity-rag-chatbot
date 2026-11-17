# Cybersecurity RAG Chatbot 🛡️🤖

A privacy-focused, local **Retrieval-Augmented Generation (RAG)** chatbot designed for analyzing cybersecurity documentation, threat reports, policies, and research papers. 

Built with **Flask**, **LangChain**, **FAISS**, and local models (**TinyLlama-1.1B** & **Sentence Transformers**), this application allows you to ingest PDF documents and ask questions entirely offline without exposing sensitive data to external third-party cloud APIs.

---

## ✨ Features

- **Local & Private Execution**: Runs local embeddings (`sentence-transformers/all-MiniLM-L6-v2`) and a local quantized LLM (`TinyLlama-1.1B-Chat-v1.0-GGUF` via `CTransformers`) with no external API keys required.
- **Document Management**: Drag-and-drop multi-file PDF upload, real-time parsing, and individual document removal with automatic index rebuilding.
- **High-Performance Vector Search**: Leverages FAISS (Facebook AI Similarity Search) to retrieve relevant context chunks instantly.
- **Cybersecurity Focused Context Prompting**: Tailored system prompt instructing the model to act as a security analyst with strict context-grounded reasoning.
- **Responsive Web Interface**: Sleek dark-mode dashboard styled with Tailwind CSS, featuring document lists, dynamic upload feedback, and a conversational chat window with typing indicators.
- **Docker Support**: Containerized for seamless cross-platform deployment.

---

## 🏗️ Architecture

```
User (Browser) ──> Web UI (index.html / Tailwind CSS)
                          │
                   Flask Server (app.py)
                   ┌──────┴──────────────────────────┐
                   ▼                                 ▼
           [Document Upload]                 [Chat Query]
                   │                                 │
            PyPDF Text Extractor                     │
                   │                                 │
       Recursive Character Splitter                  │
                   │                                 │
     Sentence-Transformers Embeddings                │
                   │                                 │
         FAISS Local Vector Store  ◄── Similarity Search (top k=3)
                                                     │
                                             LangChain Stuff QA
                                                     │
                                        CTransformers (TinyLlama GGUF)
                                                     │
                                            Generated Answer
```

---

## 📁 Project Structure

```
.
├── app.py               # Flask backend, RAG pipeline, and REST API endpoints
├── index.html           # Frontend interface (Tailwind CSS, FontAwesome)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker container configuration
├── .dockerignore        # Docker build context exclusions
├── .gitignore           # Git ignore rules for virtual environments and vector stores
└── README.md            # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or 3.11 recommended
- C/C++ build tools (required for building `ctransformers` and C extensions)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/riyabehl07/cybersecurity-rag-chatbot.git
cd cybersecurity-rag-chatbot
```

### 2. Set Up a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note on Model Weights**: On first launch, the application will automatically download the embedding model (`all-MiniLM-L6-v2`) and the quantized LLM (`TinyLlama-1.1B-Chat-v1.0-GGUF`, ~669MB). Please ensure you have an active internet connection during initial startup.

### 4. Run the Application

```bash
python app.py
```

Access the web interface at **[http://localhost:5000](http://localhost:5000)**.

---

## 🐳 Running with Docker

You can containerize and run the application without needing local Python installations:

```bash
# Build the Docker image
docker build -t cybersecurity-rag-chatbot .

# Run the container
docker run -p 5000:5000 cybersecurity-rag-chatbot
```

Visit `http://localhost:5000` in your browser.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the main web dashboard (`index.html`). |
| `POST` | `/upload` | Uploads one or more PDF files and rebuilds the vector store. |
| `GET` | `/documents` | Returns JSON list of currently indexed PDF files. |
| `DELETE` | `/delete/<filename>` | Removes an uploaded PDF and triggers index rebuild. |
| `POST` | `/chat` | Submits a query `{"message": "..."}` and returns RAG response `{"reply": "..."}`. |

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
