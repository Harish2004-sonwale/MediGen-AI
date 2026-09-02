# MediGen-AI: Visual Screenshot Capture Guide

This guide outlines the top 10 screenshots to capture for repository visual presentation, portfolio display, and documentation assets.

---

## Recommended Screenshot Assets

| # | View Name | URL / Path | Key Visual Elements to Capture |
|---|---|---|---|
| **1** | **Authentication & Role Selector** | `http://localhost:3000/login` | Clean login card, email/password fields, quick demo role selection chips (`Admin`, `Doctor`, `Patient`), and security badges. |
| **2** | **Clinical Dashboard & Facility Ribbon** | `http://localhost:3000/` | Main header with active facility ribbon (`FAC-METRO-MAIN`), quick clinical metrics, active patient counts, recent alerts, and navigation sidebar. |
| **3** | **Unified Patient Workspace** | `http://localhost:3000/patients` | Patient demographic summary banner, active allergies list, chronic condition tags, vital sign trend cards, and clinical timeline. |
| **4** | **CPOE & CDS Order Sets** | `http://localhost:3000/orders` | CPOE protocol bundle (e.g. *ACS Protocol* or *Sepsis Bundle*), order itemization, priority badges (`STAT`, `Routine`), and real-time CDS interaction check green status. |
| **5** | **Bedside eMAR & BCMA Scanner** | `http://localhost:3000/emar` | Bedside barcode scanner modal with 5-Rights verification checklist (Patient, Medication, Dose, Route, Time) and ISMP High-Alert dual witness badge. |
| **6** | **Interactive DICOM PACS Viewer** | `http://localhost:3000/imaging` | HTML5 Canvas DICOM CT/MRI scan with active Window/Level preset buttons (Lung, Soft Tissue, Bone), caliper distance measurement (`14.2 mm`), and AI lesion bounding box overlay. |
| **7** | **12-Lead Continuous ECG Monitor** | `http://localhost:3000/waveforms` | Real-time 12-lead continuous waveform strip display (Leads I-III, aVR-aVF, V1-V6) at 250 Hz with animated sweep bar and arrhythmia alert acknowledgment modal. |
| **8** | **Grounded AI Copilot & Source Citations** | `http://localhost:3000/copilot` | AI Copilot conversational drawer with clinical response and clickable, expandable source citation cards showing chunk similarity scores and document references. |
| **9** | **FHIR R4 & SMART App Launcher** | `http://localhost:3000/interoperability` | SMART on FHIR 2.0 app authorization card, scope permissions badge, and live formatted FHIR R4 Patient resource JSON export. |
| **10** | **System Observability & Architecture** | `http://localhost:8000/docs` & Metrics | FastAPI interactive Swagger UI alongside Prometheus metrics terminal output (`/api/v1/health/metrics/prometheus`). |

---

## Capture Recommendations

- **Browser Resolution**: 1920x1080 (Full HD) or 1440x900 for clean aspect ratios.
- **Theme**: Dark or clean neutral clinical theme matching the application design system.
- **Tool**: Standard OS screenshot utility (Windows: `Win + Shift + S`, macOS: `Cmd + Shift + 4`).
- **Storage Location**: Save captured images to `docs/assets/screenshots/` (e.g. `01_login.png`, `02_dashboard.png`, `06_pacs_viewer.png`, `07_ecg_waveforms.png`).
