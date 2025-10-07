import { FormEvent, useState } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '../components/Layout';
import { useApi } from '../hooks/useApi';

export default function LoginPage() {
  const api = useApi();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const { data } = await api.post('/auth/login', { email, password });
      window.localStorage.setItem('kbd-ir-token', data.access_token);
      api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
      router.push('/');
    } catch (err) {
      setError('ログインに失敗しました');
    }
  };

  return (
    <Layout title="ログイン">
      <form onSubmit={handleSubmit} style={{ maxWidth: 320, margin: '40px auto', display: 'grid', gap: 12 }}>
        <label>
          メールアドレス
          <input type="email" value={email} onChange={(evt) => setEmail(evt.target.value)} required />
        </label>
        <label>
          パスワード
          <input type="password" value={password} onChange={(evt) => setPassword(evt.target.value)} required />
        </label>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <button type="submit">ログイン</button>
      </form>
    </Layout>
  );
}
