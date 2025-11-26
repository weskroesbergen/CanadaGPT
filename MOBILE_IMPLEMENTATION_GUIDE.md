# CanadaGPT Mobile Implementation Guide

Complete guide for implementing the mobile-optimized UI with voice features.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Voice System](#voice-system)
3. [Mobile Components](#mobile-components)
4. [Integration Examples](#integration-examples)
5. [PWA Setup](#pwa-setup)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Dependencies

All required dependencies are already installed:

```bash
# Installed dependencies:
# - lucide-react (icons)
# - @use-gesture/react (swipe gestures)
# - react-window (virtual scrolling)
```

### 2. Import CSS

Add to your global CSS or layout file:

```tsx
// In app/layout.tsx or similar
import '@/components/voice/voice-system.css';
import '@/components/mobile/mobile-cards.css';
import '@/components/mobile/mobile-navigation.css';
import '@/components/mobile/mobile-debate-viewer.css';
```

### 3. Basic Usage

```tsx
import { VoiceSearch } from '@/components/voice';
import { MobileBottomNav } from '@/components/mobile';

export default function Layout({ children }) {
  return (
    <>
      {children}
      <MobileBottomNav locale="en" />
    </>
  );
}
```

---

## Voice System

### VoiceSearch

Voice-enabled search with live transcription.

**Props:**
- `onSearch: (query: string) => void` - Search callback
- `placeholder?: string` - Input placeholder
- `className?: string` - Additional CSS classes

**Example:**
```tsx
import { VoiceSearch } from '@/components/voice';

function SearchPage() {
  const handleSearch = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`);
  };

  return <VoiceSearch onSearch={handleSearch} placeholder="Search MPs, bills..." />;
}
```

**Browser Support:**
- iOS Safari 14.5+
- Chrome Android 33+
- Requires HTTPS (except localhost)

---

### VoiceChat

Conversational AI interface with BYOK (Bring Your Own Key).

**Props:**
- `apiEndpoint: string` - Your API endpoint
- `apiKey: string` - User's Claude/OpenAI key
- `provider: 'claude' | 'openai'` - AI provider
- `context?: { page, mpId, billId, debateId }` - Page context
- `className?: string`

**Example:**
```tsx
import { VoiceChat } from '@/components/voice';

function MPPage({ mp }) {
  return (
    <VoiceChat
      apiEndpoint="/api/chat"
      apiKey={user.apiKey}
      provider="claude"
      context={{
        page: 'mp',
        mpId: mp.id,
        mpName: mp.name,
      }}
    />
  );
}
```

**API Endpoint Example:**
```ts
// app/api/chat/route.ts
export async function POST(req: Request) {
  const { provider, messages, context } = await req.json();

  // Call Claude or OpenAI with context-aware system prompt
  const response = await callAI(provider, messages, context);

  return Response.json({ response });
}
```

---

### VoiceNotes

Context-aware voice note-taking.

**Props:**
- `context: { type, id, title, metadata }` - What the note is about
- `onSave: (note) => Promise<void>` - Save callback
- `className?: string`

**Example:**
```tsx
import { VoiceNotes } from '@/components/voice';

function StatementPage({ statement }) {
  const saveNote = async (note) => {
    await fetch('/api/notes', {
      method: 'POST',
      body: JSON.stringify(note),
    });
  };

  return (
    <VoiceNotes
      context={{
        type: 'statement',
        id: statement.id,
        title: `${statement.madeBy.name} - ${statement.h2_en}`,
        metadata: { date: statement.time, speaker: statement.madeBy.name },
      }}
      onSave={saveNote}
    />
  );
}
```

---

### Voice Query Parser

Convert natural language to Neo4j Cypher queries.

**Example:**
```ts
import { parseVoiceQuery } from '@/components/voice';

// General query
const result = parseVoiceQuery("Show me Pierre Poilievre's votes on Bill C-21");
console.log(result.cypher);
// MATCH (mp:MP)-[v:VOTED]->(vote:Vote)-[:CONCERNS]->(bill:Bill)
// WHERE toLower(mp.name) CONTAINS "poilievre" AND bill.number = "BILL C-21"
// RETURN mp.name, vote.description, v.position, vote.date

// Context-aware query (on MP page)
const mpResult = parseVoiceQuery("What has he said about carbon tax?", {
  type: 'mp',
  mpId: 'pierre-poilievre',
  mpName: 'Pierre Poilievre'
});
console.log(mpResult.cypher);
// MATCH (mp:MP {id: "pierre-poilievre"})-[:MADE_BY]-(s:Statement)
// WHERE toLower(s.content_en) CONTAINS "carbon tax"
// RETURN s.content_en, s.time, s.h2_en
```

---

## Mobile Components

### MobileStatementCard

Twitter/Instagram-style speech card with swipe gestures.

```tsx
import { MobileStatementCard } from '@/components/mobile';

<MobileStatementCard
  statement={statement}
  onSwipeLeft={() => nextStatement()}
  onSwipeRight={() => prevStatement()}
  showFullContent={false}
  locale="en"
/>
```

**Features:**
- Party-color accent border
- Read more/less toggle
- Share, like, bookmark actions
- Swipeable for navigation

---

### MobileMPCard

Compact MP profile card for lists.

```tsx
import { MobileMPCard } from '@/components/mobile';

<MobileMPCard
  mp={mp}
  stats={{
    bills: 12,
    votes: 345,
    speeches: 89,
  }}
  locale="en"
/>
```

---

### MobileDebateCard

Debate preview card.

```tsx
import { MobileDebateCard } from '@/components/mobile';

<MobileDebateCard
  debate={{
    id: "123",
    date: "2025-11-16",
    statement_count: 150,
    speaker_count: 45,
  }}
  title="Question Period"
  preview="Today's debate featured discussion on housing..."
/>
```

---

### MobileBillCard

Bill card with progress indicator.

```tsx
import { MobileBillCard } from '@/components/mobile';

<MobileBillCard
  bill={{
    number: "C-21",
    session: "45-1",
    title: "An Act to amend...",
    status: "Second Reading",
    progress: 65,
  }}
/>
```

---

### MobileBottomNav

Sticky bottom navigation bar.

```tsx
import { MobileBottomNav } from '@/components/mobile';

// In layout
<MobileBottomNav locale="en" />
```

**Navigation Items:**
- Home
- Search
- Bookmarks
- Profile

---

### MobileHeader

Mobile-optimized header with voice search.

```tsx
import { MobileHeader } from '@/components/mobile';

<MobileHeader
  title="Pierre Poilievre"
  showSearch={true}
  onMenuClick={() => setMenuOpen(true)}
  locale="en"
/>
```

---

### SwipeableDrawer

Bottom sheet drawer with swipe-to-close.

```tsx
import { SwipeableDrawer } from '@/components/mobile';

<SwipeableDrawer
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Filters"
  height="half"
>
  {/* Filter content */}
</SwipeableDrawer>
```

**Heights:** `'half'`, `'full'`, `'auto'`

---

### MobileDebateViewer

Twitter/Instagram-style debate reader.

```tsx
import { MobileDebateViewer } from '@/components/mobile';

<MobileDebateViewer
  statements={debateStatements}
  locale="en"
/>
```

**Features:**
- Scroll mode: Infinite vertical scroll
- Focus mode: One statement at a time with swipe navigation
- Party filter: Show only specific party speeches
- Timeline scrubber: Color-coded dots for quick navigation

---

## Custom Hooks

### useMobileDetect

Detect device type and screen properties.

```tsx
import { useMobileDetect } from '@/hooks/useMobileDetect';

function MyComponent() {
  const { isMobile, isTablet, isIOS, screenWidth, orientation } = useMobileDetect();

  if (isMobile) {
    return <MobileView />;
  }
  return <DesktopView />;
}
```

**Returns:**
- `isMobile: boolean`
- `isTablet: boolean`
- `isDesktop: boolean`
- `isTouchDevice: boolean`
- `isIOS: boolean`
- `isAndroid: boolean`
- `screenWidth: number`
- `screenHeight: number`
- `orientation: 'portrait' | 'landscape'`

---

### useSwipeGesture

Swipe gesture detection.

```tsx
import { useSwipeGesture } from '@/hooks/useSwipeGesture';

function SwipeableCard() {
  const bind = useSwipeGesture({
    onSwipeLeft: () => console.log('Swiped left'),
    onSwipeRight: () => console.log('Swiped right'),
    threshold: 50,
    velocityThreshold: 0.3,
  });

  return <div {...bind()}>Swipe me!</div>;
}
```

**Alternative (no dependencies):**
```tsx
import { useSimpleSwipe } from '@/hooks/useSwipeGesture';

const swipeHandlers = useSimpleSwipe({
  onSwipeLeft,
  onSwipeRight,
});

return <div {...swipeHandlers}>Swipe me!</div>;
```

---

## Integration Examples

### Example 1: Mobile MP Profile Page

```tsx
// app/[locale]/mps/[id]/mobile-page.tsx
'use client';

import { useMobileDetect } from '@/hooks/useMobileDetect';
import { MobileHeader, MobileBottomNav } from '@/components/mobile';
import { VoiceChat, VoiceNotes } from '@/components/voice';
import { useState } from 'react';

export default function MobileMPPage({ mp }) {
  const { isMobile } = useMobileDetect();
  const [isChatOpen, setIsChatOpen] = useState(false);

  if (!isMobile) return <DesktopMPPage mp={mp} />;

  return (
    <>
      <MobileHeader title={mp.name} showSearch />

      {/* Content */}
      <div className="p-4">
        {/* Quick stats */}
        {/* Swipeable tabs */}
        {/* Voice notes */}
      </div>

      {/* Voice chat FAB */}
      <button
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-20 right-4 w-14 h-14 bg-red-600 rounded-full"
      >
        <Mic />
      </button>

      <SwipeableDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        title="Ask about this MP"
        height="full"
      >
        <VoiceChat
          apiEndpoint="/api/chat"
          apiKey={user.apiKey}
          provider="claude"
          context={{ page: 'mp', mpId: mp.id }}
        />
      </SwipeableDrawer>

      <MobileBottomNav />
    </>
  );
}
```

---

### Example 2: Mobile Debate Page

```tsx
// app/[locale]/debates/[id]/mobile-page.tsx
'use client';

import { MobileDebateViewer } from '@/components/mobile';

export default function MobileDebatePage({ debate, statements }) {
  return (
    <MobileDebateViewer statements={statements} locale="en" />
  );
}
```

---

## PWA Setup

### 1. Create Manifest

File: `public/manifest.json`

```json
{
  "name": "CanadaGPT",
  "short_name": "CanadaGPT",
  "description": "Canadian Parliamentary Data Platform",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0a0a",
  "theme_color": "#dc2626",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "permissions": ["microphone"],
  "features": ["voice-recognition", "web-share"]
}
```

### 2. Add to Layout

```tsx
// app/layout.tsx
export const metadata = {
  manifest: '/manifest.json',
};
```

### 3. Service Worker (Optional)

File: `public/sw.js`

```js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('canadagpt-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/manifest.json',
        // Add critical resources
      ]);
    })
  );
});
```

---

## Testing

### Mobile Testing Checklist

**iOS Safari:**
- [ ] Voice recognition works (requires HTTPS)
- [ ] Touch targets are at least 44x44px
- [ ] Swipe gestures work smoothly
- [ ] Bottom nav respects safe area
- [ ] No zoom on input focus (font-size >= 16px)

**Chrome Android:**
- [ ] Voice recognition works
- [ ] Haptic feedback works
- [ ] Pull-to-refresh disabled where needed
- [ ] Share API works

**General:**
- [ ] Responsive breakpoints work (320px, 375px, 414px, 768px)
- [ ] Smooth scrolling with momentum
- [ ] No layout shift on keyboard open
- [ ] Offline voice notes queue works

### Testing Tools

```bash
# Chrome DevTools Mobile Emulation
# 1. Open DevTools (F12)
# 2. Click Device Toolbar (Ctrl+Shift+M)
# 3. Select device: iPhone 14 Pro, Pixel 7, etc.

# Test on real device via network
npm run dev -- --host
# Visit http://YOUR_IP:3000 on mobile device
```

---

## Troubleshooting

### Voice Recognition Not Working

**Problem:** "Speech recognition not supported"

**Solutions:**
1. Ensure HTTPS (required for iOS Safari)
2. Check browser support (iOS 14.5+, Chrome Android 33+)
3. Grant microphone permission in browser settings
4. Test in supported browser (not Firefox)

---

### Swipe Gestures Not Working

**Problem:** Swipes not detected or interfering with scroll

**Solutions:**
1. Check if `@use-gesture/react` is installed
2. Adjust `threshold` and `velocityThreshold` values
3. Use `useSimpleSwipe` for basic swipe detection
4. Prevent default touch behavior where needed

---

### Bottom Nav Hidden Behind Content

**Problem:** Content overlaps bottom navigation

**Solution:**
```css
/* Add padding to page container */
.page-container {
  padding-bottom: 80px; /* Height of bottom nav + safe area */
}
```

---

### Voice Input Zoom on iOS

**Problem:** Input field zooms when focused

**Solution:**
```css
/* Ensure font-size is at least 16px */
.voice-search-input {
  font-size: 16px; /* Prevents iOS zoom */
}
```

---

### Performance Issues on Long Lists

**Problem:** Slow scrolling with many statements

**Solution:**
```tsx
// Use react-window for virtual scrolling
import { FixedSizeList as List } from 'react-window';

<List
  height={600}
  itemCount={statements.length}
  itemSize={200}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>
      <MobileStatementCard statement={statements[index]} />
    </div>
  )}
</List>
```

---

## Production Deployment

### HTTPS Requirements

Voice API **requires HTTPS** in production:

1. **Vercel/Netlify:** HTTPS automatic
2. **Custom server:** Use Let's Encrypt or Cloudflare
3. **Development:** Use `localhost` (HTTPS not required)

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_API_ENDPOINT=https://api.canadagpt.ca
NEO4J_URI=bolt://your-neo4j-instance
```

### Performance Tips

1. **Code Splitting:** Mobile components lazy-loaded on mobile devices only
2. **Image Optimization:** Use Next.js `<Image>` component
3. **Font Loading:** Preload critical fonts
4. **Analytics:** Track mobile vs desktop usage

---

## Support

**Issues:** https://github.com/your-repo/issues

**Documentation:** This file + component JSDoc comments

**Voice API Docs:** https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
