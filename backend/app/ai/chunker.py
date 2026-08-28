from dataclasses import dataclass
import math
import re
from typing import Optional

from app.ai.cleaner import clean_clinical_text
from app.ai.extractors import ExtractedDocument


@dataclass
class ChunkData:
    """Represents a generated text chunk ready for persistence."""

    chunk_index: int
    page_number: Optional[int]
    content: str
    token_count: int


def estimate_token_count(text: str) -> int:
    """Estimate token count deterministically without requiring external API or heavy tokenizers."""
    if not text:
        return 0
    # Standard rule of thumb: ~4 characters per token in English / medical text
    char_estimate = math.ceil(len(text) / 4)
    # Word count heuristic: ~1.3 tokens per word
    word_estimate = math.ceil(len(text.split()) * 1.3)
    return max(1, max(char_estimate, word_estimate))


def split_text_into_semantic_segments(text: str) -> list[str]:
    """Split text along paragraph and sentence boundaries to preserve clinical context."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    segments: list[str] = []

    for para in paragraphs:
        # Split paragraph into sentences while preserving trailing punctuation
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for s in sentences:
            s_clean = s.strip()
            if s_clean:
                segments.append(s_clean)

    return segments if segments else [text]


def chunk_page_content(
    page_text: str,
    page_number: Optional[int],
    start_chunk_index: int,
    chunk_size_tokens: int = 500,
    chunk_overlap_tokens: int = 100,
) -> list[ChunkData]:
    """Create overlapping chunks from a single page's text."""
    cleaned = clean_clinical_text(page_text)
    if not cleaned:
        return []

    segments = split_text_into_semantic_segments(cleaned)
    chunks: list[ChunkData] = []
    current_segments: list[str] = []
    current_tokens = 0
    chunk_idx = start_chunk_index

    for seg in segments:
        seg_tokens = estimate_token_count(seg)

        if current_tokens + seg_tokens > chunk_size_tokens and current_segments:
            # Emit current chunk
            chunk_content = " ".join(current_segments).strip()
            chunks.append(
                ChunkData(
                    chunk_index=chunk_idx,
                    page_number=page_number,
                    content=chunk_content,
                    token_count=estimate_token_count(chunk_content),
                )
            )
            chunk_idx += 1

            # Keep overlapping tail segments for next chunk
            overlap_segments: list[str] = []
            overlap_tokens = 0
            for prev_seg in reversed(current_segments):
                prev_tokens = estimate_token_count(prev_seg)
                if overlap_tokens + prev_tokens <= chunk_overlap_tokens:
                    overlap_segments.insert(0, prev_seg)
                    overlap_tokens += prev_tokens
                else:
                    break

            current_segments = overlap_segments
            current_tokens = overlap_tokens

        current_segments.append(seg)
        current_tokens += seg_tokens

    # Flush remaining segments
    if current_segments:
        chunk_content = " ".join(current_segments).strip()
        chunks.append(
            ChunkData(
                chunk_index=chunk_idx,
                page_number=page_number,
                content=chunk_content,
                token_count=estimate_token_count(chunk_content),
            )
        )

    return chunks


def chunk_extracted_document(
    extracted: ExtractedDocument,
    chunk_size_tokens: int = 500,
    chunk_overlap_tokens: int = 100,
) -> list[ChunkData]:
    """Chunk the entire extracted document preserving page metadata and sequential indexing."""
    all_chunks: list[ChunkData] = []
    current_chunk_index = 0

    if extracted.pages:
        for page_num, page_text in extracted.pages:
            if not page_text.strip():
                continue
            page_chunks = chunk_page_content(
                page_text=page_text,
                page_number=page_num,
                start_chunk_index=current_chunk_index,
                chunk_size_tokens=chunk_size_tokens,
                chunk_overlap_tokens=chunk_overlap_tokens,
            )
            all_chunks.extend(page_chunks)
            current_chunk_index += len(page_chunks)
    else:
        all_chunks = chunk_page_content(
            page_text=extracted.text,
            page_number=1,
            start_chunk_index=0,
            chunk_size_tokens=chunk_size_tokens,
            chunk_overlap_tokens=chunk_overlap_tokens,
        )

    return all_chunks
