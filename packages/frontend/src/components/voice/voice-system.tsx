/**
 * Voice System Components for CanadaGPT
 *
 * Three main components:
 * 1. VoiceSearch - Voice-enabled search with live transcription
 * 2. VoiceChat - Conversational interface with Claude/OpenAI
 * 3. VoiceNotes - Context-aware voice note-taking
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, MicOff, Send, Loader2, X, Check, Volume2, Save, Trash2 } from 'lucide-react';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface VoiceSearchProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  className?: string;
}

interface VoiceChatProps {
  apiEndpoint: string;
  apiKey: string;
  provider: 'claude' | 'openai';
  context?: {
    page: string;
    mpId?: string;
    billId?: string;
    debateId?: string;
  };
  className?: string;
}

interface VoiceNotesProps {
  context: {
    type: 'mp' | 'bill' | 'debate' | 'statement';
    id: string;
    title: string;
    metadata?: Record<string, any>;
  };
  onSave: (note: VoiceNote) => Promise<void>;
  className?: string;
}

interface VoiceNote {
  id: string;
  transcript: string;
  context: {
    type: string;
    id: string;
    title: string;
    metadata?: Record<string, any>;
  };
  timestamp: string;
  audioUrl?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// ============================================================================
// Browser Speech Recognition Types
// ============================================================================

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook for managing Web Speech API
 */
function useSpeechRecognition() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    // Check for browser support
    if (typeof window === 'undefined') return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-CA';

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcriptText = result[0].transcript;

        if (result.isFinal) {
          final += transcriptText + ' ';
        } else {
          interim += transcriptText;
        }
      }

      if (final) {
        setTranscript((prev) => prev + final);
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setError(`Speech recognition error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript('');
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      setError('Speech recognition not initialized');
      return;
    }

    try {
      setTranscript('');
      setInterimTranscript('');
      setError(null);
      recognitionRef.current.start();
      setIsListening(true);

      // Haptic feedback (iOS)
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }

      // Auto-stop after 30 seconds to save battery
      setTimeout(() => {
        if (isListening) {
          stopListening();
        }
      }, 30000);
    } catch (err) {
      console.error('Error starting speech recognition:', err);
      setError('Failed to start speech recognition');
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop();
      setIsListening(false);

      // Haptic feedback (iOS)
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    }
  }, [isListening]);

  return {
    isListening,
    transcript,
    interimTranscript,
    error,
    startListening,
    stopListening,
    isSupported: !!recognitionRef.current,
  };
}

// ============================================================================
// 1. VoiceSearch Component
// ============================================================================

export function VoiceSearch({ onSearch, placeholder = 'Search...', className = '' }: VoiceSearchProps) {
  const {
    isListening,
    transcript,
    interimTranscript,
    error,
    startListening,
    stopListening,
    isSupported,
  } = useSpeechRecognition();

  const [searchQuery, setSearchQuery] = useState('');

  // Update search query when transcript changes
  useEffect(() => {
    if (transcript) {
      setSearchQuery(transcript.trim());
    }
  }, [transcript]);

  const handleVoiceToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  if (!isSupported) {
    return (
      <div className={`voice-search-container ${className}`}>
        <div className="voice-search-error">
          Voice search not supported in this browser
        </div>
      </div>
    );
  }

  return (
    <div className={`voice-search-container ${className}`}>
      <div className="voice-search-input-wrapper">
        <input
          type="text"
          value={searchQuery + (interimTranscript ? ' ' + interimTranscript : '')}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          className="voice-search-input"
        />

        <button
          onClick={handleVoiceToggle}
          className={`voice-search-mic-button ${isListening ? 'listening' : ''}`}
          aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
        >
          {isListening ? (
            <>
              <MicOff className="h-5 w-5" />
              <span className="voice-waveform" />
            </>
          ) : (
            <Mic className="h-5 w-5" />
          )}
        </button>

        <button
          onClick={handleSearch}
          className="voice-search-submit-button"
          aria-label="Search"
          disabled={!searchQuery.trim()}
        >
          <Send className="h-5 w-5" />
        </button>
      </div>

      {error && (
        <div className="voice-search-error">
          {error}
        </div>
      )}

      {isListening && (
        <div className="voice-search-hint">
          Listening... (auto-stops in 30s)
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 2. VoiceChat Component
// ============================================================================

export function VoiceChat({ apiEndpoint, apiKey, provider, context, className = '' }: VoiceChatProps) {
  const {
    isListening,
    transcript,
    interimTranscript,
    error: speechError,
    startListening,
    stopListening,
    isSupported,
  } = useSpeechRecognition();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update input when transcript changes
  useEffect(() => {
    if (transcript) {
      setInputText(transcript.trim());
    }
  }, [transcript]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleVoiceToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          provider,
          messages: [...messages, userMessage],
          context,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    sendMessage(inputText);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isSupported) {
    return (
      <div className={`voice-chat-container ${className}`}>
        <div className="voice-chat-error">
          Voice chat not supported in this browser
        </div>
      </div>
    );
  }

  return (
    <div className={`voice-chat-container ${className}`}>
      {/* Messages */}
      <div className="voice-chat-messages">
        {messages.length === 0 && (
          <div className="voice-chat-empty">
            <Volume2 className="h-12 w-12 text-text-tertiary mb-2" />
            <p className="text-text-secondary">Ask me anything about Canadian parliament</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`voice-chat-message ${message.role === 'user' ? 'user' : 'assistant'}`}
          >
            <div className="voice-chat-message-content">
              {message.content}
            </div>
            <div className="voice-chat-message-time">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="voice-chat-message assistant">
            <div className="voice-chat-message-content">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="voice-chat-input-wrapper">
        <textarea
          value={inputText + (interimTranscript ? ' ' + interimTranscript : '')}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type or speak your question..."
          className="voice-chat-input"
          rows={2}
        />

        <div className="voice-chat-controls">
          <button
            onClick={handleVoiceToggle}
            className={`voice-chat-mic-button ${isListening ? 'listening' : ''}`}
            aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
          >
            {isListening ? (
              <>
                <MicOff className="h-5 w-5" />
                <span className="voice-waveform" />
              </>
            ) : (
              <Mic className="h-5 w-5" />
            )}
          </button>

          <button
            onClick={handleSend}
            className="voice-chat-send-button"
            aria-label="Send message"
            disabled={!inputText.trim() || isLoading}
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>

      {(error || speechError) && (
        <div className="voice-chat-error">
          {error || speechError}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// 3. VoiceNotes Component
// ============================================================================

export function VoiceNotes({ context, onSave, className = '' }: VoiceNotesProps) {
  const {
    isListening,
    transcript,
    interimTranscript,
    error: speechError,
    startListening,
    stopListening,
    isSupported,
  } = useSpeechRecognition();

  const [notes, setNotes] = useState<VoiceNote[]>([]);
  const [currentNote, setCurrentNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load notes from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('voice-notes');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setNotes(parsed.filter((note: VoiceNote) =>
          note.context.type === context.type && note.context.id === context.id
        ));
      } catch (err) {
        console.error('Failed to load notes:', err);
      }
    }
  }, [context]);

  // Update current note when transcript changes
  useEffect(() => {
    if (transcript) {
      setCurrentNote(transcript);
    }
  }, [transcript]);

  const handleVoiceToggle = () => {
    if (isListening) {
      stopListening();
    } else {
      setCurrentNote(''); // Clear previous note
      startListening();
    }
  };

  const handleSaveNote = async () => {
    if (!currentNote.trim()) return;

    const note: VoiceNote = {
      id: `note-${Date.now()}`,
      transcript: currentNote.trim(),
      context,
      timestamp: new Date().toISOString(),
    };

    setIsSaving(true);
    setError(null);

    try {
      // Save to server
      await onSave(note);

      // Save to localStorage (offline queue)
      const newNotes = [...notes, note];
      setNotes(newNotes);
      localStorage.setItem('voice-notes', JSON.stringify(newNotes));

      setCurrentNote('');
      setSuccessMessage('Note saved!');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to save note:', err);
      setError('Failed to save note. It will be saved locally and synced when online.');

      // Save locally anyway
      const newNotes = [...notes, note];
      setNotes(newNotes);
      localStorage.setItem('voice-notes', JSON.stringify(newNotes));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteNote = (noteId: string) => {
    const newNotes = notes.filter((n) => n.id !== noteId);
    setNotes(newNotes);
    localStorage.setItem('voice-notes', JSON.stringify(newNotes));
  };

  if (!isSupported) {
    return (
      <div className={`voice-notes-container ${className}`}>
        <div className="voice-notes-error">
          Voice notes not supported in this browser
        </div>
      </div>
    );
  }

  return (
    <div className={`voice-notes-container ${className}`}>
      {/* Context Badge */}
      <div className="voice-notes-context">
        <span className="voice-notes-context-badge">
          {context.type}: {context.title}
        </span>
      </div>

      {/* Current Note Input */}
      <div className="voice-notes-input-wrapper">
        <textarea
          value={currentNote + (interimTranscript ? ' ' + interimTranscript : '')}
          onChange={(e) => setCurrentNote(e.target.value)}
          placeholder="Type or speak your note..."
          className="voice-notes-input"
          rows={4}
        />

        <div className="voice-notes-controls">
          <button
            onClick={handleVoiceToggle}
            className={`voice-notes-mic-button ${isListening ? 'listening' : ''}`}
            aria-label={isListening ? 'Stop recording' : 'Start recording'}
          >
            {isListening ? (
              <>
                <MicOff className="h-6 w-6" />
                <span className="voice-waveform" />
              </>
            ) : (
              <Mic className="h-6 w-6" />
            )}
          </button>

          <button
            onClick={handleSaveNote}
            className="voice-notes-save-button"
            aria-label="Save note"
            disabled={!currentNote.trim() || isSaving}
          >
            {isSaving ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Save className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="voice-notes-success">
          <Check className="h-4 w-4" />
          {successMessage}
        </div>
      )}

      {(error || speechError) && (
        <div className="voice-notes-error">
          {error || speechError}
        </div>
      )}

      {/* Saved Notes */}
      {notes.length > 0 && (
        <div className="voice-notes-list">
          <h3 className="voice-notes-list-title">Saved Notes</h3>
          {notes.map((note) => (
            <div key={note.id} className="voice-note-card">
              <div className="voice-note-content">
                {note.transcript}
              </div>
              <div className="voice-note-meta">
                <span className="voice-note-time">
                  {new Date(note.timestamp).toLocaleString()}
                </span>
                <button
                  onClick={() => handleDeleteNote(note.id)}
                  className="voice-note-delete"
                  aria-label="Delete note"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
