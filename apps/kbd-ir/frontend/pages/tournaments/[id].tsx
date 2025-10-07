import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface Machine {
  id: string;
  name: string;
  game_code: string;
  description?: string;
  songs: Song[];
}

interface Song {
  id: string;
  title: string;
  difficulty: string;
  score_cap_override?: number;
}

interface TournamentDetail {
  id: string;
  name: string;
  slug: string;
  circle_scope: string;
  visibility: string;
  status: string;
  score_cap_default: number;
  machines: Machine[];
}

export default function TournamentDetailPage() {
  const router = useRouter();
  const api = useApi();
  const id = router.query.id as string | undefined;
  const { data, isLoading, error } = useQuery({
    queryKey: ['tournament', id],
    queryFn: async () => {
      if (!id) return null;
      const { data } = await api.get<TournamentDetail>(`/tournaments/${id}`);
      return data;
    },
    enabled: Boolean(id)
  });

  return (
    <Layout title={data?.name ?? '大会詳細'}>
      {isLoading && <p>読み込み中...</p>}
      {error && <p>大会情報を取得できませんでした。</p>}
      {data && (
        <>
          <h2>{data.name}</h2>
          <p>ステータス: {data.status}</p>
          <p>スコア上限: {data.score_cap_default.toLocaleString()}</p>
          <section>
            <h3>機種と曲</h3>
            {data.machines.map((machine) => (
              <div key={machine.id} style={{ marginBottom: 24 }}>
                <h4>
                  {machine.name} ({machine.game_code})
                </h4>
                <p>{machine.description}</p>
                <ul>
                  {machine.songs.map((song) => (
                    <li key={song.id}>
                      {song.title} / {song.difficulty}
                      {song.score_cap_override && ` (上限: ${song.score_cap_override})`}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
        </>
      )}
    </Layout>
  );
}
