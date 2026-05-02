import { useEffect, useState, useCallback } from 'react';

interface UseFetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Custom hook for fetching data
 * @param url The URL to fetch from
 * @param options Additional fetch options
 * @returns Object containing data, loading state, and error
 */
export const useFetch = <T,>(url: string, options?: RequestInit): UseFetchState<T> => {
  const [state, setState] = useState<UseFetchState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    try {
      setState({ data: null, loading: true, error: null });
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
