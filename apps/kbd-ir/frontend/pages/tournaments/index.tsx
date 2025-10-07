import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface Tournament {
  id: string;
  name: string;
  slug: string;
  circle_scope: string;
  visibility: string;
  status: string;
}

export default function TournamentListPage() {
  const api = useApi();
  const { data, isLoading, error } = useQuery({
    queryKey: ['tournaments'],
    queryFn: async () => {
      const { data } = await api.get<Tournament[]>('/tournaments');
      return data;
    }
  });

  return (
    <Layout title="大会一覧">
      <h2>大会一覧</h2>
      {isLoading && <p>読み込み中...</p>}
      {error && <p>大会を取得できませんでした。</p>}
      <ul>
        {data?.map((tournament) => (
          <li key={tournament.id}>
            <Link href={`/tournaments/${tournament.id}`}>{tournament.name}</Link>
            <span style={{ marginLeft: 8, fontSize: '0.85rem', color: '#555' }}>
              {tournament.circle_scope} / {tournament.visibility} / {tournament.status}
            </span>
          </li>
        ))}
      </ul>
    </Layout>
  );
}
