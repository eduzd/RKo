import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { useAuth } from "@/src/context/AuthContext";
import { useCall } from "@/src/context/CallContext";
import { useRoomAudio } from "@/src/hooks/use-room-audio";
import { api, Room } from "@/src/utils/api";

interface VoiceRoomContextValue {
  /** The room the user is currently a member of (host or joined), if any. */
  activeRoomId: string | null;
  /** True once the user has minimized the room (left the room screen but is
   *  still connected — audio keeps flowing and a floating bubble shows). */
  minimized: boolean;
  /** Latest known snapshot of the active room (title, host, members...). */
  roomSnapshot: Room | null;
  /** Call when a room screen mounts / joins a room — makes it "active" so
   *  audio + the minimize bubble can track it globally. */
  enterRoom: (roomId: string) => void;
  /** Collapse the room screen into a floating bubble; audio keeps playing. */
  minimizeRoom: () => void;
  /** Clears the minimized flag (used right before navigating back in). */
  restoreRoom: () => void;
  /** Leaves the room on the server and clears all active-room state. */
  leaveActiveRoom: () => Promise<void>;
  /** Clears local state without calling the server (e.g. room already ended). */
  clearActiveRoom: () => void;
}

const VoiceRoomContext = createContext<VoiceRoomContextValue | undefined>(
  undefined,
);

export const VoiceRoomProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { user } = useAuth();
  const { sendSignal, subscribe } = useCall();
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [minimized, setMinimized] = useState(false);
  const [roomSnapshot, setRoomSnapshot] = useState<Room | null>(null);
  const activeRoomIdRef = useRef<string | null>(null);
  const minimizedRef = useRef(false);
  activeRoomIdRef.current = activeRoomId;
  minimizedRef.current = minimized;

  const clearActiveRoom = useCallback(() => {
    activeRoomIdRef.current = null;
    setActiveRoomId(null);
    setRoomSnapshot(null);
    setMinimized(false);
  }, []);

  const fetchRoom = useCallback(async (roomId: string) => {
    try {
      const r = await api.get<Room>(`/rooms/${roomId}`);
      if (activeRoomIdRef.current === roomId) setRoomSnapshot(r);
    } catch {
      if (activeRoomIdRef.current === roomId) clearActiveRoom();
    }
  }, [clearActiveRoom]);

  const enterRoom = useCallback(
    (roomId: string) => {
      activeRoomIdRef.current = roomId;
      setActiveRoomId(roomId);
      setMinimized(false);
      fetchRoom(roomId);
    },
    [fetchRoom],
  );

  const minimizeRoom = useCallback(() => setMinimized(true), []);
  const restoreRoom = useCallback(() => setMinimized(false), []);

  const leaveActiveRoom = useCallback(async () => {
    const id = activeRoomIdRef.current;
    if (!id) return;
    try {
      await api.post(`/rooms/${id}/leave`);
    } catch {
      // room may have already ended — still clear local state
    }
    clearActiveRoom();
  }, [clearActiveRoom]);

  // Keep the active room's snapshot fresh and detect it ending, regardless
  // of whether the room screen itself is currently mounted (minimized or not).
  useEffect(() => {
    const unsub = subscribe((event: any) => {
      const id = activeRoomIdRef.current;
      if (!id) return;
      if (event.type === "room_update" && event.room?.id === id) {
        setRoomSnapshot(event.room);
      } else if (
        (event.type === "room_ended" || event.type === "room_kicked") &&
        event.room_id === id
      ) {
        clearActiveRoom();
      }
    });
    return unsub;
  }, [subscribe, clearActiveRoom]);

  // Global WebRTC audio mesh for the active room — lives here (not inside the
  // room screen) so speaking/listening keeps working while minimized.
  useRoomAudio({
    roomId: activeRoomId || "",
    myId: user?.id || "",
    members: roomSnapshot?.members || [],
    sendSignal,
    subscribe,
  });

  return (
    <VoiceRoomContext.Provider
      value={{
        activeRoomId,
        minimized,
        roomSnapshot,
        enterRoom,
        minimizeRoom,
        restoreRoom,
        leaveActiveRoom,
        clearActiveRoom,
      }}
    >
      {children}
    </VoiceRoomContext.Provider>
  );
};

export function useVoiceRoom(): VoiceRoomContextValue {
  const ctx = useContext(VoiceRoomContext);
  if (!ctx) throw new Error("useVoiceRoom must be used within VoiceRoomProvider");
  return ctx;
}
