import { cookies } from 'next/headers';

// The app's own session model: a signed-in user is a `session` cookie holding the
// user id. Real apps sign this; the fixture keeps it plain.
export type Session = { userId: string; name: string };

export async function getSession(): Promise<Session | null> {
  const store = await cookies();
  const raw = store.get('session')?.value;
  if (!raw) return null;
  const [userId, name] = raw.split(':');
  return userId ? { userId, name: name || userId } : null;
}
