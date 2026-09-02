# MediGen-AI: 5–10 Minute Live Demonstration Script

This demonstration script provides a step-by-step walkthrough for presenting MediGen-AI to reviewers, clinical leaders, technical interviewers, or stakeholders.

---

## Pre-Demo Setup Checklist (1 Minute)

1. **Start Backend Server**:
   ```bash
   cd backend
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 3000
   ```
3. **Open Browser**: Navigate to `http://localhost:3000`.

---

## Demonstration Flow (8 Minutes)

### Step 1: Authentication & Role-Based Access Control (0:00 – 1:00)

- **What to Click**:
  - Open `http://localhost:3000`.
  - On the Login screen, notice the credentials form and quick role selector.
  - Enter `admin@hospital.org` / `AdminPassword123!` (or use Doctor credentials `doctor@hospital.org` / `DoctorPassword123!`).
  - Click **Sign In**.
- **What Reviewer Sees**:
  - Immediate redirect to the Clinical Dashboard.
  - Top navigation bar showing the logged-in user profile, active role badge (`Doctor` / `Admin`), and the active Facility Ribbon (`FAC-METRO-MAIN`).
- **Capability Demonstrated**:
  - JWT OAuth2 authentication, secure session storage, and role-based UI scoping.
- **What to Say**:
  > *"MediGen-AI implements full enterprise authentication with granular role-based access control. Here we log in as a clinical doctor. Notice the active facility ribbon at the top — this enforces multi-tenant and facility isolation across all clinical queries."*

---

### Step 2: Clinical Dashboard & Patient Selection (1:00 – 2:00)

- **What to Click**:
  - Click on **Patients** in the left sidebar.
  - Search or select a patient (e.g. `Eleanor Vance` or `John Doe`).
  - Click on the patient row to open the active patient workspace.
- **What Reviewer Sees**:
  - Comprehensive clinical summary: Patient demographics, MRN, date of birth, active allergies banner, active clinical problems, and recent vital signs.
- **Capability Demonstrated**:
  - Master patient demographic management and unified clinical context switching.
- **What to Say**:
  > *"Here is the patient summary. The system automatically highlights critical clinical alerts such as drug allergies and active chronic conditions. All subsequent actions in the sidebar are now scoped to this active patient context."*

---

### Step 3: Clinical Encounters & CPOE Order Placement (2:00 – 3:30)

- **What to Click**:
  - Click on **Encounters** in the patient workspace navigation.
  - Click **New Encounter** $\rightarrow$ Enter Chief Complaint: *"Acute retrosternal chest pain with exertion"* $\rightarrow$ Save.
  - Navigate to **Orders / CPOE**.
  - Search for an order set bundle: Select **Acute Coronary Syndrome (ACS) Protocol**.
  - Click **Place Orders**.
- **What Reviewer Sees**:
  - Order set automatically populates standard orders: Aspirin 325mg PO, ECG 12-Lead STAT, Troponin-I Q3H, and Cardiology Consult.
  - Real-time Clinical Decision Support (CDS) interaction check executes and confirms no contraindications.
- **Capability Demonstrated**:
  - Computerized Physician Order Entry (CPOE), multidisciplinary protocol bundles, and automated drug-allergy / drug-drug safety checks.
- **What to Say**:
  > *"MediGen-AI supports standardized CPOE order sets. When ordering the Acute Coronary Syndrome protocol, the system bundles medication, laboratory, and cardiology consults while proactively executing interaction checks before submission."*

---

### Step 4: Bedside Medication Administration (eMAR & BCMA) (3:30 – 4:30)

- **What to Click**:
  - Navigate to **Medications / eMAR**.
  - Click **Barcode Scanner (BCMA)**.
  - Simulate scanning the patient wristband (`PAT-001`) and medication barcode (`NDC: 00071-0156-23 - Atorvastatin 40mg`).
  - Click **Verify & Administer**.
- **What Reviewer Sees**:
  - 5-Rights verification checklist turns green (Right Patient, Right Drug, Right Dose, Right Route, Right Time).
  - Administration timestamp, administering clinician ID, and verified status update immediately in the electronic medication administration record.
- **Capability Demonstrated**:
  - Barcode Medication Administration (BCMA), ISMP safety compliance, and closed-loop medication tracking.
- **What to Say**:
  > *"For medication safety, MediGen-AI features a closed-loop Barcode Medication Administration engine. It verifies all 5 rights at bedside and enforces dual-clinician sign-off for high-alert medications."*

---

### Step 5: DICOM PACS Diagnostic Viewer (4:30 – 5:30)

- **What to Click**:
  - Navigate to **Imaging / PACS**.
  - Select a study (e.g. `High Resolution Chest CT`).
  - Click on the interactive DICOM viewer canvas.
  - Select Window/Level Presets: Click **Lung Window**, then **Soft Tissue Window**.
  - Toggle the **AI Findings** overlay switch.
  - Use the caliper tool to click two points on the scan.
- **What Reviewer Sees**:
  - Canvas instantly updates pixel contrast for lung parenchyma vs mediastinal soft tissue.
  - AI-detected lesion bounding box appears with confidence score (`92% - Pulmonary Nodule`) and review buttons (Confirm / Reject).
  - Caliper displays calibrated distance in millimeters (`14.2 mm`).
- **Capability Demonstrated**:
  - DICOM PS3.18 QIDO/WADO web imaging, client-side window/level transfer function calculation, millimeter distance measurement, and radiologist AI collaboration workflow.
- **What to Say**:
  > *"Here is our HTML5 DICOM PACS viewer. It runs client-side window/level calibration with standard clinical presets, distance calipers, and integrates AI lesion overlays where clinicians can confirm or amend detected findings."*

---

### Step 6: 12-Lead Continuous ECG & Arrhythmia Alarms (5:30 – 6:30)

- **What to Click**:
  - Navigate to **Waveforms / ECG Telemetry**.
  - Select an active 12-Lead ICU monitoring session.
  - Observe the continuous multi-lead ECG strip playback (Leads I, II, III, aVR, aVL, aVF, V1-V6).
  - Click **Trigger Arrhythmia Simulation** (e.g. *Ventricular Tachycardia*).
  - When the red alarm modal appears, enter Clinician Action: *"Bedside evaluation complete. Amiodarone IV bolus administered"* and click **Acknowledge**.
- **What Reviewer Sees**:
  - Real-time continuous sweep bar animating all 12 leads at 250 Hz.
  - Critical alarm banner flashes with heart rate (180 BPM) and arrhythmia classification.
  - Acknowledgment modal captures clinician intervention notes and initiates automated 5-minute alarm debouncing.
- **Capability Demonstrated**:
  - High-frequency multi-lead physiological signal rendering, real-time arrhythmia detection, and closed-loop alarm management.
- **What to Say**:
  > *"For intensive care telemetry, MediGen-AI renders full 12-lead continuous ECG waveforms at 250 Hz. The engine includes debounced arrhythmia alerts for V-Tach, STEMI, and AFib with mandatory clinician action audit logging."*

---

### Step 7: Grounded Clinical RAG & AI Copilot (6:30 – 7:30)

- **What to Click**:
  - Click the **AI Copilot** floating drawer or open the RAG workspace.
  - Ask: *"What are the standard monitoring guidelines and electrolyte precautions during high-dose intravenous loop diuretic therapy?"*
  - Click **Send**.
- **What Reviewer Sees**:
  - Formatted clinical synthesis answering the query.
  - Clickable citation cards citing specific hospital clinical guideline chunks with similarity scores.
- **Capability Demonstrated**:
  - Ephemeral vector retrieval (ChromaDB), hallucination prevention, and verified clinical citations.
- **What to Say**:
  > *"Our Clinical AI is grounded in retrieval-augmented generation. It retrieves specific document chunks and presents verifiable citations so clinicians can immediately audit the underlying medical source literature."*

---

### Step 8: Interoperability, Observability & Architecture Wrap-Up (7:30 – 8:30)

- **What to Click**:
  - Navigate to **Interoperability / FHIR** $\rightarrow$ View FHIR R4 JSON export for the patient.
  - Open Swagger at `http://localhost:8000/docs` or Prometheus metrics at `http://localhost:8000/api/v1/health/metrics/prometheus`.
- **What Reviewer Sees**:
  - Standard FHIR R4 JSON representation.
  - Prometheus metrics stream showing request latency histogram buckets, database pool stats, and uptime.
- **Capability Demonstrated**:
  - HL7 FHIR R4 compliance, SMART on FHIR 2.0 readiness, and production-grade OpenTelemetry observability.
- **What to Say**:
  > *"MediGen-AI is fully interoperable with modern health tech ecosystems via FHIR R4 and SMART on FHIR. The platform is hardened with OpenTelemetry W3C distributed tracing, Prometheus metrics, and automated disaster recovery failover."*

---

## Q&A Quick Reference

- **Q: How does the system handle patient privacy and HIPAA compliance?**
  - *A: Full tenant isolation, role-based scoping, automated PHI sanitization in logs, and HMAC-SHA256 tamper-evident audit logging.*
- **Q: Can this run in production with live cloud infrastructure?**
  - *A: Yes. The repository includes multi-stage Dockerfiles, Nginx edge proxy configurations, and `docker-compose.prod.yml` ready for container orchestration.*
