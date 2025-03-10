"""
AI components initialization and factory
"""
import os
from app.config.config import logger, OPENAI_API_KEY, OPENAI_AVAILABLE, EMBEDDING_AVAILABLE

# Initialize AI components
def initialize_ai_components():
    """Initialize AI components if dependencies are available"""
    llm_controller = None
    embedding_retriever = None
    memory_evolution = None
    
    # Initialize LLM controller
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        try:
            from app.ai.llm.controllers import LLMController
            llm_controller = LLMController(
                backend="openai" if OPENAI_API_KEY else "mock"
            )
            logger.info("LLM controller initialized with OpenAI backend")
        except Exception as e:
            logger.warning(f"Failed to initialize LLM controller: {e}")
            llm_controller = None
    
    # Initialize embedding retriever
    if EMBEDDING_AVAILABLE:
        try:
            from app.ai.semantic.retriever import EmbeddingRetriever
            embedding_retriever = EmbeddingRetriever(model_name='all-MiniLM-L6-v2')
            
            # Load existing embeddings if available
            if embedding_retriever.embedding_available:
                embedding_retriever.load_embeddings()
                logger.info("Embedding retriever initialized and embeddings loaded")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding retriever: {e}")
            embedding_retriever = None
    
    # Initialize memory evolution system
    if llm_controller and embedding_retriever:
        try:
            from app.ai.memory.evolution import MemoryEvolutionSystem
            from app.database.db import db
            
            memory_evolution = MemoryEvolutionSystem(
                db=db,
                llm_controller=llm_controller,
                embedding_retriever=embedding_retriever
            )
            logger.info("Memory evolution system initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize memory evolution system: {e}")
            memory_evolution = None
    
    ai_components = {
        "llm_controller": llm_controller,
        "embedding_retriever": embedding_retriever,
        "memory_evolution": memory_evolution,
        "ai_features_enabled": bool(llm_controller and embedding_retriever)
    }
    
    return ai_components