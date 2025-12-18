import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';
import { createServerClient, createAdminClient } from '@/lib/supabase-server';
import { auth } from '@/auth';

// GET - Fetch existing summary
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ session: string; number: string }> }
) {
  try {
    const resolvedParams = await params;
    const supabase = await createServerClient();

    const { data, error } = await supabase
      .from('bill_summaries')
      .select('summary, model, generated_at')
      .eq('bill_session', resolvedParams.session)
      .eq('bill_number', resolvedParams.number)
      .single();

    if (error || !data) {
      return NextResponse.json(
        { error: 'No summary found' },
        { status: 404 }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching summary:', error);
    return NextResponse.json(
      { error: 'Failed to fetch summary' },
      { status: 500 }
    );
  }
}

// POST - Generate new summary
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ session: string; number: string }> }
) {
  try {
    const resolvedParams = await params;
    const body = await request.json();
    const { billTitle, billType, sponsor, votes, debates, lobbying, is_system_action } = body;

    // Check if ANTHROPIC_API_KEY is set
    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json(
        { error: 'AI service not configured' },
        { status: 503 }
      );
    }

    const anthropic = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
    });

    // Build context for the prompt
    const sponsorText = sponsor
      ? `Sponsor: ${sponsor.name}${sponsor.party ? ` (${sponsor.party})` : ''}`
      : 'Sponsor: Unknown';

    const voteCount = Array.isArray(votes) ? votes.length : 0;
    const debateCount = Array.isArray(debates) ? debates.length : 0;
    const lobbyingCount = lobbying?.organizations_lobbying || 0;

    const prompt = `Generate a concise, single-paragraph summary of this Canadian parliamentary bill (25-40 words):

Title: ${billTitle}
Type: ${billType || 'Unknown'}

Explain only what the bill aims to do - its main purpose and key changes it would make. Use plain language that a general audience can understand.

Tone: Educational, neutral, factual. No political commentary, no speculation, no information about who introduced it or parliamentary activity stats. Just explain what the bill does.`;

    const message = await anthropic.messages.create({
      model: 'claude-sonnet-4-5-20250929',
      max_tokens: 100,
      temperature: 0.5,
      messages: [{
        role: 'user',
        content: prompt
      }]
    });

    // Extract text content from response
    const summaryText = message.content
      .filter((block: any) => block.type === 'text')
      .map((block: any) => block.text)
      .join('\n\n');

    // Save summary to database
    const session = await auth();

    // For system actions, we still require authentication but don't require it for saving
    if (is_system_action || session?.user?.id) {
      // Use admin client to bypass RLS
      const supabase = createAdminClient();

      const { data, error } = await supabase
        .from('bill_summaries')
        .upsert({
          bill_number: resolvedParams.number,
          bill_session: resolvedParams.session,
          summary: summaryText,
          model: message.model,
          input_tokens: message.usage.input_tokens,
          output_tokens: message.usage.output_tokens,
          generated_by: session?.user?.id || null, // null for system actions without user
          generated_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }, {
          onConflict: 'bill_session,bill_number'
        });

      if (error) {
        console.error('Failed to save bill summary to database:', error);
        console.error('Summary details:', {
          bill_number: resolvedParams.number,
          bill_session: resolvedParams.session,
          user_id: session?.user?.id || 'system',
          is_system_action
        });
      } else {
        console.log('Successfully saved bill summary:', {
          bill_number: resolvedParams.number,
          bill_session: resolvedParams.session,
          is_system_action: is_system_action || false
        });
      }
    } else {
      console.warn('Cannot save summary - user not authenticated:', {
        hasSession: !!session,
        hasUser: !!session?.user,
        hasUserId: !!session?.user?.id,
        bill: `${resolvedParams.session}/${resolvedParams.number}`
      });
    }

    return NextResponse.json({
      summary: summaryText,
      tokens: {
        input: message.usage.input_tokens,
        output: message.usage.output_tokens,
        total: message.usage.input_tokens + message.usage.output_tokens
      },
      model: message.model,
      generated_at: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error generating bill summary:', error);

    // Handle specific Anthropic API errors
    if (error instanceof Anthropic.APIError) {
      return NextResponse.json(
        { error: `AI service error: ${error.message}` },
        { status: error.status || 500 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to generate summary' },
      { status: 500 }
    );
  }
}
