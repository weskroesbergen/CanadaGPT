# Supabase Storage Setup for Message Attachments

This document explains how to set up the Supabase Storage bucket for message attachments in the CanadaGPT application.

## Overview

The messaging system supports file attachments (images and PDFs) that are stored in Supabase Storage. This requires a one-time manual setup via the Supabase Dashboard.

## Setup Instructions

### 1. Access Supabase Dashboard

1. Navigate to your Supabase project dashboard at [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project (the one configured in `NEXT_PUBLIC_SUPABASE_URL`)
3. Click on **Storage** in the left sidebar

### 2. Create the Bucket

1. Click the **New bucket** button
2. Configure the bucket with these settings:
   - **Name**: `message-attachments`
   - **Public bucket**: Toggle **OFF** (keep it private)
   - **File size limit**: 5 MB (or adjust as needed)
   - **Allowed MIME types**: Leave blank to allow all, or specify:
     - `image/png`
     - `image/jpeg`
     - `image/jpg`
     - `image/gif`
     - `image/webp`
     - `application/pdf`
3. Click **Create bucket**

### 3. Configure Row Level Security (RLS) Policies

By default, the bucket will have RLS enabled but no policies. You need to add policies to control access:

#### Policy 1: Allow Authenticated Users to Upload

1. Click on the `message-attachments` bucket
2. Go to the **Policies** tab
3. Click **New Policy**
4. Select **For full customization** option
5. Configure the policy:
   - **Policy name**: `Authenticated users can upload`
   - **Allowed operation**: `INSERT`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     true
     ```
   - **WITH CHECK expression**:
     ```sql
     (storage.foldername(name))[1] = auth.uid()::text
     ```
     *This ensures users can only upload to folders matching their user ID*
6. Click **Review** then **Save policy**

#### Policy 2: Allow Users to Read Their Own Files

1. Click **New Policy** again
2. Configure:
   - **Policy name**: `Users can read their own files`
   - **Allowed operation**: `SELECT`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     (storage.foldername(name))[1] = auth.uid()::text
     ```
3. Click **Review** then **Save policy**

#### Policy 3: Allow Users to Read Files in Their Conversations

Since messages can be sent between users, we need to allow reading files in conversations where the user is a participant:

1. Click **New Policy**
2. Configure:
   - **Policy name**: `Users can read files in their conversations`
   - **Allowed operation**: `SELECT`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     EXISTS (
       SELECT 1 FROM direct_messages dm
       JOIN conversations c ON dm.conversation_id = c.id
       WHERE dm.attachments @> jsonb_build_array(
         jsonb_build_object('path', storage.filename(name))
       )
       AND (c.participant1_id = auth.uid() OR c.participant2_id = auth.uid())
     )
     ```
     *This allows users to read files that are attached to messages in their conversations*
3. Click **Review** then **Save policy**

#### Policy 4: Allow Users to Delete Their Own Uploads

1. Click **New Policy**
2. Configure:
   - **Policy name**: `Users can delete their own files`
   - **Allowed operation**: `DELETE`
   - **Target roles**: `authenticated`
   - **USING expression**:
     ```sql
     (storage.foldername(name))[1] = auth.uid()::text
     ```
3. Click **Review** then **Save policy**

### 4. Verify Setup

To verify the bucket is configured correctly:

1. Go to **Storage** → `message-attachments`
2. Check that the bucket shows:
   - Privacy: **Private**
   - File size limit: **5 MB** (or your configured limit)
   - RLS: **Enabled** with 4 policies

## File Upload Flow

The application handles file uploads as follows:

1. **User selects files** in the MessageInput component
2. **Files are uploaded** via `/api/messages/upload` route:
   - Files are stored in user-specific folders: `{user_id}/{timestamp}_{filename}`
   - File metadata is returned (path, filename, size, type)
3. **Message is created** with attachments JSONB array containing file metadata
4. **Recipients can download** files using the file path through Supabase Storage URLs

## File Structure

Files are organized in the bucket as:
```
message-attachments/
├── {user_id_1}/
│   ├── 1234567890_image.png
│   ├── 1234567891_document.pdf
│   └── ...
├── {user_id_2}/
│   ├── 1234567892_photo.jpg
│   └── ...
└── ...
```

## Security Considerations

- **Private bucket**: Files are not publicly accessible
- **User isolation**: Users can only upload to their own folders (`{user_id}/`)
- **Conversation access**: Users can only access files in conversations they're part of
- **File size limits**: Prevent abuse by limiting file sizes
- **MIME type restrictions**: (Optional) Limit allowed file types for security

## Troubleshooting

### Issue: "Access denied" when uploading files

**Solution**: Verify that:
1. The bucket exists and is named exactly `message-attachments`
2. RLS is enabled on the bucket
3. The upload policy exists and targets `authenticated` users
4. Your user is authenticated (session exists)

### Issue: Can't download files from messages

**Solution**: Check that:
1. The SELECT policy for conversation participants is created
2. The file path in the message matches the actual file in storage
3. The user is a participant in the conversation

### Issue: Files upload but disappear

**Solution**:
1. Check the RLS WITH CHECK expression on the INSERT policy
2. Ensure files are being uploaded to the correct folder structure (`{user_id}/...`)

## API Route Reference

The file upload is handled by `/api/messages/upload` which:
- Accepts multipart form data with file uploads
- Validates file size and type
- Uploads to Supabase Storage
- Returns file metadata for inclusion in messages

See `packages/frontend/src/app/api/messages/upload/route.ts` for implementation details.

## Next Steps

After completing this setup:
1. Test file uploads by sending a message with an attachment
2. Verify files appear in the Storage bucket
3. Test downloading files from received messages
4. Monitor storage usage in the Supabase Dashboard

## Storage Limits

Free Supabase tier includes:
- **1 GB storage** (total across all buckets)
- **2 GB bandwidth** per month
- **50 MB max file size**

Upgrade to Pro plan if you need:
- **100 GB storage** included
- **200 GB bandwidth** per month
- Custom file size limits

For pricing details, see: https://supabase.com/pricing
