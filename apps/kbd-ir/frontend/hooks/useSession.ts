import { useQuery } from '@tanstack/react-query';
import { useApi } from './useApi';

type SessionUser = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  circle: string;
};

export function useSession() {
  const api = useApi();
  return useQuery({
    queryKey: ['session'],
    queryFn: async () => {
      const { data } = await api.get<SessionUser>('/auth/me');
      return data;
    },
    staleTime: 60_000
  });
}
