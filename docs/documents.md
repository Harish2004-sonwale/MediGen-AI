# MediGen AI — Medical Document Management & Processing Module

This document provides technical documentation for the **Medical Document Upload & Management Module** in the MediGen AI Clinical Decision Support System.

---

## 1. Overview & Architecture

The Medical Document Management module provides secure, validated ingestion of clinical files (PDF, TXT, DOCX), enforces patient-isolated access control, and establishes the foundation for downstream text extraction, chunking, and Retrieval-Augmented Generation (RAG).

```text
Entity Relationship Hierarchy:

┌─────────────────┐             ┌─────────────────┐
│     Patient     │             │     Doctor      │
└────────┬────────┘             └────────┬────────┘
         │ 1                             │ 1
         │ (owns)                        │ (clinical authorization)
         │ *                             │ *
┌────────▼───────────────────────────────▼────────┐
│                Medical Document                 │
│      (document_id, title, type, file_info)      │
└────────┬────────────────────────────────────────┘
         │ 1
         │ (cascades)
         │ *
┌────────▼────────────────────────────────────────┐
│                 Document Chunk                  │
│       (chunk_index, page_number, content)       │
└─────────────────────────────────────────────────┘
```

---

## 2. Supported File Formats & Validation

| Extension | Allowed MIME Types | Validation Rules |
|---|---|---|
| `.pdf` | `application/pdf` | Valid extension, MIME type, max 10MB, non-empty |
| `.txt` | `text/plain`, `application/octet-stream` | Valid extension, MIME type, max 10MB, non-empty |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/msword`, `application/octet-stream` | Valid extension, MIME type, max 10MB, non-empty |

**Rejected Formats**: `.exe`, `.zip`, `.sh`, `.tar`, `.gz`, and all non-clinical formats.

---

## 3. Storage Design & Security

1. **Storage Directory**: Files are stored in `backend/data/medical_documents/` outside the web root.
2. **Safe Filenames**: Original filenames are preserved as metadata only. Disk filenames are generated uniquely using the public document ID (e.g. `DOCU-20260828-A1B2.pdf`).
3. **Path Traversal Prevention**: Storage paths are validated against `os.path.normpath` and checked against the storage root directory.
4. **Transaction Rollback Cleanup**: If a database error occurs after file write, the physical file is immediately purged from disk.

---

## 4. API Endpoints Reference

| Method | Endpoint | Allowed Roles | Description | Status Code |
|---|---|---|---|---|
| `POST` | `/api/v1/documents/upload` | Clinical, Admin, Patient | Upload medical document (`multipart/form-data`) | `201 Created` |
| `GET` | `/api/v1/documents` | Authenticated | List authorized documents (Filtered by patient, type, status) | `200 OK` |
| `GET` | `/api/v1/documents/{document_id}` | Authenticated | Retrieve safe document metadata | `200 OK` |
| `DELETE` | `/api/v1/documents/{document_id}` | Admin, Attending Doctor | Delete document and physical file | `200 OK` |

---

## 5. Authorization Matrix

| Role | Upload for Self | Upload for Patient | List Own | List Other's | View Metadata | Delete Document |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`admin`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`healthcare_staff`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`doctor`** | ❌ | ✅ (Patient under care) | ❌ | ✅ (Patient under care) | ✅ (Patient under care) | ✅ (Patient under care) |
| **`patient`** | ✅ | ❌ (403) | ✅ | ❌ (403/404) | ✅ (Own only) | ❌ (403) |
| **Unauthenticated** | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) | ❌ (401) |
