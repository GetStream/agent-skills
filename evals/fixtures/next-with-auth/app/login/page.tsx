import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

async function login(formData: FormData) {
  'use server';
  const userId = String(formData.get('userId') || '').trim();
  const name = String(formData.get('name') || '').trim();
  if (!userId) return;
  const store = await cookies();
  store.set('session', `${userId}:${name}`, { httpOnly: true, path: '/' });
  redirect('/');
}

export default function LoginPage() {
  return (
    <main style={{ padding: 24 }}>
      <h1>Sign in</h1>
      <form action={login}>
        <input name="userId" placeholder="user id" required />
        <input name="name" placeholder="display name" />
        <button type="submit">Sign in</button>
      </form>
    </main>
  );
}
