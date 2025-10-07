import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Image from 'next/image';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface Submission {
  id: string;
  song_id: string;
  user_id: string;
  score: number;
  photo_key: string;
  review_status: string;
  submitted_at: string;
}

export default function AdminReviewsPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['reviews', 'pending'],
    queryFn: async () => {
      const { data } = await api.get<Submission[]>('/reviews/pending');
      return data;
    }
  });

  const reviewMutation = useMutation({
    mutationFn: async ({ id, decision }: { id: string; decision: 'approved' | 'rejected' }) => {
      await api.post(`/reviews/${id}`, { decision });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews', 'pending'] })
  });

  return (
    <Layout title="スコアレビュー">
      <h2>レビュー待ち一覧</h2>
      {isLoading && <p>読み込み中...</p>}
      {error && <p>レビュー待ちスコアを取得できませんでした。</p>}
      <div style={{ display: 'grid', gap: 24 }}>
        {data?.map((submission) => (
          <article key={submission.id} style={{ border: '1px solid #ccd', padding: 16, borderRadius: 8 }}>
            <p>
              ユーザー: {submission.user_id} / スコア: {submission.score}
            </p>
            <p>提出日時: {new Date(submission.submitted_at).toLocaleString()}</p>
            <div style={{ maxWidth: 320, maxHeight: 240, overflow: 'hidden' }}>
              <Image
                src={`https://s3.amazonaws.com/kbdir-prod/${submission.photo_key}`}
                alt="スコア写真"
                width={320}
                height={240}
                style={{ objectFit: 'contain' }}
              />
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
              <button onClick={() => reviewMutation.mutate({ id: submission.id, decision: 'approved' })}>
                承認
              </button>
              <button onClick={() => reviewMutation.mutate({ id: submission.id, decision: 'rejected' })}>
                差し戻し
              </button>
            </div>
          </article>
        ))}
      </div>
    </Layout>
  );
}
