'use client';

import React, { useState } from 'react';
import { CheckCircle2, MessageCircleQuestion, Info, AlertCircle, X, Send } from 'lucide-react';
import { useNotifications } from '@/contexts/NotificationsContext';

interface Notification {
  id: string;
  type: 'info' | 'action_taken' | 'question' | 'error';
  title: string;
  message: string;
  status: string;
  created_at: string;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return 'just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

const ICON_MAP = {
  action_taken: <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />,
  question: <MessageCircleQuestion className="w-5 h-5 text-blue-500 flex-shrink-0" />,
  info: <Info className="w-5 h-5 text-gray-500 flex-shrink-0" />,
  error: <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />,
};

export default function NotificationCard({ notification }: { notification: Notification }) {
  const { replyToNotification, dismissNotification } = useNotifications();
  const [replyText, setReplyText] = useState('');
  const [sending, setSending] = useState(false);
  const isUnread = notification.status === 'unread';
  const isQuestion = notification.type === 'question' && notification.status !== 'answered';

  const handleReply = async () => {
    if (!replyText.trim()) return;
    setSending(true);
    await replyToNotification(notification.id, replyText.trim());
    setReplyText('');
    setSending(false);
  };

  return (
    <div className={`p-3 rounded-lg border ${isUnread ? 'bg-blue-50/50 border-blue-100' : 'bg-card border-border'} transition-colors`}>
      <div className="flex items-start gap-2">
        {ICON_MAP[notification.type] || ICON_MAP.info}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-foreground truncate">{notification.title}</span>
            {isUnread && <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">{notification.message}</p>
          <span className="text-xs text-muted-foreground mt-1 block">{timeAgo(notification.created_at)}</span>
        </div>
        {!isQuestion && (
          <button
            onClick={() => dismissNotification(notification.id)}
            className="p-1 rounded hover:bg-secondary text-muted-foreground flex-shrink-0"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {isQuestion && (
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleReply()}
            placeholder="Type your reply..."
            className="flex-1 px-2 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={sending}
          />
          <button
            onClick={handleReply}
            disabled={sending || !replyText.trim()}
            className="px-2 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
