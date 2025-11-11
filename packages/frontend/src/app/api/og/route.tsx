/**
 * Dynamic Open Graph Image Generation
 *
 * Generates rich social media preview images with:
 * - MP photos for MP-related cards
 * - Maple leaf logo for other content
 * - Card text/description overlay
 */

import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

// Helper to fetch image and convert to base64
async function getImageAsBase64(url: string): Promise<string | null> {
  try {
    const response = await fetch(url);
    if (!response.ok) return null;

    const arrayBuffer = await response.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    const contentType = response.headers.get('content-type') || 'image/jpeg';
    return `data:${contentType};base64,${base64}`;
  } catch (error) {
    console.error('Failed to fetch image:', error);
    return null;
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const title = searchParams.get('title') || 'CanadaGPT';
    const description = searchParams.get('description') || '';
    const imageUrl = searchParams.get('image'); // MP photo URL
    const type = searchParams.get('type') || 'default'; // 'mp', 'speech', 'default'

    // Base URL for assets
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://canadagpt.ca';

    // Fetch logo as base64 for fallback
    const logoUrl = `${baseUrl}/maple-leaf-logo-512.png`;
    const logoBase64 = await getImageAsBase64(logoUrl);

    // Fetch MP photo if provided
    let mpPhotoBase64: string | null = null;
    if (imageUrl) {
      const fullImageUrl = imageUrl.startsWith('http') ? imageUrl : `${baseUrl}${imageUrl}`;
      mpPhotoBase64 = await getImageAsBase64(fullImageUrl);
    }

    // Use MP photo if available, otherwise use logo
    const displayImage = mpPhotoBase64 || logoBase64;

    return new ImageResponse(
      (
        <div
          style={{
            height: '100%',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#1a1a1a',
            padding: '60px',
            fontFamily: 'system-ui, sans-serif',
          }}
        >
          {/* Background gradient */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'linear-gradient(135deg, #DC143C 0%, #8B0000 100%)',
              opacity: 0.1,
            }}
          />

          {/* Content */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              height: '100%',
              position: 'relative',
              zIndex: 1,
            }}
          >
            {/* Text Content */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                maxWidth: displayImage ? '60%' : '100%',
                paddingRight: displayImage ? '40px' : '0',
              }}
            >
              {/* Title */}
              <div
                style={{
                  fontSize: '52px',
                  fontWeight: 'bold',
                  color: '#ffffff',
                  marginBottom: '20px',
                  lineHeight: 1.2,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {title}
              </div>

              {/* Description */}
              {description && (
                <div
                  style={{
                    fontSize: '28px',
                    color: '#cccccc',
                    lineHeight: 1.4,
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {description}
                </div>
              )}

              {/* CanadaGPT branding */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginTop: '40px',
                  fontSize: '24px',
                  color: '#DC143C',
                  fontWeight: '600',
                }}
              >
                <div style={{ marginRight: '12px' }}>🍁</div>
                CanadaGPT
              </div>
            </div>

            {/* Image (MP photo or logo) */}
            {displayImage && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: mpPhotoBase64 ? '320px' : '280px',
                  height: mpPhotoBase64 ? '400px' : '280px',
                  flexShrink: 0,
                }}
              >
                <img
                  src={displayImage}
                  alt=""
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: mpPhotoBase64 ? 'cover' : 'contain',
                    borderRadius: mpPhotoBase64 ? '16px' : '0',
                    border: mpPhotoBase64 ? '4px solid #DC143C' : 'none',
                  }}
                />
              </div>
            )}
          </div>
        </div>
      ),
      {
        width: 1200,
        height: 630,
      }
    );
  } catch (error) {
    console.error('Failed to generate OG image:', error);

    // Return a simple fallback image
    return new ImageResponse(
      (
        <div
          style={{
            height: '100%',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#1a1a1a',
            fontSize: '48px',
            fontWeight: 'bold',
            color: '#ffffff',
          }}
        >
          🍁 CanadaGPT
        </div>
      ),
      {
        width: 1200,
        height: 630,
      }
    );
  }
}
