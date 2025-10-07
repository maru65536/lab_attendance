import axios from 'axios';
import { useEffect, useMemo } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_KBDIR_API ?? '/api/kbd_ir';

export function useApi() {
  const instance = useMemo(() => {
    const client = axios.create({
      baseURL: API_BASE,
      withCredentials: true
    });
    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('kbd-ir-token');
      if (token) {
        client.defaults.headers.common.Authorization = `Bearer ${token}`;
      }
    }
    return client;
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = window.localStorage.getItem('kbd-ir-token');
    if (token) {
      instance.defaults.headers.common.Authorization = `Bearer ${token}`;
    }
  }, [instance]);

  return instance;
}
