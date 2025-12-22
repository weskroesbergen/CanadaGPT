/**
 * MessageInput Component
 *
 * Text input with file upload support and typing indicators
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Paperclip, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useMentionAutocomplete } from '@/hooks/useMentionAutocomplete';
import { MentionAutocomplete } from '@/components/messages/MentionAutocomplete';

interface MessageInputProps {
  onSend: (content: string, attachments: any[]) => Promise<void>;
  onTyping: (isTyping: boolean) => void;
  disabled?: boolean;
}

export function MessageInput({ onSend, onTyping, disabled }: MessageInputProps) {
  const [content, setContent] = useState('');
  const [attachments, setAttachments] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Mention autocomplete
  const {
    isOpen: showMentions,
    suggestions,
    selectedIndex,
    handleTextChange,
    handleKeyDown: handleMentionKeyDown,
    insertMention,
    setSelectedIndex,
  } = useMentionAutocomplete(textareaRef);

  // Handle mention detection when content changes
  useEffect(() => {
    handleTextChange(content);
  }, [content, handleTextChange]);

  // Handle typing indicator
  useEffect(() => {
    if (content.length > 0) {
      onTyping(true);

      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }

      // Stop typing after 2 seconds of inactivity
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(false);
      }, 2000);
    } else {
      onTyping(false);
    }

    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [content, onTyping]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);

    try {
      const uploadPromises = Array.from(files).map(async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/messages/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Upload failed');
        }

        return response.json();
      });

      const uploadedFiles = await Promise.all(uploadPromises);
      setAttachments((prev) => [...prev, ...uploadedFiles]);
      toast.success('Files uploaded successfully');
    } catch (error) {
      console.error('Error uploading files:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to upload files'
      );
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSend = async () => {
    const trimmedContent = content.trim();

    if (!trimmedContent && attachments.length === 0) {
      return;
    }

    setSending(true);
    onTyping(false);

    try {
      await onSend(trimmedContent, attachments);
      setContent('');
      setAttachments([]);

      // Focus back on textarea
      textareaRef.current?.focus();
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to send message'
      );
    } finally {
      setSending(false);
    }
  };

  // Handle mention selection
  const handleMentionSelect = (user: any) => {
    const newText = insertMention(user, content);
    setContent(newText);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Let mention autocomplete handle keyboard events if suggestions are shown
    const mentionHandled = handleMentionKeyDown(e);
    if (mentionHandled) {
      // Sync content state with textarea value after mention insertion
      if (textareaRef.current) {
        setContent(textareaRef.current.value);
      }
      return;
    }

    // Normal message sending logic
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background p-4">
      {/* Attachments Preview */}
      {attachments.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachments.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-2 rounded-lg border bg-muted px-3 py-2 text-sm"
            >
              <Paperclip className="h-4 w-4" />
              <span className="max-w-[200px] truncate">{file.filename}</span>
              <button
                onClick={() => removeAttachment(index)}
                className="ml-1 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Mention Autocomplete */}
      {showMentions && suggestions.length > 0 && (
        <MentionAutocomplete
          suggestions={suggestions}
          selectedIndex={selectedIndex}
          onSelect={handleMentionSelect}
          onHover={setSelectedIndex}
        />
      )}

      {/* Input Area */}
      <div className="flex gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          disabled={uploading || sending || disabled}
        />

        <Button
          variant="outline"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || sending || disabled}
        >
          {uploading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Paperclip className="h-4 w-4" />
          )}
        </Button>

        <Textarea
          ref={textareaRef}
          value={content}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
          disabled={sending || disabled}
          className="min-h-[44px] max-h-[200px] resize-none"
          rows={1}
        />

        <Button
          onClick={handleSend}
          disabled={(!content.trim() && attachments.length === 0) || sending || disabled}
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
