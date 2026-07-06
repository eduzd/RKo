import { Ionicons } from "@expo/vector-icons";
import * as Haptics from "expo-haptics";
import { usePathname, useRouter } from "expo-router";
import React from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Avatar } from "@/src/components/Avatar";
import { useVoiceRoom } from "@/src/context/VoiceRoomContext";

/**
 * Floating "minimized voice room" bubble — HelloTalk style. Shown globally
 * (above the tab bar, on any screen) whenever the user has minimized a live
 * room they're still connected to. Tapping it re-opens the room; the small
 * close button leaves the room entirely without reopening it.
 */
export function MinimizedRoomBubble() {
  const { activeRoomId, minimized, roomSnapshot, restoreRoom, leaveActiveRoom } =
    useVoiceRoom();
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();

  const onTabsScreen = pathname?.startsWith("/") && !pathname?.startsWith("/room/");
  if (!activeRoomId || !minimized) return null;

  const host = roomSnapshot?.host;
  const bottomOffset =
    insets.bottom + (onTabsScreen ? 56 + Math.max(insets.bottom, 12) + 10 + 14 : 24);

  return (
    <View
      style={[styles.wrap, { bottom: bottomOffset }]}
      pointerEvents="box-none"
      testID="voice-room-bubble"
    >
      <Pressable
        style={styles.bubble}
        onPress={() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
          restoreRoom();
          router.push(`/room/${activeRoomId}`);
        }}
      >
        <Avatar name={host?.name} url={host?.avatar_url} size={48} />
        <View style={styles.liveDot} />
      </Pressable>
      <Pressable
        testID="voice-room-bubble-close"
        style={styles.closeBtn}
        hitSlop={8}
        onPress={() => leaveActiveRoom()}
      >
        <Ionicons name="close" size={12} color="#FFFFFF" />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    right: 16,
    zIndex: 999,
  },
  bubble: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2A2154",
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.5)",
    shadowColor: "#000",
    shadowOpacity: 0.35,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 8,
  },
  liveDot: {
    position: "absolute",
    top: -1,
    left: -1,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#F87171",
    borderWidth: 1.5,
    borderColor: "#FFFFFF",
  },
  closeBtn: {
    position: "absolute",
    top: -4,
    right: -4,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "#4B3F87",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: "#FFFFFF",
  },
});
