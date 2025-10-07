import { useQuery } from '@tanstack/react-query';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface Submission {
  id: string;
  song_id: string;
  score: number;
  photo_key: string;
  review_status: string;
  submitted_at: string;
}

export default function MySubmissionsPage() {
  const api = useApi();
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-submissions'],
    queryFn: async () => {
      const { data } = await api.get<Submission[]>('/my/submissions');
      return data;
    }
  });

  return (
    <Layout title="提出済みスコア">
      <h2>提出済みスコア</h2>
      {isLoading && <p>読み込み中...</p>}
      {error && <p>スコアを取得できませんでした。</p>}
      <ul>
        {data?.map((submission) => (
          <li key={submission.id}>
            {submission.song_id} / {submission.score} 点 / {submission.review_status}
          </li>
        ))}
      </ul>
    </Layout>
  );
}
