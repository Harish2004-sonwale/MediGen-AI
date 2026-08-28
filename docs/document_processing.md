# MediGen AI — Document Text Extraction & Clinical Chunking Pipeline

This document details the architecture and implementation of the **Text Extraction & Clinical Chunking Engine** (Milestone 8, Phase 8.3) in the MediGen AI Clinical Decision Support System.

---

## 1. Pipeline Overview

```text
Uploaded File (PDF, DOCX, TXT)
            ↓
Format Dispatcher (extract_document_text)
 ├── PDF: pypdf (page-by-page extraction, scanned-PDF check)
 ├── DOCX: python-docx (paragraphs + tables extraction)
 └── TXT: UTF-8 reader with graceful encoding fallbacks
            ↓
Clinical Text Cleaner (clean_clinical_text)
 ├── Normalizes whitespace and line breaks
 └── Preserves medical terminology, units, numbers, medication names
            ↓
Semantic Chunking Engine (chunk_extracted_document)
 ├── Paragraph & sentence boundary awareness
 ├── Configurable token threshold (default: 500) & overlap (default: 100)
 └── Sequential chunk_index & page_number metadata tracking
            ↓
Database Persistence (process_medical_document)
 ├── Atomically cleans existing chunks (idempotent reprocessing)
 ├── Inserts DocumentChunk records with unique public IDs (CHK-YYYYMMDD-XXXX)
 └── Updates MedicalDocument status to 'completed' (or 'failed' on error)
```

---

## 2. Supported Formats & Extraction Strategy

| Format | Library | Strategy | Failure Handling |
|---|---|---|---|
| **`.pdf`** | `pypdf` | Page-by-page text extraction with page index tracking | Detects scanned/image-only PDFs and marks status as `failed` with descriptive OCR roadmap note. |
| **`.docx`** | `python-docx` | Iterates paragraphs and table cells in logical order | Fails gracefully on empty/corrupted files. |
| **`.txt`** | Standard library | UTF-8 with fallback replacement for non-standard encodings | Rejects empty files. |

---

## 3. Semantic Chunking & Token Estimation

- **Chunk Size**: `DOCUMENT_CHUNK_SIZE_TOKENS` (default: 500 tokens).
- **Chunk Overlap**: `DOCUMENT_CHUNK_OVERLAP_TOKENS` (default: 100 tokens).
- **Token Estimation**: Fast deterministic heuristic calculating character & whitespace density (`max(math.ceil(len(text)/4), math.ceil(len(words)*1.3))`).
- **Boundary Preservation**: Sentences and paragraphs are kept intact; chunks split along punctuation boundaries (`. `, `? `, `! `, `\n\n`) rather than breaking words mid-sentence.

---

## 4. Reprocessing & Chunk Idempotency

- **Endpoint**: `POST /api/v1/documents/{document_id}/reprocess`
- **Behavior**:
  - Re-executes extraction, text cleaning, and chunking against the stored file.
  - Safely deletes existing chunks associated with the document ID before saving new chunks.
  - Updates `page_count`, `total_chunks`, `processing_status`, and `updated_at`.
  - Prevents duplicate chunks upon repeated reprocessing calls.

---

## 5. Security & RBAC Considerations

1. **Patient Data Isolation**: Chunks inherit `patient_id` directly from the parent `MedicalDocument`.
2. **Access Restrictions**:
   - `patient`: Can view document metadata for their own records, but cannot access raw chunk endpoints (`403 Forbidden`).
   - `doctor`: Can view chunks only for patients under active clinical care.
   - `admin` / `healthcare_staff`: Full administrative access for clinical governance.
3. **No Clinical Data Leaks in Logs**: Sensitive extracted clinical text is never printed to logs or system traces.
