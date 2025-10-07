import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface Tournament {
  id: string;
  name: string;
  slug: string;
  circle_scope: string;
  visibility: string;
  status: string;
  score_cap_default: number;
}

export default function AdminTournamentsPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState({
    name: '',
    slug: '',
    circle_scope: 'kbm',
    visibility: 'public',
    status: 'draft',
    score_cap_default: 1000000
  });

  const listQuery = useQuery({
    queryKey: ['admin', 'tournaments'],
    queryFn: async () => {
      const { data } = await api.get<Tournament[]>('/tournaments');
      return data;
    }
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      await api.post('/tournaments', formState);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'tournaments'] });
      setFormState({ ...formState, name: '', slug: '' });
    }
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <Layout title="大会管理">
      <h2>大会管理</h2>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12, maxWidth: 420 }}>
        <label>
          大会名
          <input
            value={formState.name}
            onChange={(evt) => setFormState((prev) => ({ ...prev, name: evt.target.value }))}
            required
          />
        </label>
        <label>
          スラッグ
          <input
            value={formState.slug}
            onChange={(evt) => setFormState((prev) => ({ ...prev, slug: evt.target.value }))}
            required
          />
        </label>
        <label>
          サークル範囲
          <select
            value={formState.circle_scope}
            onChange={(evt) => setFormState((prev) => ({ ...prev, circle_scope: evt.target.value }))}
          >
            <option value="kbm">KBM</option>
            <option value="bbd">BBD</option>
            <option value="joint">合同</option>
          </select>
        </label>
        <label>
          公開設定
          <select
            value={formState.visibility}
            onChange={(evt) => setFormState((prev) => ({ ...prev, visibility: evt.target.value }))}
          >
            <option value="public">公開</option>
            <option value="ops_test">運営テスト</option>
          </select>
        </label>
        <label>
          ステータス
          <select
            value={formState.status}
            onChange={(evt) => setFormState((prev) => ({ ...prev, status: evt.target.value }))}
          >
            <option value="draft">ドラフト</option>
            <option value="scheduled">予定</option>
            <option value="open">受付中</option>
            <option value="closed">終了</option>
            <option value="archived">アーカイブ</option>
          </select>
        </label>
        <label>
          スコア上限
          <input
            type="number"
            value={formState.score_cap_default}
            onChange={(evt) => setFormState((prev) => ({ ...prev, score_cap_default: Number(evt.target.value) }))}
          />
        </label>
        <button type="submit" disabled={createMutation.isPending}>
          大会を作成
        </button>
      </form>

      <section style={{ marginTop: 32 }}>
        <h3>既存の大会</h3>
        {listQuery.isLoading && <p>読み込み中...</p>}
        {listQuery.data && (
          <ul>
            {listQuery.data.map((tournament) => (
              <li key={tournament.id}>
                {tournament.name} / {tournament.circle_scope} / {tournament.visibility} / {tournament.status}
              </li>
            ))}
          </ul>
        )}
      </section>
    </Layout>
  );
}
