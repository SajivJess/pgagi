import os
import hashlib
import json
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiofiles
from pypdf import PdfReader
from fastapi import UploadFile
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import re

class DocumentProcessor:
    """Handles document ingestion, chunking, and vector indexing with FAISS"""
    
    def __init__(self):
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        print("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)  # L2 distance for similarity
        
        # Storage for chunks and metadata
        self.chunks = []  # List of all chunks with metadata
        self.documents = {}  # Document metadata
        
        # BM25 for keyword search (hybrid retrieval)
        self.bm25 = None
        self.tokenized_chunks = []
        
        # Persistent storage paths
        self.metadata_file = self.upload_dir / "documents_metadata.json"
        self.index_file = self.upload_dir / "faiss.index"
        self.chunks_file = self.upload_dir / "chunks.pkl"
        self.bm25_file = self.upload_dir / "bm25.pkl"
        
        # Load existing data if available
        self._load_persistent_data()
        
        # Build BM25 if chunks exist but BM25 doesn't
        if len(self.chunks) > 0 and self.bm25 is None:
            print("Building BM25 index for existing chunks...")
            self._build_bm25_index()
            self._save_persistent_data()
            print("BM25 index built and saved")
    
    def _load_persistent_data(self):
        """Load persisted index and chunks"""
        try:
            if self.index_file.exists():
                self.index = faiss.read_index(str(self.index_file))
                print(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            if self.chunks_file.exists():
                with open(self.chunks_file, 'rb') as f:
                    self.chunks = pickle.load(f)
                print(f"Loaded {len(self.chunks)} chunks")
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                print(f"Loaded metadata for {len(self.documents)} documents")
            
            if self.bm25_file.exists():
                with open(self.bm25_file, 'rb') as f:
                    bm25_data = pickle.load(f)
                    self.bm25 = bm25_data['bm25']
                    self.tokenized_chunks = bm25_data['tokenized_chunks']
                print(f"Loaded BM25 index")
        except Exception as e:
            print(f"Warning: Could not load persistent data: {e}")
    
    def _save_persistent_data(self):
        """Save index and chunks to disk"""
        try:
            faiss.write_index(self.index, str(self.index_file))
            
            with open(self.chunks_file, 'wb') as f:
                pickle.dump(self.chunks, f)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2)
            
            # Save BM25 index
            if self.bm25:
                with open(self.bm25_file, 'wb') as f:
                    pickle.dump({
                        'bm25': self.bm25,
                        'tokenized_chunks': self.tokenized_chunks
                    }, f)
                
            print("Saved persistent data")
        except Exception as e:
            print(f"Error saving persistent data: {e}")
    
    async def process_document(self, file: UploadFile) -> Dict[str, Any]:
        """Process and index a document"""
        print(f"Starting document processing for: {file.filename}")
        
        # Save uploaded file
        file_path = self.upload_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        print(f"File saved to: {file_path}")
        
        # Generate document ID
        doc_id = hashlib.md5(file.filename.encode()).hexdigest()
        
        # Extract text from PDF and create chunks
        print(f"Extracting text from PDF...")
        text_chunks = self._extract_and_chunk_pdf(file_path, doc_id, file.filename)
        print(f"Extracted {len(text_chunks)} chunks from PDF")
        
        if not text_chunks:
            return {
                "document_id": doc_id,
                "filename": file.filename,
                "chunks_count": 0,
                "error": "No text extracted from PDF"
            }
        
        # Generate embeddings
        print(f"Generating embeddings for {len(text_chunks)} chunks...")
        texts = [chunk["content"] for chunk in text_chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
        
        # Add to FAISS index
        print(f"Adding {len(embeddings)} vectors to FAISS index...")
        embeddings_np = np.array(embeddings).astype('float32')
        self.index.add(embeddings_np)
        print(f"FAISS index now has {self.index.ntotal} vectors")
        
        # Store chunks
        self.chunks.extend(text_chunks)
        
        # Update BM25 index for hybrid search
        print("Building BM25 index for keyword search...")
        self._build_bm25_index()
        
        # Save document metadata
        self.documents[doc_id] = {
            "filename": file.filename,
            "path": str(file_path),
            "chunks_count": len(text_chunks),
        }
        
        # Persist to disk
        print("Saving to disk...")
        self._save_persistent_data()
        print("Document processing complete!")
        
        return {
            "document_id": doc_id,
            "filename": file.filename,
            "chunks_count": len(text_chunks)
        }
    
    def _extract_and_chunk_pdf(self, file_path: Path, doc_id: str, filename: str) -> List[Dict[str, Any]]:
        """Extract text from PDF and split into chunks"""
        chunks = []
        
        try:
            reader = PdfReader(file_path)
            
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                
                if text.strip():
                    # Chunk the page text
                    page_chunks = self._chunk_text(text, chunk_size=1000, overlap=200)
                    
                    for chunk_idx, chunk_text in enumerate(page_chunks):
                        chunk_id = f"{doc_id}_page{page_num}_chunk{chunk_idx}"
                        chunks.append({
                            "id": chunk_id,
                            "document_id": doc_id,
                            "filename": filename,
                            "page_number": page_num,
                            "chunk_index": chunk_idx,
                            "content": chunk_text
                        })
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
        return chunks
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start += (chunk_size - overlap)
        
        return chunks
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\w+', text.lower())
        return tokens
    
    def _build_bm25_index(self):
        """Build BM25 index for keyword search"""
        if not self.chunks:
            return
        
        # Tokenize all chunks
        self.tokenized_chunks = [self._tokenize(chunk["content"]) for chunk in self.chunks]
        
        # Build BM25 index
        self.bm25 = BM25Okapi(self.tokenized_chunks)
        print(f"BM25 index built with {len(self.tokenized_chunks)} chunks")
    
    def search_documents(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Hybrid search combining FAISS vector similarity and BM25 keyword search"""
        if self.index.ntotal == 0:
            return []
        
        # FAISS vector search
        query_embedding = self.embedding_model.encode([query])[0]
        query_vector = np.array([query_embedding]).astype('float32')
        distances, indices = self.index.search(query_vector, min(top_k * 2, self.index.ntotal))
        
        # BM25 keyword search
        bm25_scores = []
        if self.bm25:
            tokenized_query = self._tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Combine scores (hybrid approach)
        combined_results = {}
        
        # Add vector search results
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.chunks):
                vector_score = float(1 / (1 + dist))
                bm25_score = float(bm25_scores[int(idx)]) if len(bm25_scores) > 0 and int(idx) < len(bm25_scores) else 0.0
                
                # Weighted combination: 60% vector, 40% BM25
                combined_score = 0.6 * vector_score + 0.4 * (bm25_score / 10.0 if bm25_score > 0.0 else 0.0)
                
                combined_results[int(idx)] = {
                    'chunk': self.chunks[int(idx)],
                    'score': float(combined_score),
                    'vector_score': float(vector_score),
                    'bm25_score': float(bm25_score)
                }
        
        # Sort by combined score
        sorted_results = sorted(combined_results.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Apply filters if provided
        filtered_results = []
        for idx, data in sorted_results[:top_k * 2]:
            chunk = data['chunk'].copy()
            
            # Apply document filter
            if filters and filters.get('document'):
                if str(chunk['filename']) != str(filters['document']):
                    continue
            
            # Apply page filter
            if filters and filters.get('page_range'):
                page_min, page_max = int(filters['page_range'][0]), int(filters['page_range'][1])
                page_num = int(chunk['page_number'])
                if not (page_min <= page_num <= page_max):
                    continue
            
            # Apply confidence filter
            if filters and filters.get('min_confidence'):
                score = float(data['score'])
                min_conf = float(filters['min_confidence'])
                if score < min_conf:
                    continue
            
            chunk["relevance_score"] = data['score']
            chunk["vector_score"] = data['vector_score']
            chunk["bm25_score"] = data['bm25_score']
            filtered_results.append(chunk)
            
            if len(filtered_results) >= top_k:
                break
        
        return filtered_results
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get list of all documents"""
        return [
            {
                "document_id": doc_id,
                **metadata
            }
            for doc_id, metadata in self.documents.items()
        ]
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all uploaded documents (alias for get_all_documents)"""
        return self.get_all_documents()
