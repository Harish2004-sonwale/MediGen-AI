"""AI services and pipeline integrations for MediGen AI.

Phase 8.3: Extraction, cleaning, chunking
Phase 8.4: Embedding providers, vector store
Phase 8.5: Clinical RAG query, context retrieval, prompt construction & LLM synthesis
"""

from app.ai.chunker import (
    ChunkData,
    chunk_extracted_document,
    chunk_page_content,
    estimate_token_count,
    split_text_into_semantic_segments,
)
from app.ai.cleaner import clean_clinical_text
from app.ai.context_builder import (
    CLINICAL_GROUNDING_SYSTEM_PROMPT,
    INSUFFICIENT_INFORMATION_MESSAGE,
    GroundedContextChunk,
    build_grounded_context,
)
from app.ai.embeddings import (
    BaseEmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from app.ai.extractors import (
    ExtractedDocument,
    extract_document_text,
    extract_docx,
    extract_pdf,
    extract_txt,
)
from app.ai.llm import (
    BaseLLMProvider,
    BedrockLLMProvider,
    CitationData,
    LLMGroundedResponse,
    MockLLMProvider,
    OpenAILLMProvider,
    get_llm_provider,
)
from app.ai.ocr import (
    BaseOCRProvider,
    MockOCRProvider,
    TextractOCRProvider,
    get_ocr_provider,
)
from app.ai.vector_store import (
    BaseVectorStore,
    ChromaVectorStore,
    VectorSearchResult,
    get_vector_store,
)

__all__ = [
    # Extractors
    "ExtractedDocument",
    "extract_document_text",
    "extract_pdf",
    "extract_docx",
    "extract_txt",
    # Cleaner
    "clean_clinical_text",
    # Chunker
    "ChunkData",
    "estimate_token_count",
    "split_text_into_semantic_segments",
    "chunk_page_content",
    "chunk_extracted_document",
    # Embeddings
    "BaseEmbeddingProvider",
    "MockEmbeddingProvider",
    "get_embedding_provider",
    # OCR
    "BaseOCRProvider",
    "MockOCRProvider",
    "TextractOCRProvider",
    "get_ocr_provider",
    # Vector store
    "BaseVectorStore",
    "ChromaVectorStore",
    "VectorSearchResult",
    "get_vector_store",
    # Context builder & Grounding
    "CLINICAL_GROUNDING_SYSTEM_PROMPT",
    "INSUFFICIENT_INFORMATION_MESSAGE",
    "GroundedContextChunk",
    "build_grounded_context",
    # LLM Synthesis
    "BaseLLMProvider",
    "CitationData",
    "LLMGroundedResponse",
    "MockLLMProvider",
    "OpenAILLMProvider",
    "BedrockLLMProvider",
    "get_llm_provider",
]
