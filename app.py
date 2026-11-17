import os
import shutil
import traceback
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pypdf import PdfReader

# --- LangChain Imports ---
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import CTransformers # For running local models

# --- Constants ---
UPLOAD_FOLDER = 'uploads'
VECTORSTORE_PATH = 'vectorstore'
ALLOWED_EXTENSIONS = {'pdf'}

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='.', static_url_path='')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Global RAG Components ---
vector_store = None
qa_chain = None
embeddings = None
llm = None

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_pdf_text(pdf_paths):
    text = ""
    for pdf_path in pdf_paths:
        try:
            # Use strict=False to be more lenient with potentially corrupted PDFs
            pdf_reader = PdfReader(pdf_path, strict=False)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        except Exception as e:
            print(f"Error reading PDF {os.path.basename(pdf_path)}: {e}")
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    return text_splitter.split_text(text)

def create_and_save_vectorstore(text_chunks, embeddings_model):
    if not text_chunks:
        print("No text chunks to process. Vector store not created.")
        return None
    try:
        new_vector_store = FAISS.from_texts(texts=text_chunks, embedding=embeddings_model)
        if os.path.exists(VECTORSTORE_PATH):
            shutil.rmtree(VECTORSTORE_PATH)
        new_vector_store.save_local(VECTORSTORE_PATH)
        print(f"Vector store created and saved to {VECTORSTORE_PATH}")
        return new_vector_store
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

def initialize_components():
    global embeddings, qa_chain, llm
    print("Initializing embedding model (local)...")
    try:
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        print("Embedding model initialized.")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize embeddings. Error: {e}")
        traceback.print_exc()
        return False

    print("Initializing local LLM (this may take a few moments)...")
    try:
        # This will download the model file (~669MB) the first time it's run.
        # It runs on the CPU by default but can be configured to use your GPU.
        llm = CTransformers(
            model='TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF',
            model_file='tinyllama-1.1b-chat-v1.0.Q5_K_M.gguf',
            model_type='llama',
            config={'max_new_tokens': 1024, 'temperature': 0.7, 'context_length': 4096}
        )
        print("Local LLM initialized successfully.")
    except Exception as e:
        print(f"Could not initialize local LLM. Check your internet connection for the first download.")
        print(f"Error: {e}")
        traceback.print_exc()
        llm = None

    prompt_template = """
    You are an expert cybersecurity analyst. Use the following pieces of context to answer the user's question.
    If you don't know the answer from the context provided, just say that you don't know, don't try to make up an answer.
    Provide a concise and helpful answer based on the documents.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """
    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    print("Initializing QA model with custom prompt...")
    if llm:
        qa_chain = load_qa_chain(llm, chain_type="stuff", prompt=PROMPT)
        print("QA chain initialized.")
    else:
        qa_chain = None
        print("QA chain could not be initialized because the LLM is not available.")
    return True

def rebuild_global_vectorstore():
    global vector_store
    print("Rebuilding global vector store...")
    if not embeddings:
        print("Embeddings model not initialized. Cannot rebuild vector store.")
        return False

    uploaded_docs = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
    if not uploaded_docs:
        print("No documents in upload folder. Clearing vector store.")
        if os.path.exists(VECTORSTORE_PATH):
            shutil.rmtree(VECTORSTORE_PATH)
        vector_store = None
        return True

    try:
        raw_text = get_pdf_text(uploaded_docs)
        text_chunks = get_text_chunks(raw_text)
        vector_store = create_and_save_vectorstore(text_chunks, embeddings)
        print("Global vector store rebuilt successfully.")
        return True
    except Exception as e:
        print(f"An error occurred during vector store rebuild: {e}")
        vector_store = None
        return False

# --- Flask Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    files = request.files.getlist('files')
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
    if not rebuild_global_vectorstore():
        return jsonify({'success': False, 'message': 'Failed to process documents.'}), 500
    return jsonify({'success': True, 'message': 'Files processed.'})

@app.route('/documents', methods=['GET'])
def get_documents():
    try:
        docs = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
        return jsonify({'documents': docs})
    except Exception as e:
        return jsonify({'documents': [], 'message': str(e)}), 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
        if os.path.exists(filepath):
            os.remove(filepath)
            rebuild_global_vectorstore()
            return jsonify({'success': True, 'message': f'File {filename} deleted.'})
        else:
            return jsonify({'success': False, 'message': 'File not found.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    global vector_store, qa_chain
    data = request.json
    user_message = data.get('message')

    if not qa_chain:
        return jsonify({'reply': 'The local Question-Answering model is not available. Please check the server logs.'}), 503

    if not os.path.exists(VECTORSTORE_PATH):
        return jsonify({'reply': 'Please upload PDF files first.'}), 400

    try:
        current_vector_store = FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
        docs = current_vector_store.similarity_search(user_message, k=3)
        if not docs:
             return jsonify({'reply': "I could not find relevant information in the uploaded documents to answer your question."})

        # Using the correct .invoke method for the chain
        response = qa_chain.invoke(
            {"input_documents": docs, "question": user_message}
        )
        reply = response.get('output_text', 'Sorry, I had trouble generating a response.')
        return jsonify({'reply': reply})

    except Exception as e:
        print(f"!!! CHAT PROCESSING ERROR !!!")
        print(f"Error: {e}")
        traceback.print_exc()
        print("-----------------")
        return jsonify({'reply': 'An error occurred while processing your request. Check server logs for details.'}), 500

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask server...")
    if not initialize_components():
         print("Shutting down due to critical initialization error.")
    else:
        rebuild_global_vectorstore()
        # use_reloader=False is important for stability when models are loaded into memory
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

