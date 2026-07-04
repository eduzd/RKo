import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import React from "react";
import { Platform, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useNotifications } from "@/src/context/NotificationsContext";
import { useTheme } from "@/src/context/ThemeContext";
import { fonts } from "@/src/theme";

export default function TabsLayout() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { chatUnread, momentsUnread, profileUnread } = useNotifications();
  // Reserve room for the device's home indicator / nav bar, but keep a
  // comfortable minimum gap so the bar never sits flush against the edge.
  const bottomGap = Math.max(insets.bottom, 12);

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors.onSurfaceSecondary,
        tabBarHideOnKeyboard: true,
        tabBarLabelStyle: {
          fontFamily: fonts.textBold,
          fontSize: 11,
        },
        tabBarItemStyle: {
          paddingTop: 4,
        },
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.divider,
          borderTopWidth: StyleSheet.hairlineWidth,
          // Comfortable content height + safe-area gap (min 12) so the bar
          // stays lifted above the home indicator on every device.
          height: 56 + bottomGap,
          paddingBottom: bottomGap,
          paddingTop: 8,
          ...Platform.select({
            ios: {
              shadowColor: "#0F172A",
              shadowOpacity: 0.06,
              shadowRadius: 10,
              shadowOffset: { width: 0, height: -3 },
            },
            android: { elevation: 12 },
            default: {},
          }),
        },
      }}
    >
      <Tabs.Screen
        name="chats"
        options={{
          title: "Chats",
          tabBarButtonTestID: "tab-chats",
          tabBarBadge:
            chatUnread > 0 ? (chatUnread > 99 ? "99+" : chatUnread) : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.error,
            color: "#FFFFFF",
            fontFamily: fonts.textBold,
            fontSize: 10,
          },
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="chatbubbles" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="connect"
        options={{
          title: "Connect",
          tabBarButtonTestID: "tab-connect",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="moments"
        options={{
          title: "Moments",
          tabBarButtonTestID: "tab-moments",
          tabBarBadge:
            momentsUnread > 0
              ? momentsUnread > 99
                ? "99+"
                : momentsUnread
              : undefined,
          tabBarBadgeStyle: {
            backgroundColor: colors.error,
            color: "#FFFFFF",
            fontFamily: fonts.textBold,
            fontSize: 10,
          },
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="planet" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="voice"
        options={{
          title: "Voice",
          tabBarButtonTestID: "tab-voice",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="mic" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Me",
          tabBarButtonTestID: "tab-profile",
          tabBarIcon: ({ color, size }) => (
            <View>
              <Ionicons name="person" size={size} color={color} />
              {profileUnread > 0 && (
                <View
                  testID="profile-tab-dot"
                  style={[styles.tabDot, { borderColor: colors.surface }]}
                />
              )}
            </View>
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabDot: {
    position: "absolute",
    top: -2,
    right: -3,
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: "#EF4444",
    borderWidth: 1.5,
  },
});
