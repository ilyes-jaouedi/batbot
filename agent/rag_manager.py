import os
import logging
from typing import List, Optional
from pypdf import PdfReader
from docx import Document
import easyocr
import numpy as np
import cv2
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions
from .config import KNOWLEDGE_BASE_DIR, CHROMA_DB_DIR, COLLECTION_NAME

logger = logging.getLogger(__name__)

# Initialize local embedding function
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

class RAGManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        # Initialize OCR reader (downloads models on first use)
        self.ocr_reader = easyocr.Reader(['en', 'fr'])

    def _extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        try:
            if ext == ".pdf":
                reader = PdfReader(file_path)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
            
            elif ext == ".docx":
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])

            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            elif ext in [".png", ".jpg", ".jpeg"]:
                results = self.ocr_reader.readtext(file_path, detail=0)
                text = " ".join(results)

        except Exception as e:
            logger.error(f"Error extracting from {file_path}: {e}")
        
        return text

    def ingest_pdfs(self) -> str:
        """
        Scans knowledge_base for PDF, DOCX, TXT, MD, and Images.
        Only processes new files.
        """
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            return f"Error: '{KNOWLEDGE_BASE_DIR}' directory does not exist."

        supported_exts = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg"}
        all_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if os.path.splitext(f)[1].lower() in supported_exts]
        
        if not all_files:
            return "No supported files found in the knowledge base folder."

        # Get existing sources from ChromaDB
        existing_data = self.collection.get(include=["metadatas"])
        existing_sources = set()
        if existing_data and existing_data.get("metadatas"):
            for meta in existing_data["metadatas"]:
                if meta and "source" in meta:
                    existing_sources.add(meta["source"])

        new_files = [f for f in all_files if f not in existing_sources]
        
        if not new_files:
            return "No new documents found. Knowledge base is up to date."

        count = 0
        for file_name in new_files:
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, file_name)
            text = self._extract_text(file_path)
            
            if not text.strip():
                logger.warning(f"Could not extract text from {file_name}. Skipping.")
                continue

            chunks = self.text_splitter.split_text(text)
            
            ids = [f"{file_name}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": file_name} for _ in range(len(chunks))]
            
            self.collection.upsert(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            count += 1
            logger.info(f"Ingested: {file_name} ({len(chunks)} chunks)")

        return f"Successfully ingested {count} NEW document(s). Skipped {len(all_files) - count} files."

    def query_knowledge(self, query_text: str, n_results: int = 3) -> str:
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return "No relevant information found in the local knowledge base."
            
            context = "\n\n---\n\n".join(results['documents'][0])
            return f"Relevant information found in your documents:\n\n{context}"
        except Exception as e:
            logger.error(f"Error querying knowledge base: {e}")
            return f"Error searching knowledge base: {str(e)}"

rag_manager = RAGManager()
