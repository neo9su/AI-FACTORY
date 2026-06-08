'use client';

import { useState } from 'react';

export default function LoginModal({ onClose, onLogin }: {
  onClose: () => void;
  onLogin: (token: string, user: { username: string; role: string }) => void;
}) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    username: '',
    password: '',
    email: '',
    fullName: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const url = isRegister ? `${API}/api/v1/auth/register` : `${API}/api/v1/auth/login`;
      const body = isRegister
        ? { email: form.email, username: form.username, password: form.password, full_name: form.fullName }
        : { username: form.username, password: form.password };
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail || 'Request failed');
        return;
      }
      if (isRegister) {
        setIsRegister(false);
        setError('✅ Registered! Now login.');
        return;
      }
      // Login success
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify({ username: form.username, role: 'member' }));
      onLogin(data.access_token, { username: form.username, role: 'member' });
    } catch (err) {
      setError('Connection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl p-8 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
        <h2 className="text-2xl font-bold text-gray-900 mb-1">
          {isRegister ? '注册' : '登录'}
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          {isRegister ? '创建你的 AI Factory 账户' : '登录你的 AI Factory 账户'}
        </p>

        {error && (
          <div className={`p-3 rounded-lg text-sm mb-4 ${
            error.startsWith('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <>
              <input
                type="email"
                placeholder="邮箱"
                value={form.email}
                onChange={e => setForm({...form, email: e.target.value})}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                placeholder="全名（选填）"
                value={form.fullName}
                onChange={e => setForm({...form, fullName: e.target.value})}
                className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </>
          )}
          <input
            type="text"
            placeholder="用户名"
            value={form.username}
            onChange={e => setForm({...form, username: e.target.value})}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="password"
            placeholder="密码"
            value={form.password}
            onChange={e => setForm({...form, password: e.target.value})}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '注册' : '登录')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {isRegister ? '已有账户？→ 登录' : '没有账户？→ 注册'}
          </button>
        </div>

        <button onClick={onClose} className="mt-4 w-full py-2 text-sm text-gray-400 hover:text-gray-600">
          取消
        </button>
      </div>
    </div>
  );
}
