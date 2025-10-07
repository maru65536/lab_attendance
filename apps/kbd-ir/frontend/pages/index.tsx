import Link from 'next/link';
import { Layout } from '../components/Layout';
import { useSession } from '../hooks/useSession';

export default function HomePage() {
  const { data, isLoading, error } = useSession();

  if (isLoading) {
    return (
      <Layout title="KBD-IR">
        <p>読み込み中...</p>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout title="ログイン">
        <p>セッション情報を取得できませんでした。<Link href="/login">ログイン</Link>してください。</p>
      </Layout>
    );
  }

  return (
    <Layout title="ダッシュボード">
      <h2>{data.display_name} さん、ようこそ。</h2>
      <div>
        <ul>
          <li><Link href="/tournaments">大会一覧</Link></li>
          <li><Link href="/submissions">提出済みスコア</Link></li>
          {['superadmin', 'kbm-admin', 'bbd-admin'].includes(data.role) && (
            <>
              <li><Link href="/admin/tournaments">大会管理</Link></li>
              <li><Link href="/admin/reviews">スコアレビュー</Link></li>
              <li><Link href="/admin/users">ユーザー管理</Link></li>
            </>
          )}
        </ul>
      </div>
    </Layout>
  );
}
