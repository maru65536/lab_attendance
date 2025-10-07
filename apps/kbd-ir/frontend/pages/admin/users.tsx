import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Layout } from '../../components/Layout';
import { useApi } from '../../hooks/useApi';

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  circle: string;
  is_active: boolean;
}

export default function AdminUsersPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const { data } = await api.get<User[]>('/admin/users');
      return data;
    }
  });

  const promoteMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      await api.patch(`/admin/users/${userId}/role`, { role });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
  });

  return (
    <Layout title="ユーザー管理">
      <h2>ユーザー管理</h2>
      {isLoading && <p>読み込み中...</p>}
      {error && <p>ユーザー一覧を取得できませんでした。</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th align="left">氏名</th>
            <th align="left">メール</th>
            <th align="left">ロール</th>
            <th align="left">サークル</th>
            <th align="left">操作</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((user) => (
            <tr key={user.id} style={{ borderBottom: '1px solid #dde' }}>
              <td>{user.display_name}</td>
              <td>{user.email}</td>
              <td>{user.role}</td>
              <td>{user.circle}</td>
              <td>
                <button
                  onClick={() => promoteMutation.mutate({ userId: user.id, role: user.role.includes('admin') ? user.role : `${user.circle}-admin` })}
                >
                  {user.role.includes('admin') ? '権限更新' : '管理者に昇格'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Layout>
  );
}
