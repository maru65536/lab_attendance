import Head from 'next/head';
import { ReactNode } from 'react';
import styles from '../styles/Layout.module.css';

interface Props {
  title?: string;
  children: ReactNode;
}

export function Layout({ title = 'KBD-IR', children }: Props) {
  return (
    <>
      <Head>
        <title>{title}</title>
      </Head>
      <div className={styles.wrapper}>
        <header className={styles.header}>
          <h1>KBD-IR 管理画面</h1>
        </header>
        <main className={styles.main}>{children}</main>
      </div>
    </>
  );
}
