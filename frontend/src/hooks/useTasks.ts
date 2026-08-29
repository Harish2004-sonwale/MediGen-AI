// ==============================================================================
// MediGen AI - Background Task Polling & Management Hook
// ==============================================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { tasksApi } from '../api/client';
import { BackgroundTask } from '../types';

export const useTasks = (patientId?: string) => {
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      const res = await tasksApi.list(1, 50, patientId);
      setTasks(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tasks.');
    }
  }, [patientId]);

  useEffect(() => {
    loadTasks();

    // Check if any tasks are currently running or queued
    const hasActiveTasks = tasks.some(
      (t) => t.status === 'queued' || t.status === 'running' || t.status === 'retrying'
    );

    if (hasActiveTasks) {
      pollingRef.current = setInterval(() => {
        loadTasks();
      }, 2500);
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [tasks, loadTasks]);

  const retryTask = async (taskId: string) => {
    try {
      await tasksApi.retry(taskId);
      await loadTasks();
    } catch (err: any) {
      setError(err.message || `Failed to retry task ${taskId}`);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await tasksApi.cancel(taskId);
      await loadTasks();
    } catch (err: any) {
      setError(err.message || `Failed to cancel task ${taskId}`);
    }
  };

  const triggerDocumentOCR = async (documentId: string) => {
    setIsLoading(true);
    try {
      const task = await tasksApi.triggerDocumentProcessing(documentId);
      await loadTasks();
      return task;
    } finally {
      setIsLoading(false);
    }
  };

  const triggerTimelineSummary = async (pId: string, focus?: string) => {
    setIsLoading(true);
    try {
      const task = await tasksApi.triggerTimelineSummary(pId, focus);
      await loadTasks();
      return task;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    tasks,
    isLoading,
    error,
    loadTasks,
    retryTask,
    cancelTask,
    triggerDocumentOCR,
    triggerTimelineSummary,
  };
};
