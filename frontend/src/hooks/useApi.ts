import useSWR from 'swr';
import api from '@/lib/api';

const fetcher = (url: string) => api.get(url).then(r => r.data);

export function useApi<T>(url: string | null, refreshInterval = 30000) {
  const { data, error, isLoading, mutate } = useSWR<T>(url, fetcher, {
    refreshInterval,
    revalidateOnFocus: true,
  });

  return { data, error, isLoading, refresh: mutate };
}