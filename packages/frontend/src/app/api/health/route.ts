/**
 * Health check endpoint for Cloud Run health checks and monitoring
 * Returns 200 OK if the application is running
 */
export async function GET() {
  return new Response(
    JSON.stringify({
      status: 'ok',
      timestamp: new Date().toISOString(),
      service: 'canadagpt-frontend',
    }),
    {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );
}
