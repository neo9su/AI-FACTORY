import { useEffect, useRef, useState } from 'react';
import { io, type Socket } from 'socket.io-client';

const WS_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
}

export function useWebSocket(projectId: string | null): {
  messages: WebSocketMessage[];
  isConnected: boolean;
  sendMessage: (message: unknown) => void;
} {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const socket = io(WS_URL, {
      path: '/ws',
      query: { project_id: projectId },
      transports: ['websocket', 'polling'],
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
      console.log('WebSocket connected for project:', projectId);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    });

    socket.on('message', (data: WebSocketMessage) => {
      setMessages((prev) => [...prev, data]);
    });

    socket.on('project_update', (data: WebSocketMessage) => {
      setMessages((prev) => [...prev, { ...data, type: 'project_update' }]);
    });

    socket.on('task_update', (data: WebSocketMessage) => {
      setMessages((prev) => [...prev, { ...data, type: 'task_update' }]);
    });

    socket.on('agent_update', (data: WebSocketMessage) => {
      setMessages((prev) => [...prev, { ...data, type: 'agent_update' }]);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [projectId]);

  const sendMessage = (message: unknown): void => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('message', message);
    }
  };

  return { messages, isConnected, sendMessage };
}
