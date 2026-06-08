'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import LoginModal from '@/components/login-modal';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) router.push('/dashboard');
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <LoginModal
        onClose={() => router.back()}
        onLogin={(token, user) => {
          localStorage.setItem('user', JSON.stringify(user));
          router.push('/dashboard');
        }}
      />
    </div>
  );
}
