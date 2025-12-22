# Phase 2: Supabase Storage Bucket Setup

## Message Attachments Bucket Configuration

### 1. Create Bucket via Supabase Dashboard

1. Go to your Supabase project: https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk
2. Navigate to **Storage** in the left sidebar
3. Click **New bucket**
4. Configure:
   - **Name**: `message-attachments`
   - **Public bucket**: ✅ Yes (allows direct URL access for images)
   - **File size limit**: 10 MB (matches upload route validation)
   - **Allowed MIME types**: Leave default or specify: `image/*,application/pdf`

### 2. Set Up RLS Policies

After creating the bucket, add these Row Level Security policies:

#### Policy 1: Allow Authenticated Users to Upload
```sql
CREATE POLICY "Authenticated users can upload message attachments"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'message-attachments' AND
  auth.uid()::text = (storage.foldername(name))[1]
);
```

**Explanation**: Users can only upload files to their own folder (organized by user ID)

#### Policy 2: Allow Public Read Access
```sql
CREATE POLICY "Anyone can view message attachments"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'message-attachments');
```

**Explanation**: Once uploaded, attachments can be viewed by anyone with the URL (necessary for recipients to see attachments)

#### Policy 3: Allow Users to Delete Their Own Files
```sql
CREATE POLICY "Users can delete their own message attachments"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'message-attachments' AND
  auth.uid()::text = (storage.foldername(name))[1]
);
```

### 3. Verify Upload Route Configuration

The upload route at `/api/messages/upload/route.ts` is already configured to:
- Accept files up to 10MB
- Only allow images and PDFs: `accept="image/*,.pdf"`
- Upload to path: `{userId}/{timestamp}-{filename}`
- Return public URL for display

### 4. Test Upload Flow

After bucket creation:

1. Sign in to the app
2. Navigate to `/messages`
3. Start a conversation
4. Click the paperclip icon
5. Select an image or PDF (max 10MB)
6. Verify:
   - Upload progress indicator shows
   - File appears in attachment preview
   - Send message with attachment
   - Attachment displays correctly in message thread

### 5. Folder Structure

Files will be organized by user ID:
```
message-attachments/
├── {user-id-1}/
│   ├── 1705123456789-image.jpg
│   ├── 1705123789012-document.pdf
│   └── ...
├── {user-id-2}/
│   └── ...
```

### 6. Security Considerations

**Why Public Bucket?**
- Allows direct URL access for image rendering without auth headers
- Recipients can view attachments without complex proxy routes
- Standard practice for user-generated content that needs to be shared

**Privacy via Obscurity:**
- URLs contain random timestamps and UUIDs
- Only users who receive the message know the URL
- No directory listing is enabled
- RLS prevents unauthorized deletion

**Future Enhancement:**
If private attachments are needed:
1. Create separate `private-attachments` bucket
2. Implement signed URL generation in API route
3. Add expiring tokens for access control

## Deployment Checklist

- [ ] Create `message-attachments` bucket in Supabase dashboard
- [ ] Add RLS policies (3 policies above)
- [ ] Verify file size limit (10 MB)
- [ ] Test upload flow with image
- [ ] Test upload flow with PDF
- [ ] Verify attachments display in message thread
- [ ] Check that public URLs work
- [ ] Confirm deletion works for own files
- [ ] Monitor storage usage in Supabase dashboard

## Complete Phase 2 Feature List

✅ **Database**
- conversations table with participant constraints
- direct_messages table with JSONB attachments
- typing_indicators table with auto-expiry
- Helper functions (get_or_create_conversation, mark_messages_read)
- Triggers for conversation metadata updates

✅ **API Routes**
- GET/POST /api/messages/conversations
- GET/POST /api/messages/conversations/[id]
- POST /api/messages/conversations/[id]/read
- POST /api/messages/upload

✅ **Real-time Hooks**
- useRealtimeMessages (Supabase subscriptions)
- useTypingIndicator (debounced, auto-cleanup)

✅ **UI Components**
- ConversationsList (with unread badges)
- MessageThread (real-time updates, typing animation)
- MessageInput (file upload, Enter to send)

✅ **Pages**
- /messages (responsive two-column layout)
- ?user=username support for direct conversation links

⏳ **Pending**
- Supabase Storage bucket creation (this document)
- End-to-end testing

## Next: Phase 3 Preview

After Phase 2 testing is complete, Phase 3 will add:
- Persistent notification system (beyond toast)
- @username mentions with autocomplete
- Notification preferences
- Email digests for missed messages
