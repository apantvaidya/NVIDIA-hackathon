import { API_BASE_URL } from "./client";

export type RealtimeEvent = {
  type: string;
  ts?: string;
  payload?: any;
  [key: string]: any;
};

export type RealtimeListener = (event: RealtimeEvent) => void;

function toWsUrl(httpUrl: string): string {
  if (httpUrl.startsWith("https://")) return httpUrl.replace(/^https:\/\//, "wss://") + "/ws";
  if (httpUrl.startsWith("http://")) return httpUrl.replace(/^http:\/\//, "ws://") + "/ws";
  return httpUrl.replace(/^\/\//, "ws://") + "/ws";
}

export function connectRealtime(onEvent: RealtimeListener): () => void {
  const url = toWsUrl(API_BASE_URL);
  let socket: WebSocket | null = null;
  let closed = false;
  let reconnectTimer: number | undefined;

  const open = () => {
    if (closed) return;
    socket = new WebSocket(url);
    socket.onmessage = (msg) => {
      try {
        onEvent(JSON.parse(msg.data));
      } catch {
        // ignore non-JSON frames
      }
    };
    socket.onclose = () => {
      if (closed) return;
      reconnectTimer = window.setTimeout(open, 2000);
    };
    socket.onerror = () => {
      socket?.close();
    };
  };

  open();

  return () => {
    closed = true;
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    socket?.close();
  };
}
