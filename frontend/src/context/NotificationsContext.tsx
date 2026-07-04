import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { useAuth } from "@/src/context/AuthContext";
import { useChatSocket } from "@/src/hooks/use-chat-socket";
import { api, Conversation } from "@/src/utils/api";

interface NotificationCounts {
  moments_unread: number;
  profile_unread: number;
}

interface NotificationsContextValue {
  /** Total unread messages across all chat conversations. */
  chatUnread: number;
  /** Likes / comments / replies on the current user's own moments. */
  momentsUnread: number;
  /** New followers + new profile visitors (shown as a dot on "Me"). */
  profileUnread: number;
  refresh: () => void;
  markMomentsRead: () => void;
  markProfileRead: () => void;
}

const NotificationsContext = createContext<NotificationsContextValue>({
  chatUnread: 0,
  momentsUnread: 0,
  profileUnread: 0,
  refresh: () => {},
  markMomentsRead: () => {},
  markProfileRead: () => {},
});

export const NotificationsProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { user } = useAuth();
  const [chatUnread, setChatUnread] = useState(0);
  const [momentsUnread, setMomentsUnread] = useState(0);
  const [profileUnread, setProfileUnread] = useState(0);

  const refresh = useCallback(() => {
    if (!user) return;
    api
      .get<Conversation[]>("/chats")
      .then((convs) =>
        setChatUnread(convs.reduce((sum, c) => sum + (c.unread || 0), 0)),
      )
      .catch(() => {});
    api
      .get<NotificationCounts>("/notifications/counts")
      .then((c) => {
        setMomentsUnread(c.moments_unread);
        setProfileUnread(c.profile_unread);
      })
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) {
      setChatUnread(0);
      setMomentsUnread(0);
      setProfileUnread(0);
      return;
    }
    refresh();
    const t = setInterval(refresh, 12000);
    return () => clearInterval(t);
  }, [user, refresh]);

  useChatSocket(
    useCallback(
      (event) => {
        if (event.type === "new_message") refresh();
      },
      [refresh],
    ),
  );

  const markMomentsRead = useCallback(() => {
    setMomentsUnread(0);
    api.post("/notifications/read?category=moments").catch(() => {});
  }, []);

  const markProfileRead = useCallback(() => {
    setProfileUnread(0);
    api.post("/notifications/read?category=profile").catch(() => {});
  }, []);

  return (
    <NotificationsContext.Provider
      value={{
        chatUnread,
        momentsUnread,
        profileUnread,
        refresh,
        markMomentsRead,
        markProfileRead,
      }}
    >
      {children}
    </NotificationsContext.Provider>
  );
};

export const useNotifications = () => useContext(NotificationsContext);
