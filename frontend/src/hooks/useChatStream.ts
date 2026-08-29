// ==============================================================================
// MediGen AI - Real-Time SSE Streaming Chat Hook
// ==============================================================================

import { useState, useRef, useCallback } from 'react';
import { chatApi } from '../api/client';
import { ChatMessage, ChatSession, TimelineCitation } from '../types';

export const useChatStream = (patientId?: string) => {
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamingCitations, setStreamingCitations] = useState<TimelineCitation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startNewSession = useCallback(async (pId: string, title?: string) => {
    setError(null);
    try {
      const session = await chatApi.createSession(pId, title || 'Clinical Consultation');
      setCurrentSession(session);
      setMessages([]);
      setStreamingText('');
      setStreamingCitations([]);
      return session;
    } catch (err: any) {
      setError(err.message || 'Failed to start consultation session.');
      throw err;
    }
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    setError(null);
    try {
      const detail = await chatApi.getSession(sessionId);
      setCurrentSession({
        session_id: detail.session_id,
        patient_id: detail.patient_id,
        title: detail.title,
        is_active: detail.is_active,
        message_count: detail.messages.length,
        created_at: detail.created_at,
        updated_at: detail.updated_at,
      });
      setMessages(detail.messages);
      setStreamingText('');
      setStreamingCitations([]);
    } catch (err: any) {
      setError(err.message || 'Failed to load session history.');
    }
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      let session = currentSession;
      if (!session && patientId) {
        session = await startNewSession(patientId);
      }

      if (!session) {
        setError('No active consultation session.');
        return;
      }

      // 1. Optimistically append user message
      const userMessage: ChatMessage = {
        message_id: `user-${Date.now()}`,
        sender_role: 'user',
        content: text.trim(),
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);
      setStreamingText('');
      setStreamingCitations([]);
      setError(null);

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let fullText = '';
      const citations: TimelineCitation[] = [];

      try {
        await chatApi.streamMessage(
          session.session_id,
          text.trim(),
          {
            onStart: () => {
              setStreamingText('');
            },
            onDelta: (delta: string) => {
              fullText += delta;
              setStreamingText(fullText);
            },
            onCitation: (citation: TimelineCitation) => {
              citations.push(citation);
              setStreamingCitations([...citations]);
            },
            onDone: (data) => {
              const assistantMessage: ChatMessage = {
                message_id: data.message_id || `asst-${Date.now()}`,
                sender_role: 'assistant',
                content: fullText,
                citations: citations.length > 0 ? citations : undefined,
                insufficient_information: data.insufficient_information,
                created_at: new Date().toISOString(),
              };

              setMessages((prev) => [...prev, assistantMessage]);
              setStreamingText('');
              setStreamingCitations([]);
              setIsStreaming(false);
            },
            onError: (errStr: string) => {
              setError(errStr);
              setIsStreaming(false);
            },
          },
          abortController.signal
        );
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Error occurred while streaming response.');
        }
        setIsStreaming(false);
      }
    },
    [currentSession, patientId, startNewSession]
  );

  const abortStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  return {
    currentSession,
    messages,
    isStreaming,
    streamingText,
    streamingCitations,
    error,
    startNewSession,
    loadSession,
    sendMessage,
    abortStreaming,
  };
};
