import React, { useState, useEffect, useRef } from 'react';
import { pacsApi, waveformsApi } from '../../api/client';
import {
  DICOMStudyItem,
  DICOMSeriesItem,
  DICOMInstanceItem,
  AILesionFindingItem,
  ECGSessionItem,
  ArrhythmiaAlertItem,
  ArrhythmiaEventType,
  AIFindingReviewStatus,
} from '../../types';

interface Props {
  patientId: string;
}

export const DICOMPACSViewerWorkspace: React.FC<Props> = ({ patientId }) => {
  const [activeTab, setActiveTab] = useState<'pacs' | 'waveform' | 'alerts' | 'ingest'>('pacs');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // PACS State
  const [studies, setStudies] = useState<DICOMStudyItem[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<DICOMStudyItem | null>(null);
  const [selectedSeries, setSelectedSeries] = useState<DICOMSeriesItem | null>(null);
  const [selectedInstance, setSelectedInstance] = useState<DICOMInstanceItem | null>(null);

  // PACS Viewport Controls
  const [windowCenter, setWindowCenter] = useState<number>(40);
  const [windowWidth, setWindowWidth] = useState<number>(400);
  const [zoom, setZoom] = useState<number>(1.0);
  const [invert, setInvert] = useState<boolean>(false);
  const [showAiOverlay, setShowAiOverlay] = useState<boolean>(true);
  const [showDicomMetadata, setShowDicomMetadata] = useState<boolean>(false);
  const [activeTool, setActiveTool] = useState<'pan' | 'zoom' | 'caliper'>('pan');
  const [caliperPoints, setCaliperPoints] = useState<{ x: number; y: number }[]>([]);
  const [caliperDistanceMm, setCaliperDistanceMm] = useState<number | null>(null);

  // Waveform State
  const [ecgSessions, setEcgSessions] = useState<ECGSessionItem[]>([]);
  const [selectedEcgSession, setSelectedEcgSession] = useState<ECGSessionItem | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackTimeSec, setPlaybackTimeSec] = useState<number>(0);
  const [gainMmPerMv, setGainMmPerMv] = useState<number>(10);
  const [alerts, setAlerts] = useState<ArrhythmiaAlertItem[]>([]);

  // Modals
  const [ackAlertModal, setAckAlertModal] = useState<ArrhythmiaAlertItem | null>(null);
  const [clinicianActionText, setClinicianActionText] = useState<string>('');

  // Ingest Form
  const [newStudyModality, setNewStudyModality] = useState<string>('CT');
  const [newStudyDesc, setNewStudyDesc] = useState<string>('High-Resolution Chest CT with IV Contrast');
  const [newStudySite, setNewStudySite] = useState<string>('CHEST');
  const [newEcgRhythm, setNewEcgRhythm] = useState<ArrhythmiaEventType>('stemi_elevation');
  const [newEcgHeartRate, setNewEcgHeartRate] = useState<number>(95);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const ecgCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // Fetch initial PACS and Waveforms
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [studiesResp, ecgResp, alertsResp] = await Promise.all([
        pacsApi.queryStudies(patientId),
        waveformsApi.getPatientSessions(patientId),
        waveformsApi.listActiveAlerts(),
      ]);

      setStudies(studiesResp.studies);
      if (studiesResp.studies.length > 0) {
        const firstStudy = studiesResp.studies[0];
        setSelectedStudy(firstStudy);
        if (firstStudy.series_list.length > 0) {
          const firstSeries = firstStudy.series_list[0];
          setSelectedSeries(firstSeries);
          setWindowCenter(firstSeries.window_center_default);
          setWindowWidth(firstSeries.window_width_default);
          if (firstSeries.instances.length > 0) {
            setSelectedInstance(firstSeries.instances[0]);
          }
        }
      }

      setEcgSessions(ecgResp.sessions);
      if (ecgResp.sessions.length > 0) {
        setSelectedEcgSession(ecgResp.sessions[0]);
      }
      setAlerts(alertsResp);
    } catch (err: any) {
      setError(err.message || 'Failed to load PACS imaging or waveform telemetry data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [patientId]);

  // DICOM Canvas Renderer
  useEffect(() => {
    if (!canvasRef.current || !selectedInstance) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Fill background with medical black
    ctx.fillStyle = '#08080c';
    ctx.fillRect(0, 0, w, h);

    // Draw simulated medical DICOM anatomy slice
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.38 * zoom;

    // Apply Window / Level mapping to anatomical contours
    const brightness = Math.max(0.1, Math.min(2.0, (windowWidth / 400.0)));
    const contrast = Math.max(0.2, Math.min(2.5, 100.0 / Math.max(10, Math.abs(windowCenter) + 50)));

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
    const grad = ctx.createRadialGradient(cx, cy, radius * 0.1, cx, cy, radius);
    if (!invert) {
      grad.addColorStop(0, `rgba(${Math.floor(180 * contrast)}, ${Math.floor(180 * contrast)}, ${Math.floor(200 * contrast)}, ${0.85 * brightness})`);
      grad.addColorStop(0.5, `rgba(${Math.floor(110 * contrast)}, ${Math.floor(115 * contrast)}, ${Math.floor(130 * contrast)}, ${0.65 * brightness})`);
      grad.addColorStop(0.8, `rgba(${Math.floor(60 * contrast)}, ${Math.floor(60 * contrast)}, ${Math.floor(75 * contrast)}, ${0.45 * brightness})`);
      grad.addColorStop(1, 'rgba(15, 15, 25, 0.2)');
    } else {
      grad.addColorStop(0, `rgba(${Math.floor(60 * contrast)}, ${Math.floor(60 * contrast)}, ${Math.floor(75 * contrast)}, ${0.45 * brightness})`);
      grad.addColorStop(0.5, `rgba(${Math.floor(110 * contrast)}, ${Math.floor(115 * contrast)}, ${Math.floor(130 * contrast)}, ${0.65 * brightness})`);
      grad.addColorStop(1, `rgba(${Math.floor(200 * contrast)}, ${Math.floor(200 * contrast)}, ${Math.floor(220 * contrast)}, ${0.85 * brightness})`);
    }
    ctx.fillStyle = grad;
    ctx.fill();

    // Draw anatomical bone / parenchyma structures
    ctx.strokeStyle = invert ? '#111' : '#eee';
    ctx.lineWidth = 3 * zoom;
    ctx.beginPath();
    ctx.ellipse(cx - radius * 0.35, cy, radius * 0.3, radius * 0.45, 0, 0, 2 * Math.PI);
    ctx.ellipse(cx + radius * 0.35, cy, radius * 0.3, radius * 0.45, 0, 0, 2 * Math.PI);
    ctx.stroke();

    // AI Overlay Findings
    if (showAiOverlay && selectedInstance.ai_findings) {
      selectedInstance.ai_findings.forEach((finding) => {
        const coords = finding.coordinates_json;
        const boxX = cx + (coords.x - 256) * (radius / 256);
        const boxY = cy + (coords.y - 256) * (radius / 256);
        const boxW = coords.w * (radius / 256);
        const boxH = coords.h * (radius / 256);

        // Heatmap Aura
        ctx.fillStyle = 'rgba(239, 68, 68, 0.25)';
        ctx.beginPath();
        ctx.arc(boxX + boxW / 2, boxY + boxH / 2, Math.max(boxW, boxH) * 0.85, 0, 2 * Math.PI);
        ctx.fill();

        // Bounding Box
        ctx.strokeStyle = finding.clinician_review_status === 'confirmed' ? '#10b981' : '#ef4444';
        ctx.lineWidth = 2.5;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(boxX, boxY, boxW, boxH);
        ctx.setLineDash([]);

        // Label
        ctx.fillStyle = finding.clinician_review_status === 'confirmed' ? '#10b981' : '#ef4444';
        ctx.font = 'bold 12px monospace';
        ctx.fillText(
          `${finding.lesion_type} (${(finding.confidence_score * 100).toFixed(0)}%)`,
          boxX,
          boxY - 8
        );
      });
    }

    // Draw Caliper Measurement
    if (caliperPoints.length > 0) {
      ctx.fillStyle = '#38bdf8';
      caliperPoints.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI);
        ctx.fill();
      });

      if (caliperPoints.length === 2) {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(caliperPoints[0].x, caliperPoints[0].y);
        ctx.lineTo(caliperPoints[1].x, caliperPoints[1].y);
        ctx.stroke();

        const midX = (caliperPoints[0].x + caliperPoints[1].x) / 2;
        const midY = (caliperPoints[0].y + caliperPoints[1].y) / 2;
        ctx.fillStyle = '#38bdf8';
        ctx.font = 'bold 13px sans-serif';
        if (caliperDistanceMm !== null) {
          ctx.fillText(`${caliperDistanceMm.toFixed(1)} mm`, midX + 10, midY - 5);
        }
      }
    }

    // Viewport HUD Metadata
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px monospace';
    ctx.fillText(`W: ${windowWidth.toFixed(0)} L: ${windowCenter.toFixed(0)} | Zoom: ${(zoom * 100).toFixed(0)}%`, 16, h - 20);
    ctx.fillText(`Modality: ${selectedSeries?.modality || 'CT'} | Slices: ${selectedSeries?.number_of_instances || 1}`, 16, 24);
    ctx.fillText(`Lossless DICOM / WADO-RS`, w - 180, 24);

    ctx.restore();
  }, [
    selectedInstance,
    selectedSeries,
    windowCenter,
    windowWidth,
    zoom,
    invert,
    showAiOverlay,
    caliperPoints,
    caliperDistanceMm,
  ]);

  // Handle Caliper clicks
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (activeTool !== 'caliper' || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (caliperPoints.length >= 2) {
      setCaliperPoints([{ x, y }]);
      setCaliperDistanceMm(null);
    } else {
      const nextPoints = [...caliperPoints, { x, y }];
      setCaliperPoints(nextPoints);
      if (nextPoints.length === 2) {
        const dx = nextPoints[1].x - nextPoints[0].x;
        const dy = nextPoints[1].y - nextPoints[0].y;
        const pixelDist = Math.sqrt(dx * dx + dy * dy);
        const pixelSpacing = selectedSeries?.pixel_spacing_row_mm || 0.68;
        const distMm = (pixelDist / zoom) * pixelSpacing;
        setCaliperDistanceMm(distMm);
      }
    }
  };

  // Waveform Timer Loop
  useEffect(() => {
    let interval: any = null;
    if (isPlaying && selectedEcgSession) {
      interval = setInterval(() => {
        setPlaybackTimeSec((prev) => {
          const maxDur = selectedEcgSession.duration_seconds || 10;
          return prev + 0.05 >= maxDur ? 0 : prev + 0.05;
        });
      }, 50);
    }
    return () => clearInterval(interval);
  }, [isPlaying, selectedEcgSession]);

  // Multi-Lead ECG Canvas Renderer
  useEffect(() => {
    if (!ecgCanvasRef.current || !selectedEcgSession) return;
    const canvas = ecgCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Draw standard 25mm/s medical ECG pink grid background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Minor grid (1mm)
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 10) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 10) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Major grid (5mm)
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1.0;
    for (let x = 0; x < w; x += 50) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 50) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    const leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
    const rowHeight = h / 6;
    const colWidth = w / 2;
    const samplesPerSec = selectedEcgSession.sample_rate_hz || 250;
    const startIdx = Math.floor(playbackTimeSec * samplesPerSec);
    const windowSamples = Math.floor(2.5 * samplesPerSec); // 2.5 second window

    leads.forEach((lead, idx) => {
      const col = idx < 6 ? 0 : 1;
      const row = idx % 6;
      const originX = col * colWidth;
      const originY = row * rowHeight + rowHeight / 2;

      // Draw Lead Label
      ctx.fillStyle = '#38bdf8';
      ctx.font = 'bold 12px monospace';
      ctx.fillText(lead, originX + 12, originY - 14);

      const leadData = selectedEcgSession.multi_lead_samples_json[lead] || [];
      if (leadData.length === 0) return;

      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 1.8;
      ctx.beginPath();

      for (let i = 0; i < windowSamples; i++) {
        const sampleIdx = (startIdx + i) % leadData.length;
        const voltage = leadData[sampleIdx] || 0.0;
        const px = originX + 45 + (i / windowSamples) * (colWidth - 60);
        const py = originY - voltage * (gainMmPerMv * 3.5);

        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    });

    // Time Scrubber Cursor
    const cursorX = 45 + ((playbackTimeSec % 2.5) / 2.5) * (colWidth - 60);
    ctx.strokeStyle = 'rgba(239, 68, 68, 0.75)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, h);
    ctx.moveTo(colWidth + cursorX, 0);
    ctx.lineTo(colWidth + cursorX, h);
    ctx.stroke();
  }, [selectedEcgSession, playbackTimeSec, gainMmPerMv]);

  // Window/Level Presets
  const applyPreset = (preset: 'soft_tissue' | 'lung' | 'bone' | 'brain' | 'stroke') => {
    switch (preset) {
      case 'soft_tissue':
        setWindowWidth(400);
        setWindowCenter(40);
        break;
      case 'lung':
        setWindowWidth(1500);
        setWindowCenter(-600);
        break;
      case 'bone':
        setWindowWidth(1800);
        setWindowCenter(400);
        break;
      case 'brain':
        setWindowWidth(80);
        setWindowCenter(40);
        break;
      case 'stroke':
        setWindowWidth(40);
        setWindowCenter(40);
        break;
    }
  };

  // Review AI Finding
  const handleReviewFinding = async (findingId: string, newStatus: AIFindingReviewStatus) => {
    try {
      const updated = await pacsApi.reviewFinding(findingId, {
        status: newStatus,
        review_notes: `Clinician ${newStatus} this finding during interactive review.`,
      });
      if (selectedInstance) {
        setSelectedInstance({
          ...selectedInstance,
          ai_findings: selectedInstance.ai_findings.map((f) => (f.finding_id === findingId ? updated : f)),
        });
      }
    } catch (err: any) {
      alert(`Review failed: ${err.message}`);
    }
  };

  // Acknowledge Alert
  const handleAcknowledgeAlert = async () => {
    if (!ackAlertModal || !clinicianActionText.trim()) return;
    try {
      const updated = await waveformsApi.acknowledgeAlert(ackAlertModal.alert_id, {
        clinician_action_taken: clinicianActionText,
        status: 'acknowledged',
      });
      setAlerts(alerts.map((a) => (a.alert_id === updated.alert_id ? updated : a)));
      setAckAlertModal(null);
      setClinicianActionText('');
    } catch (err: any) {
      alert(`Failed to acknowledge alert: ${err.message}`);
    }
  };

  // Ingest New Study
  const handleCreateStudy = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const study = await pacsApi.createStudy({
        patient_id: patientId,
        study_description: newStudyDesc,
        modality: newStudyModality,
        body_site: newStudySite,
      });
      setStudies([study, ...studies]);
      setSelectedStudy(study);
      if (study.series_list.length > 0) {
        setSelectedSeries(study.series_list[0]);
        if (study.series_list[0].instances.length > 0) {
          setSelectedInstance(study.series_list[0].instances[0]);
        }
      }
      setActiveTab('pacs');
    } catch (err: any) {
      alert(`Study creation failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Ingest New Waveform Session
  const handleIngestEcg = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const session = await waveformsApi.ingestSession({
        patient_id: patientId,
        rhythm_state: newEcgRhythm,
        heart_rate_bpm: newEcgHeartRate,
      });
      setEcgSessions([session, ...ecgSessions]);
      setSelectedEcgSession(session);
      const freshAlerts = await waveformsApi.listActiveAlerts();
      setAlerts(freshAlerts);
      setActiveTab('waveform');
    } catch (err: any) {
      alert(`Waveform ingestion failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading && studies.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-3"></div>
        <p>Loading DICOM PACS studies & ICU telemetry streams...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pacs-waveforms-workspace">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-2xl">🖼️</span>
            <h2 className="text-xl font-bold text-white tracking-wide">
              DICOM PACS Medical Vision & Real-Time Waveform Telemetry
            </h2>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            DICOM PS3.18 WADO-RS diagnostic viewer with window/level calibration, AI lesion overlays & 12-lead ICU ECG continuous monitor.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
          <button
            onClick={() => setActiveTab('pacs')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === 'pacs' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🖼️ DICOM PACS Viewer
          </button>
          <button
            onClick={() => setActiveTab('waveform')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === 'waveform' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📈 12-Lead ECG Monitor
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === 'alerts' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            🚨 Arrhythmia Alarms
            {alerts.filter((a) => a.status === 'active').length > 0 && (
              <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold animate-pulse">
                {alerts.filter((a) => a.status === 'active').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('ingest')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              activeTab === 'ingest' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ➕ Ingest / Simulate
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-200 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* TAB 1: DICOM PACS VIEWER */}
      {activeTab === 'pacs' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Studies & Series Explorer */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
                Patient Studies ({studies.length})
              </h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {studies.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => {
                      setSelectedStudy(s);
                      if (s.series_list.length > 0) {
                        setSelectedSeries(s.series_list[0]);
                        if (s.series_list[0].instances.length > 0) {
                          setSelectedInstance(s.series_list[0].instances[0]);
                        }
                      }
                    }}
                    className={`p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedStudy?.id === s.id
                        ? 'bg-indigo-950/60 border-indigo-500 text-white shadow-md'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-300 hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs bg-slate-700 px-1.5 py-0.5 rounded text-indigo-300">
                        {s.modality}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {new Date(s.study_datetime).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-xs font-semibold mt-1 truncate">{s.study_description}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                      UID: {s.study_instance_uid.slice(-16)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Series & Instances Selector */}
            {selectedStudy && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
                  Series & Instances
                </h3>
                <div className="space-y-2">
                  {selectedStudy.series_list.map((ser) => (
                    <div
                      key={ser.id}
                      onClick={() => {
                        setSelectedSeries(ser);
                        if (ser.instances.length > 0) setSelectedInstance(ser.instances[0]);
                      }}
                      className={`p-2.5 rounded-lg border cursor-pointer text-xs ${
                        selectedSeries?.id === ser.id
                          ? 'bg-emerald-950/50 border-emerald-500 text-white'
                          : 'bg-slate-800/40 border-slate-700/50 text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{ser.series_description}</span>
                        <span className="text-[10px] bg-slate-700 px-1 rounded text-slate-300">
                          {ser.number_of_instances} img
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1">
                        Thk: {ser.slice_thickness_mm}mm | Spacing: {ser.pixel_spacing_row_mm}mm
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Central Diagnostic DICOM Viewport */}
          <div className="lg:col-span-3 space-y-4">
            {/* Viewport Action Toolbar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
              {/* Presets */}
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400 font-semibold mr-1">Presets:</span>
                <button
                  onClick={() => applyPreset('soft_tissue')}
                  className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Soft Tissue
                </button>
                <button
                  onClick={() => applyPreset('lung')}
                  className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Lung
                </button>
                <button
                  onClick={() => applyPreset('bone')}
                  className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Bone
                </button>
                <button
                  onClick={() => applyPreset('brain')}
                  className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Brain
                </button>
                <button
                  onClick={() => applyPreset('stroke')}
                  className="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Stroke
                </button>
              </div>

              {/* Tools */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setActiveTool('pan');
                    setCaliperPoints([]);
                    setCaliperDistanceMm(null);
                  }}
                  className={`px-2.5 py-1 text-xs rounded font-semibold border ${
                    activeTool === 'pan'
                      ? 'bg-indigo-600 text-white border-indigo-500'
                      : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}
                >
                  🖐️ Pan
                </button>
                <button
                  onClick={() => {
                    setActiveTool('caliper');
                  }}
                  className={`px-2.5 py-1 text-xs rounded font-semibold border ${
                    activeTool === 'caliper'
                      ? 'bg-cyan-600 text-white border-cyan-500'
                      : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}
                >
                  📏 Caliper (mm)
                </button>
                <button
                  onClick={() => setInvert(!invert)}
                  className={`px-2.5 py-1 text-xs rounded font-semibold border ${
                    invert ? 'bg-amber-600 text-white border-amber-500' : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}
                >
                  🔄 Invert
                </button>
                <button
                  onClick={() => setShowAiOverlay(!showAiOverlay)}
                  className={`px-2.5 py-1 text-xs rounded font-semibold border ${
                    showAiOverlay ? 'bg-red-600 text-white border-red-500' : 'bg-slate-800 text-slate-300 border-slate-700'
                  }`}
                >
                  🎯 AI Overlay
                </button>
                <button
                  onClick={() => setShowDicomMetadata(true)}
                  className="px-2.5 py-1 text-xs rounded font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                >
                  🏷️ DICOM Tags
                </button>
              </div>
            </div>

            {/* Canvas Viewport */}
            <div className="relative bg-black rounded-xl border border-slate-800 overflow-hidden shadow-2xl flex items-center justify-center min-h-[460px]">
              <canvas
                ref={canvasRef}
                width={512}
                height={512}
                onClick={handleCanvasClick}
                className="cursor-crosshair max-w-full"
              />

              {/* Viewport Sliders Floating Panel */}
              <div className="absolute top-4 right-4 bg-slate-900/80 backdrop-blur-md p-3 rounded-lg border border-slate-700/80 space-y-2.5 text-xs text-slate-300 shadow-xl w-48">
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span>Window (W)</span>
                    <span className="font-mono text-indigo-400">{windowWidth}</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="2000"
                    value={windowWidth}
                    onChange={(e) => setWindowWidth(Number(e.target.value))}
                    className="w-full h-1 bg-slate-700 rounded appearance-none cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span>Level (L)</span>
                    <span className="font-mono text-indigo-400">{windowCenter}</span>
                  </div>
                  <input
                    type="range"
                    min="-800"
                    max="800"
                    value={windowCenter}
                    onChange={(e) => setWindowCenter(Number(e.target.value))}
                    className="w-full h-1 bg-slate-700 rounded appearance-none cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span>Zoom</span>
                    <span className="font-mono text-indigo-400">{(zoom * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.5"
                    max="2.5"
                    step="0.1"
                    value={zoom}
                    onChange={(e) => setZoom(Number(e.target.value))}
                    className="w-full h-1 bg-slate-700 rounded appearance-none cursor-pointer"
                  />
                </div>
                <button
                  onClick={() => {
                    setZoom(1.0);
                    setInvert(false);
                    setCaliperPoints([]);
                    setCaliperDistanceMm(null);
                  }}
                  className="w-full py-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Reset Viewport
                </button>
              </div>
            </div>

            {/* AI Findings Review Panel */}
            {selectedInstance && selectedInstance.ai_findings.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-3">
                  <span className="text-red-400">🎯</span>
                  Persisted AI Vision Findings ({selectedInstance.ai_findings.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {selectedInstance.ai_findings.map((f) => (
                    <div
                      key={f.id}
                      className="p-3 bg-slate-800/80 rounded-lg border border-slate-700 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm text-red-400">{f.lesion_type}</span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                              f.clinician_review_status === 'confirmed'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                                : f.clinician_review_status === 'rejected'
                                ? 'bg-red-950 text-red-300 border border-red-700'
                                : 'bg-amber-950 text-amber-300 border border-amber-700'
                            }`}
                          >
                            {f.clinician_review_status}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1">Location: {f.anatomical_location}</p>
                        <p className="text-xs text-slate-400">
                          Confidence: {(f.confidence_score * 100).toFixed(1)}% | Model: {f.model_name}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-700">
                        <button
                          onClick={() => handleReviewFinding(f.finding_id, 'confirmed')}
                          className="flex-1 py-1 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-all"
                        >
                          ✓ Confirm Finding
                        </button>
                        <button
                          onClick={() => handleReviewFinding(f.finding_id, 'rejected')}
                          className="flex-1 py-1 text-xs font-semibold bg-red-800 hover:bg-red-700 text-white rounded transition-all"
                        >
                          ✕ Reject Finding
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: MULTI-LEAD ECG MONITOR */}
      {activeTab === 'waveform' && (
        <div className="space-y-4">
          {/* Waveform Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`px-4 py-2 rounded-lg font-bold text-sm shadow-md transition-all ${
                  isPlaying
                    ? 'bg-amber-600 hover:bg-amber-500 text-white'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                }`}
              >
                {isPlaying ? '⏸ Pause Telemetry' : '▶ Resume Live Feed'}
              </button>

              <div className="text-xs text-slate-300">
                <span className="text-slate-400">Heart Rate: </span>
                <span className="font-mono font-bold text-base text-emerald-400">
                  {selectedEcgSession?.heart_rate_bpm || 75} BPM
                </span>
              </div>

              <div className="text-xs text-slate-300">
                <span className="text-slate-400">Rhythm: </span>
                <span className="font-bold text-indigo-400 uppercase">
                  {selectedEcgSession?.current_rhythm_state.replace('_', ' ')}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <span>Gain:</span>
                {[5, 10, 20].map((g) => (
                  <button
                    key={g}
                    onClick={() => setGainMmPerMv(g)}
                    className={`px-2 py-1 rounded text-xs font-mono font-semibold border ${
                      gainMmPerMv === g
                        ? 'bg-indigo-600 text-white border-indigo-500'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {g} mm/mV
                  </button>
                ))}
              </div>

              <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                Sweep: 25 mm/s | 250 Hz
              </span>
            </div>
          </div>

          {/* 12-Lead Continuous Strip Viewport */}
          <div className="bg-slate-950 rounded-xl border border-slate-800 p-3 shadow-2xl overflow-x-auto">
            <canvas
              ref={ecgCanvasRef}
              width={1000}
              height={520}
              className="w-full rounded-lg"
            />
          </div>

          {/* Active Arrhythmia Alarms Banner */}
          {selectedEcgSession && selectedEcgSession.alerts.length > 0 && (
            <div className="bg-red-950/80 border border-red-700 rounded-xl p-4 text-red-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl animate-bounce">🚨</span>
                <div>
                  <h4 className="font-bold text-sm text-white uppercase tracking-wider">
                    Critical Arrhythmia Alert Triggered: {selectedEcgSession.alerts[0].event_type.replace('_', ' ')}
                  </h4>
                  <p className="text-xs text-red-300 mt-0.5">
                    {selectedEcgSession.alerts[0].alert_description} (Lead: {selectedEcgSession.alerts[0].lead_involved})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAckAlertModal(selectedEcgSession.alerts[0])}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold shadow-lg"
              >
                Acknowledge Alarm
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ARRHYTHMIA ALARMS CONSOLE */}
      {activeTab === 'alerts' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <h3 className="text-base font-bold text-white tracking-wide">
            ICU Arrhythmia Alarms & Clinical Acknowledgments ({alerts.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/80 text-slate-400 uppercase font-semibold border-b border-slate-700">
                <tr>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Lead</th>
                  <th className="py-3 px-4">Heart Rate</th>
                  <th className="py-3 px-4">Triggered At</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-800/50">
                    <td className="py-3 px-4 font-bold text-white capitalize">
                      {a.event_type.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                          a.severity === 'critical'
                            ? 'bg-red-950 text-red-300 border border-red-700'
                            : 'bg-amber-950 text-amber-300 border border-amber-700'
                        }`}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-indigo-300">{a.lead_involved}</td>
                    <td className="py-3 px-4 font-mono">{a.heart_rate_bpm} BPM</td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(a.triggered_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                          a.status === 'active'
                            ? 'bg-red-900/60 text-red-200 animate-pulse'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {a.status === 'active' ? (
                        <button
                          onClick={() => setAckAlertModal(a)}
                          className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold"
                        >
                          Acknowledge
                        </button>
                      ) : (
                        <span className="text-slate-500 text-[11px]">Acknowledged</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: INGEST / SIMULATOR */}
      {activeTab === 'ingest' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* DICOM Study Ingestion */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4">
              🖼️ Ingest DICOM PACS Study
            </h3>
            <form onSubmit={handleCreateStudy} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Study Description</label>
                <input
                  type="text"
                  value={newStudyDesc}
                  onChange={(e) => setNewStudyDesc(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Modality</label>
                  <select
                    value={newStudyModality}
                    onChange={(e) => setNewStudyModality(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    <option value="CT">CT (Computed Tomography)</option>
                    <option value="MR">MR (Magnetic Resonance)</option>
                    <option value="CR">CR (Computed Radiography)</option>
                    <option value="DX">DX (Digital X-Ray)</option>
                    <option value="US">US (Ultrasound)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Body Site</label>
                  <select
                    value={newStudySite}
                    onChange={(e) => setNewStudySite(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                  >
                    <option value="CHEST">CHEST</option>
                    <option value="HEAD_BRAIN">HEAD / BRAIN</option>
                    <option value="ABDOMEN">ABDOMEN</option>
                    <option value="PELVIS">PELVIS</option>
                    <option value="SPINE">SPINE</option>
                  </select>
                </div>
              </div>
              <button
                type="submit"
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg shadow"
              >
                Register & Stream DICOM Study
              </button>
            </form>
          </div>

          {/* ICU Telemetry Ingestion */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4">
              📈 Ingest 12-Lead ICU Telemetry Stream
            </h3>
            <form onSubmit={handleIngestEcg} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Rhythm Pattern</label>
                <select
                  value={newEcgRhythm}
                  onChange={(e) => setNewEcgRhythm(e.target.value as ArrhythmiaEventType)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                >
                  <option value="normal_sinus_rhythm">Normal Sinus Rhythm (NSR)</option>
                  <option value="stemi_elevation">Anterior STEMI (ST-Elevation in V2-V4)</option>
                  <option value="atrial_fibrillation">Atrial Fibrillation (Rapid Irregular)</option>
                  <option value="ventricular_tachycardia">Ventricular Tachycardia (Wide QRS Monomorphic)</option>
                  <option value="asystole">Asystole (Flatline)</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Heart Rate (BPM)</label>
                <input
                  type="number"
                  min="30"
                  max="220"
                  value={newEcgHeartRate}
                  onChange={(e) => setNewEcgHeartRate(Number(e.target.value))}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                />
              </div>
              <button
                type="submit"
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg shadow"
              >
                Stream Telemetry & Run Debounced Alarm Engine
              </button>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DICOM Metadata Tags */}
      {showDicomMetadata && selectedStudy && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>🏷️</span> Standard DICOM PS3.18 Metadata
              </h3>
              <button
                onClick={() => setShowDicomMetadata(false)}
                className="text-slate-400 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs text-slate-300 font-mono">
              <div className="bg-slate-800/80 p-2.5 rounded border border-slate-700">
                <span className="text-indigo-400 font-semibold">(0020,000D) StudyInstanceUID:</span>{' '}
                {selectedStudy.study_instance_uid}
              </div>
              <div className="bg-slate-800/80 p-2.5 rounded border border-slate-700">
                <span className="text-indigo-400 font-semibold">(0008,0050) AccessionNumber:</span>{' '}
                {selectedStudy.accession_number}
              </div>
              <div className="bg-slate-800/80 p-2.5 rounded border border-slate-700">
                <span className="text-indigo-400 font-semibold">(0008,0060) Modality:</span>{' '}
                {selectedStudy.modality}
              </div>
              <div className="bg-slate-800/80 p-2.5 rounded border border-slate-700">
                <span className="text-indigo-400 font-semibold">(0018,0050) SliceThickness:</span>{' '}
                {selectedSeries?.slice_thickness_mm || 1.25} mm
              </div>
              <div className="bg-slate-800/80 p-2.5 rounded border border-slate-700">
                <span className="text-indigo-400 font-semibold">(0028,0030) PixelSpacing:</span>{' '}
                {selectedSeries?.pixel_spacing_row_mm || 0.68} \ {selectedSeries?.pixel_spacing_col_mm || 0.68} mm
              </div>
            </div>

            <div className="pt-2 text-right">
              <button
                onClick={() => setShowDicomMetadata(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Acknowledge Alert */}
      {ackAlertModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>🚨</span> Acknowledge ICU Arrhythmia Alert
              </h3>
              <button
                onClick={() => setAckAlertModal(null)}
                className="text-slate-400 hover:text-white text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-200">
              <p className="font-bold">{ackAlertModal.alert_description}</p>
              <p className="text-[11px] text-red-300 mt-1">Lead: {ackAlertModal.lead_involved} | HR: {ackAlertModal.heart_rate_bpm} BPM</p>
            </div>

            <div>
              <label className="block text-xs text-slate-300 mb-1 font-semibold">
                Clinical Intervention / Action Taken:
              </label>
              <textarea
                value={clinicianActionText}
                onChange={(e) => setClinicianActionText(e.target.value)}
                placeholder="e.g. Bedside physician notified. Rapid Response activated. IV Amiodarone initiated."
                rows={3}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setAckAlertModal(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleAcknowledgeAlert}
                disabled={!clinicianActionText.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow"
              >
                Confirm Acknowledgment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
