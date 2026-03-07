'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

interface Notification {
  id: string;
  type: 'info' | 'action_taken' | 'question' | 'error';
  title: string;
  message: string;
  meeting_id?: string | null;
  session_id?: string | null;
  status: 'unread' | 'read' | 'answered' | 'dismissed';
  created_at: string;
}

interface NotificationsContextType {
  notifications: Notification[];
  unreadCount: number;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  fetchNotifications: () => Promise<void>;
  replyToNotification: (id: string, message: string) => Promise<void>;
  dismissNotification: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
}

const NotificationsContext = createContext<NotificationsContextType | null>(null);

const BACKEND_URL = 'http://localhost:5167';

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/friday/notifications/unread-count`);
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.count);
      }
    } catch {
      // Backend not available — silently ignore
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/friday/notifications?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
        setUnreadCount(data.filter((n: Notification) => n.status === 'unread').length);
      }
    } catch {
      // Backend not available
    }
  }, []);

  const replyToNotification = useCallback(async (id: string, message: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/friday/notifications/${id}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (res.ok) {
        await fetchNotifications();
      }
    } catch (e) {
      console.error('Failed to reply to notification:', e);
    }
  }, [fetchNotifications]);

  const dismissNotification = useCallback(async (id: string) => {
    try {
      await fetch(`${BACKEND_URL}/friday/notifications/${id}/dismiss`, { method: 'POST' });
      await fetchNotifications();
    } catch (e) {
      console.error('Failed to dismiss notification:', e);
    }
  }, [fetchNotifications]);

  const markAllRead = useCallback(async () => {
    try {
      await fetch(`${BACKEND_URL}/friday/notifications/mark-read`, { method: 'POST' });
      await fetchNotifications();
    } catch (e) {
      console.error('Failed to mark all read:', e);
    }
  }, [fetchNotifications]);

  // Poll unread count every 30s
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30_000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // Fetch full list when panel opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  return (
    <NotificationsContext.Provider
      value={{
        notifications,
        unreadCount,
        isOpen,
        setIsOpen,
        fetchNotifications,
        replyToNotification,
        dismissNotification,
        markAllRead,
      }}
    >
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider');
  return ctx;
}
