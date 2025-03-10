"""
Semantic search module using embeddings
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
import os
import pickle
from pathlib import Path
from app.config.config import logger

class EmbeddingRetriever:
    """Class for embedding-based semantic search"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """Initialize the embedding retriever
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.embedding_available = True
        except ImportError:
            logger.warning("SentenceTransformer not available. Semantic search will be disabled.")
            self.embedding_available = False
            self.model = None
            
        self.corpus = []
        self.embeddings = None
        self.doc_ids = []  # Store document IDs in order
        self.embedding_cache_path = Path("embeddings_cache.pkl")
    
    def save_embeddings(self):
        """Save embeddings to disk"""
        if not self.embedding_available or self.embeddings is None:
            return
            
        data = {
            "corpus": self.corpus,
            "embeddings": self.embeddings,
            "doc_ids": self.doc_ids
        }
        
        with open(self.embedding_cache_path, 'wb') as f:
            pickle.dump(data, f)
    
    def load_embeddings(self):
        """Load embeddings from disk"""
        if not self.embedding_available or not self.embedding_cache_path.exists():
            return False
            
        try:
            with open(self.embedding_cache_path, 'rb') as f:
                data = pickle.load(f)
                
            self.corpus = data["corpus"]
            self.embeddings = data["embeddings"]
            self.doc_ids = data["doc_ids"]
            return True
        except Exception as e:
            logger.error(f"Error loading embeddings: {str(e)}")
            return False
    
    def add_documents(self, documents: List[str], doc_ids: List[str]):
        """Add documents to the retriever
        
        Args:
            documents: List of document texts
            doc_ids: List of document IDs corresponding to the documents
        """
        if not self.embedding_available or not documents:
            return
            
        if not self.corpus:  # Reset if no existing documents
            self.corpus = documents
            self.doc_ids = doc_ids
            self.embeddings = self.model.encode(documents)
        else:
            # Append new documents
            self.corpus.extend(documents)
            self.doc_ids.extend(doc_ids)
            new_embeddings = self.model.encode(documents)
            
            if self.embeddings is None:
                self.embeddings = new_embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
                
        # Save embeddings to disk
        self.save_embeddings()
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar documents using cosine similarity
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of tuples (doc_id, similarity_score)
        """
        if not self.embedding_available or not self.corpus or self.embeddings is None:
            return []
            
        # Encode query
        from sklearn.metrics.pairwise import cosine_similarity
        query_embedding = self.model.encode([query])[0]
        
        # Calculate cosine similarities
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        
        # Get top k results
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        # Return document IDs and similarity scores
        results = []
        for idx in top_indices:
            if idx < len(self.doc_ids):
                results.append((self.doc_ids[idx], float(similarities[idx])))
                
        return results
    
    def reset(self):
        """Reset the retriever"""
        self.corpus = []
        self.embeddings = None
        self.doc_ids = []
        
        # Remove cache file if it exists
        if self.embedding_cache_path.exists():
            try:
                os.remove(self.embedding_cache_path)
            except Exception as e:
                logger.error(f"Error removing embeddings cache: {str(e)}")