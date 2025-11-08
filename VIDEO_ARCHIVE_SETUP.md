# Video Archive Integration Guide

## Overview

This guide explains how to set up your video archive and integrate it with the chamber seating plan for video playback.

## Storage Options

### Option 1: Cloudflare R2 (Recommended)
**Pros:**
- S3-compatible API
- Zero egress fees (free bandwidth)
- $0.015/GB storage
- Fast global CDN
- Simple setup

**Setup:**
```bash
# 1. Create R2 bucket in Cloudflare dashboard
# 2. Enable public access or use signed URLs
# 3. Get access keys

# Example URL structure:
# https://pub-abc123.r2.dev/videos/2024/debate-123.mp4
```

**Costs:**
- Storage: ~$1.50/month per 100GB
- Bandwidth: FREE
- Requests: ~$0.36 per million

### Option 2: AWS S3 + CloudFront
**Pros:**
- Industry standard
- Reliable
- Many features

**Cons:**
- Bandwidth costs (~$0.085/GB)
- More complex setup

**Setup:**
```bash
# 1. Create S3 bucket
aws s3 mb s3://canadagpt-videos

# 2. Create CloudFront distribution
# 3. Set up CORS for video playback
```

### Option 3: Azure Blob Storage
**Pros:**
- Good for Canadian data residency
- Toronto data centers
- Integrated CDN

**Setup:**
```bash
# 1. Create storage account
az storage account create --name canadagptvids

# 2. Create container
# 3. Enable CDN
```

## Video Organization Structure

Recommended folder structure:
```
videos/
├── house/
│   ├── 2024/
│   │   ├── 01-january/
│   │   │   ├── 2024-01-15-debate.mp4
│   │   │   ├── 2024-01-15-question-period.mp4
│   │   │   └── metadata.json
│   │   └── 02-february/
│   └── 2025/
├── committees/
│   ├── ETHI/
│   │   └── 2024-03-20-meeting-15.mp4
│   └── HUMA/
└── thumbnails/
    └── 2024-01-15-debate.jpg
```

## Video Metadata

Store metadata alongside videos as JSON:
```json
{
  "debate_id": "debate-2024-01-15",
  "date": "2024-01-15",
  "title": "House Proceedings - Question Period",
  "type": "question_period",
  "parliament": 44,
  "session": 1,
  "sitting_number": 234,
  "duration_seconds": 3600,
  "video_url": "https://your-cdn.com/videos/2024/01-january/2024-01-15-debate.mp4",
  "thumbnail_url": "https://your-cdn.com/thumbnails/2024-01-15-debate.jpg",
  "cpac_episode_id": "cpac-123456",
  "speakers": [
    {
      "mp_id": "pierre-poilievre",
      "parl_mp_id": 25524,
      "start_time": 120.5,
      "end_time": 245.2,
      "topic": "Carbon tax"
    }
  ]
}
```

## Importing Video URLs to Neo4j

### Method 1: Manual - Single Video

```bash
# Connect to Neo4j
cypher-shell -a bolt://localhost:7687 -u neo4j -p canadagpt2024

# Add video to existing debate
MATCH (d:Debate {date: date('2024-01-15')})
SET d.cpac_video_url = 'https://your-cdn.com/videos/2024/01-january/2024-01-15-debate.mp4',
    d.cpac_episode_id = 'cpac-123456',
    d.video_start_time = datetime('2024-01-15T14:00:00'),
    d.video_duration = 3600;
```

### Method 2: Bulk Import Script

Create `scripts/import_video_urls.py`:
```python
#!/usr/bin/env python3
"""Import video URLs from metadata JSON files"""

import json
import glob
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "canadagpt2024"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Find all metadata files
metadata_files = glob.glob('videos/**/metadata.json', recursive=True)

with driver.session() as session:
    for filepath in metadata_files:
        with open(filepath, 'r') as f:
            metadata = json.load(f)

        # Update or create Debate node
        result = session.run("""
            MERGE (d:Debate {id: $debate_id})
            ON CREATE SET
                d.date = date($date),
                d.topic = $title,
                d.parliament = $parliament,
                d.session = $session
            SET
                d.cpac_video_url = $video_url,
                d.cpac_episode_id = $cpac_episode_id,
                d.video_duration = $duration
            RETURN d.id as id
        """,
            debate_id=metadata['debate_id'],
            date=metadata['date'],
            title=metadata['title'],
            parliament=metadata.get('parliament'),
            session=metadata.get('session'),
            video_url=metadata['video_url'],
            cpac_episode_id=metadata.get('cpac_episode_id'),
            duration=metadata.get('duration_seconds')
        )

        record = result.single()
        print(f"✓ Imported video for {metadata['date']}: {metadata['title']}")

driver.close()
print(f"\n✓ Imported {len(metadata_files)} videos")
```

Run:
```bash
python3 scripts/import_video_urls.py
```

### Method 3: CSV Bulk Import

Create `video_urls.csv`:
```csv
debate_id,date,video_url,cpac_episode_id,duration_seconds
debate-2024-01-15,2024-01-15,https://cdn.example.com/2024-01-15.mp4,cpac-123,3600
debate-2024-01-16,2024-01-16,https://cdn.example.com/2024-01-16.mp4,cpac-124,3720
```

Import:
```cypher
LOAD CSV WITH HEADERS FROM 'file:///video_urls.csv' AS row
MERGE (d:Debate {id: row.debate_id})
ON CREATE SET d.date = date(row.date)
SET d.cpac_video_url = row.video_url,
    d.cpac_episode_id = row.cpac_episode_id,
    d.video_duration = toInteger(row.duration_seconds);
```

## Updating Chamber Page to Use Videos

### 1. Create Debate Selector Component

`packages/frontend/src/components/chamber/DebateSelector.tsx`:
```typescript
'use client';

import { useQuery, gql } from '@apollo/client';
import { Select } from '@canadagpt/design-system';

const GET_DEBATES_WITH_VIDEO = gql`
  query GetDebatesWithVideo {
    debates(where: { cpac_video_url_NOT: null }, options: { sort: [{ date: DESC }], limit: 50 }) {
      id
      date
      topic
      cpac_video_url
      video_duration
    }
  }
`;

export function DebateSelector({ onSelect }: { onSelect: (debate: any) => void }) {
  const { data, loading } = useQuery(GET_DEBATES_WITH_VIDEO);

  return (
    <Select
      label="Select Debate to Watch"
      onChange={(e) => {
        const debate = data?.debates.find((d: any) => d.id === e.target.value);
        if (debate) onSelect(debate);
      }}
    >
      <option value="">Choose a date...</option>
      {data?.debates.map((debate: any) => (
        <option key={debate.id} value={debate.id}>
          {new Date(debate.date).toLocaleDateString()} - {debate.topic || 'House Proceedings'}
        </option>
      ))}
    </Select>
  );
}
```

### 2. Update Chamber Page

In `packages/frontend/src/app/chamber/page.tsx`:
```typescript
const [selectedDebate, setSelectedDebate] = useState<any>(null);

// In the video section:
<CPACPlayer
  videoUrl={selectedDebate?.cpac_video_url}
  title={selectedDebate?.topic || 'House of Commons - Question Period'}
  date={selectedDebate?.date ? new Date(selectedDebate.date).toLocaleDateString() : undefined}
  isLive={false}
/>

// Add debate selector above video player:
<DebateSelector onSelect={setSelectedDebate} />
```

## Video Format Recommendations

### Encoding Settings
- **Container**: MP4 (H.264 + AAC)
- **Video Codec**: H.264 (x264)
- **Resolution**: 1920x1080 (1080p) or 1280x720 (720p)
- **Bitrate**: 2-4 Mbps (good quality, reasonable size)
- **Frame Rate**: 30 fps
- **Audio Codec**: AAC
- **Audio Bitrate**: 128 kbps

### FFmpeg Conversion Example
```bash
ffmpeg -i input.mp4 \
  -c:v libx264 \
  -preset medium \
  -crf 23 \
  -c:a aac \
  -b:a 128k \
  -movflags +faststart \
  output.mp4
```

### Generate Thumbnails
```bash
# Extract thumbnail at 10 seconds
ffmpeg -i video.mp4 -ss 00:00:10 -vframes 1 -q:v 2 thumbnail.jpg
```

## Cost Estimates

### For 1 year of daily proceedings (365 videos)

**Assumptions:**
- Average video length: 3 hours
- H.264 @ 2 Mbps = ~2.7 GB per video
- Total: ~1 TB of video

**Cloudflare R2:**
- Storage: 1000 GB × $0.015 = $15/month
- Bandwidth: FREE
- **Total: ~$180/year**

**AWS S3 + CloudFront:**
- Storage: $23/month
- Bandwidth (assuming 10k views/month): $255/month
- **Total: ~$3,336/year** ⚠️ EXPENSIVE

**Verdict:** Use Cloudflare R2 - saves $3,156/year!

## Downloading from CPAC/ParlVU

### Option 1: youtube-dl (if supported)
```bash
youtube-dl "https://parlvu.parl.gc.ca/..."
```

### Option 2: Browser DevTools
1. Open ParlVU video page
2. Open DevTools (F12) → Network tab
3. Filter by "m3u8" or "mp4"
4. Play video
5. Copy video manifest URL
6. Download with ffmpeg:
```bash
ffmpeg -i "https://parlvu.parl.gc.ca/...manifest.m3u8" \
  -c copy \
  output.mp4
```

### Option 3: Manual 30-minute clips
- ParlVU allows downloading 30-minute clips
- Download multiple clips
- Concatenate with ffmpeg:
```bash
# Create file list
echo "file 'part1.mp4'" > concat.txt
echo "file 'part2.mp4'" >> concat.txt
echo "file 'part3.mp4'" >> concat.txt

# Concatenate
ffmpeg -f concat -safe 0 -i concat.txt -c copy full_video.mp4
```

## Automating Video Ingestion

### Weekly Cron Job
```bash
#!/bin/bash
# download_latest_videos.sh

# 1. Check CPAC for new episodes
curl "https://cpac.ca/api/episodes?latest=7days" | jq ...

# 2. Download new videos
# ...

# 3. Upload to R2
aws s3 sync ./downloads/ s3://canadagpt-videos/house/$(date +%Y)/ \
  --endpoint-url https://your-account.r2.cloudflarestorage.com

# 4. Import to Neo4j
python3 scripts/import_video_urls.py

# 5. Clean up local files
rm -rf ./downloads/*
```

Add to crontab:
```bash
# Run every Sunday at 2am
0 2 * * 0 /path/to/download_latest_videos.sh
```

## Security Considerations

### Option 1: Public URLs (Simple)
- Videos publicly accessible via CDN URL
- No authentication required
- Easy to implement
- ⚠️ Anyone with URL can watch

### Option 2: Signed URLs (Secure)
```typescript
// Generate signed URL server-side
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3Client = new S3Client({ region: 'auto' });

async function getVideoUrl(videoKey: string) {
  const command = new GetObjectCommand({
    Bucket: 'canadagpt-videos',
    Key: videoKey,
  });

  // URL expires in 1 hour
  return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
}
```

### Option 3: Token-gated (Premium)
```typescript
// Add to video player
<CPACPlayer
  videoUrl={selectedDebate?.cpac_video_url}
  authToken={session?.access_token}
/>

// Backend validates token before serving video
```

## Next Steps

1. **Choose storage provider** (recommend: Cloudflare R2)
2. **Create bucket/container**
3. **Upload first test video**
4. **Add video URL to a Debate node** (use Method 1)
5. **Test playback in chamber page**
6. **Automate bulk import** (use Method 2 or 3)
7. **Set up automated ingestion** (optional)

## Support

For video issues:
- **Format errors**: Re-encode with FFmpeg (see settings above)
- **CORS errors**: Enable CORS on your CDN
- **Playback issues**: Check browser console for errors
- **Large files**: Use adaptive bitrate streaming (HLS/DASH)

---

**Status**: Ready to integrate once you have videos uploaded!
