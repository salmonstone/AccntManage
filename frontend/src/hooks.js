import { useState, useEffect, useCallback, useRef } from 'react';

export function useApi(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn();
      setData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => { reload(); }, [reload]);

  return { data, loading, error, reload };
}

export function useNotification() {
  const [notification, setNotification] = useState(null);
  const timerRef = useRef(null);

  const notify = useCallback((message, type = 'info') => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setNotification({ message, type });
    timerRef.current = setTimeout(() => setNotification(null), 4000);
  }, []);

  return { notification, notify };
}

export function useWebSocket(onMessage) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const cbRef = useRef(onMessage);
  cbRef.current = onMessage;

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (cbRef.current) cbRef.current(data);
      } catch {}
    };
    ws.onclose = () => {
      setConnected(false);
      setTimeout(() => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
      }, 3000);
    };

    return () => ws.close();
  }, []);

  return { connected };
}
