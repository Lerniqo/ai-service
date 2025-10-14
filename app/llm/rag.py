"""
RAG (Retrieval-Augmented Generation) Module

This module handles vector store initialization, document loading, and retrieval
for enhancing LLM responses with relevant context.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    JSONLoader,
    CSVLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.config import get_settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for managing RAG operations including vector store and retrieval."""
    
    def __init__(self):
        """Initialize RAG service with settings."""
        self.settings = get_settings()
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.EMBEDDING_CHUNK_SIZE,
            chunk_overlap=self.settings.EMBEDDING_CHUNK_OVERLAP,
            length_function=len,
        )
        
    def _initialize_embeddings(self):
        """Initialize Google Generative AI embeddings."""
        if not self.embeddings:
            if not self.settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not configured")
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=self.settings.EMBEDDING_MODEL,
                google_api_key=self.settings.GOOGLE_API_KEY
            )
            logger.info(f"Initialized embeddings with model: {self.settings.EMBEDDING_MODEL}")
    
    def _initialize_vector_store(self):
        """Initialize or load the vector store."""
        if not self.vector_store:
            self._initialize_embeddings()
            
            persist_directory = Path(self.settings.VECTOR_STORE_PATH)
            persist_directory.mkdir(parents=True, exist_ok=True)
            
            if self.settings.VECTOR_STORE_TYPE.lower() == "chroma":
                self.vector_store = Chroma(
                    collection_name=self.settings.VECTOR_STORE_COLLECTION,
                    embedding_function=self.embeddings,
                    persist_directory=str(persist_directory)
                )
                logger.info(f"Initialized Chroma vector store at: {persist_directory}")
            else:
                raise ValueError(f"Unsupported vector store type: {self.settings.VECTOR_STORE_TYPE}")
    
    def load_documents_from_directory(
        self,
        directory_path: str,
        file_pattern: str = "**/*.txt",
        loader_type: str = "text"
    ) -> int:
        """
        Load documents from a directory into the vector store.
        
        Args:
            directory_path: Path to directory containing documents
            file_pattern: Glob pattern for files to load
            loader_type: Type of loader (text, json, csv)
            
        Returns:
            Number of documents loaded
        """
        self._initialize_vector_store()
        
        # Select appropriate loader
        loader_cls = {
            "text": TextLoader,
            "json": JSONLoader,
            "csv": CSVLoader
        }.get(loader_type.lower(), TextLoader)
        
        # Load documents
        loader = DirectoryLoader(
            directory_path,
            glob=file_pattern,
            loader_cls=loader_cls,
            show_progress=True
        )
        
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} documents from {directory_path}")
        
        # Split documents into chunks
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Split into {len(split_docs)} chunks")
        
        # Add to vector store
        self.vector_store.add_documents(split_docs)
        logger.info(f"Added {len(split_docs)} chunks to vector store")
        
        return len(split_docs)
    
    def load_documents(self, documents: List[Document]) -> int:
        """
        Load pre-processed documents into the vector store.
        
        Args:
            documents: List of LangChain Document objects
            
        Returns:
            Number of chunks added
        """
        self._initialize_vector_store()
        
        # Split documents into chunks
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(split_docs)} chunks")
        
        # Add to vector store
        self.vector_store.add_documents(split_docs)
        logger.info(f"Added {len(split_docs)} chunks to vector store")
        
        return len(split_docs)
    
    def load_text_data(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> int:
        """
        Load raw text data into the vector store.
        
        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dicts for each text
            
        Returns:
            Number of chunks added
        """
        self._initialize_vector_store()
        
        # Create documents from texts
        documents = [
            Document(page_content=text, metadata=metadatas[i] if metadatas else {})
            for i, text in enumerate(texts)
        ]
        
        return self.load_documents(documents)
    
    def retrieve_relevant_context(
        self,
        query: str,
        k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query string
            k: Number of documents to retrieve (defaults to RAG_TOP_K from config)
            score_threshold: Minimum similarity score (defaults to RAG_SCORE_THRESHOLD)
            
        Returns:
            List of relevant documents
        """
        self._initialize_vector_store()
        
        k = k or self.settings.RAG_TOP_K
        score_threshold = score_threshold or self.settings.RAG_SCORE_THRESHOLD
        
        # Retrieve with scores
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query,
            k=k
        )
        
        # Filter by score threshold
        filtered_docs = [
            doc for doc, score in docs_with_scores
            if score >= score_threshold
        ]
        
        logger.info(f"Retrieved {len(filtered_docs)} relevant documents for query")
        return filtered_docs
    
    def get_retriever(self, **kwargs):
        """
        Get a LangChain retriever for the vector store.
        
        Args:
            **kwargs: Additional arguments for the retriever
            
        Returns:
            LangChain retriever
        """
        self._initialize_vector_store()
        
        search_kwargs = {
            "k": kwargs.get("k", self.settings.RAG_TOP_K),
        }
        
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs
        )
    
    def clear_vector_store(self):
        """Clear all documents from the vector store."""
        if self.vector_store:
            self.vector_store.delete_collection()
            logger.info("Cleared vector store")
            self.vector_store = None
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        self._initialize_vector_store()
        
        if isinstance(self.vector_store, Chroma):
            collection = self.vector_store._collection
            return {
                "name": collection.name,
                "count": collection.count(),
            }
        
        return {"error": "Stats not available for this vector store type"}


# Global RAG service instance
_rag_service = None


def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
