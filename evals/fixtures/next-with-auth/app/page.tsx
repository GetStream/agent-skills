import { redirect } from 'next/navigation';
import { getSession } from '@/lib/session';

export default async function Home() {
  const session = await getSession();
  if (!session) redirect('/login');
  return (
    <main style={{ padding: 24 }}>
      <h1>Welcome back, {session.name}</h1>
      <p>Your workspace dashboard.</p>
    </main>
  );
}
