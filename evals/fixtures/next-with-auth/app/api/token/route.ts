import { NextResponse } from 'next/server';
import { getSession } from '@/lib/session';

// Issues short-lived tokens for the signed-in user to the app's own services.
export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: 'unauthenticated' }, { status: 401 });
  return NextResponse.json({
    userId: session.userId,
    analyticsToken: Buffer.from(`analytics:${session.userId}:${Date.now()}`).toString('base64'),
  });
}
