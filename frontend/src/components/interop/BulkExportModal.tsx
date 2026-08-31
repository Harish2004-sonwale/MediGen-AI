import React, { useState } from 'react';
import { bulkExportApi } from '../../api/client';
import { BulkExportJob } from '../../types';

interface BulkExportModalProps {
  isOpen?: boolean;
  facilityId?: string;
  onClose: () => void;
}

export const BulkExportModal: React.FC<BulkExportModalProps> = ({ isOpen = true, onClose }) => {
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['Patient', 'Encounter', 'Condition', 'Observation']);
  const [job, setJob] = useState<BulkExportJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  const availableTypes = [
    { id: 'Patient', label: 'Patients (Demographics & Identifiers)' },
    { id: 'Encounter', label: 'Encounters (Visits & Admissions)' },
    { id: 'Condition', label: 'Conditions & Diagnoses (SNOMED/ICD-10)' },
    { id: 'Observation', label: 'Observations & Vital Signs (LOINC)' },
    { id: 'ServiceRequest', label: 'Orders & CPOE Requisitions' },
    { id: 'CarePlan', label: 'Care Plans & Clinical Protocols' },
  ];

  const handleToggleType = (typeId: string) => {
    setSelectedTypes((prev) =>
      prev.includes(typeId) ? prev.filter((t) => t !== typeId) : [...prev, typeId]
    );
  };

  const handleStartExport = async () => {
    try {
      setLoading(true);
      setError(null);
      const kickoff = await bulkExportApi.kickoffExport(selectedTypes);
      const initialJob = await bulkExportApi.getExportStatus(kickoff.job_id);
      setJob(initialJob);

      // Poll every 2 seconds until completed or failed
      const interval = setInterval(async () => {
        try {
          const updated = await bulkExportApi.getExportStatus(kickoff.job_id);
          setJob(updated);
          if (updated.status === 'COMPLETED' || updated.status === 'FAILED') {
            clearInterval(interval);
            setPollingInterval(null);
          }
        } catch (e) {
          clearInterval(interval);
          setPollingInterval(null);
        }
      }, 2000);

      setPollingInterval(interval);
    } catch (err: any) {
      setError(err.message || 'Failed to initiate FHIR Bulk Data Export');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-w-lg w-full p-6 relative">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold"
        >
          ✕
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-xl text-indigo-600 dark:text-indigo-400 font-bold text-xl">
            💾
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">FHIR R4 Bulk Data Export ($export)</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">SMART/HL7 FHIR Bulk Data Access IG (NDJSON format)</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-xs text-red-600 dark:text-red-400 flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {!job && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                Select Resource Types
              </label>
              <div className="space-y-2">
                {availableTypes.map((type) => (
                  <label
                    key={type.id}
                    className="flex items-center gap-3 p-2.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer text-xs transition"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(type.id)}
                      onChange={() => handleToggleType(type.id)}
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{type.id}</span>
                    <span className="text-slate-400 text-[11px]">— {type.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartExport}
                disabled={loading || selectedTypes.length === 0}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-sm transition flex items-center gap-2"
              >
                <span>📥</span>
                {loading ? 'Starting Export...' : 'Initiate Asynchronous Export'}
              </button>
            </div>
          </div>
        )}

        {job && (
          <div className="space-y-6">
            <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Job ID</span>
                <span className="font-mono text-xs font-semibold text-slate-800 dark:text-slate-200">{job.job_id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Status</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
                  {job.status} ({job.progress_percent}%)
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${job.progress_percent}%` }}
                />
              </div>
            </div>

            {job.status === 'COMPLETED' && job.output_urls_json && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                  Generated NDJSON Output Files
                </h4>
                <div className="space-y-2">
                  {job.output_urls_json.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span>📄</span>
                        <div>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">{file.type}.ndjson</span>
                          <span className="block text-[10px] text-slate-400">{file.count ?? 0} records</span>
                        </div>
                      </div>
                      <a
                        href={file.url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1.5 bg-slate-100 dark:bg-slate-700 hover:bg-indigo-600 hover:text-white text-slate-700 dark:text-slate-300 rounded-lg font-medium transition flex items-center gap-1 text-xs"
                      >
                        📥 Download
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-xl text-xs hover:bg-slate-200 dark:hover:bg-slate-600 transition"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
