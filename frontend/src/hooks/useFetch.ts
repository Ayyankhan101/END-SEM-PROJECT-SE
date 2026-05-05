import { useEffect, useState, useCallback } from 'react';

interface UseFetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseFetchOptions extends RequestInit {
  skipInitialLoading?: boolean;
}

/**
 * Custom hook for fetching data
 * @param url The URL to fetch from
 * @param options Additional fetch options (including skipInitialLoading)
 * @returns Object containing data, loading state, and error
 */
export const useFetch = <T,>(url: string, options?: UseFetchOptions): UseFetchState<T> => {
  const skipLoading = options?.skipInitialLoading ?? false;
  
  const [state, setState] = useState<UseFetchState<T>>({
    data: null,
    loading: !skipLoading,
    error: null,
  });

  const fetchData = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const json = await response.json();
      setState({ data: json, loading: false, error: null });
    } catch (error) {
      setState({ data: null, loading: false, error: error as Error });
    }
  }, [url, options]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return state;
};

export default useFetch;
