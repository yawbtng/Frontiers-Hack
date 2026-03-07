'use client';

import React from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useNotifications } from '@/contexts/NotificationsContext';
import NotificationCard from './NotificationCard';

export default function NotificationsPanel() {
  const { notifications, isOpen, setIsOpen, markAllRead } = useNotifications();

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetContent side="right" className="w-[380px] sm:w-[420px] p-0">
        <SheetHeader className="px-4 pt-4 pb-2 border-b border-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-lg font-semibold">Agent Activity</SheetTitle>
            <button
              onClick={markAllRead}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              Mark all read
            </button>
          </div>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-80px)]">
          <div className="p-3 space-y-2">
            {notifications.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm py-12">
                No notifications yet. The agent will post updates here as it processes meetings.
              </div>
            ) : (
              notifications.map((n) => <NotificationCard key={n.id} notification={n} />)
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
