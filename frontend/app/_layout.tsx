import {
  Figtree_600SemiBold,
  Figtree_700Bold,
} from "@expo-google-fonts/figtree";
import {
  Nunito_400Regular,
  Nunito_600SemiBold,
  Nunito_700Bold,
} from "@expo-google-fonts/nunito";
import { useFonts } from "expo-font";
import * as Linking from "expo-linking";
import { Stack, useRouter } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { Platform } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/src/context/AuthContext";
import { CallProvider } from "@/src/context/CallContext";
import { NotificationsProvider } from "@/src/context/NotificationsContext";
import { ThemeProvider, useTheme } from "@/src/context/ThemeContext";
import { useIconFonts } from "@/src/hooks/use-icon-fonts";
import { Notifications, pushSupported } from "@/src/utils/push-native";

SplashScreen.preventAutoHideAsync();

// 1. Foreground handler — MODULE SCOPE, before any component mounts.
if (pushSupported && Notifications) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

// 2. Android notification channel — MODULE SCOPE, must exist before any
// push can arrive (created lazily inside a flow would be too late).
if (pushSupported && Notifications && Platform.OS === "android") {
  Notifications.setNotificationChannelAsync("default", {
    name: "Default",
    importance: Notifications.AndroidImportance.MAX,
    sound: "default",
  });
}

function ThemedApp() {
  const { mode } = useTheme();
  return (
    <AuthProvider>
      <NotificationsProvider>
        <CallProvider>
          <StatusBar style={mode === "dark" ? "light" : "dark"} />
          <Stack screenOptions={{ headerShown: false }} />
        </CallProvider>
      </NotificationsProvider>
    </AuthProvider>
  );
}

export default function RootLayout() {
  const router = useRouter();
  const [iconsLoaded, iconsError] = useIconFonts();
  const [fontsLoaded, fontsError] = useFonts({
    Figtree_600SemiBold,
    Figtree_700Bold,
    Nunito_400Regular,
    Nunito_600SemiBold,
    Nunito_700Bold,
  });

  const ready = (iconsLoaded || !!iconsError) && (fontsLoaded || !!fontsError);

  useEffect(() => {
    if (ready) SplashScreen.hideAsync();
  }, [ready]);

  // Push notification tap handling — native only, and only where push is
  // actually supported (see src/utils/push-native.ts).
  useEffect(() => {
    if (!pushSupported || !Notifications) return;

    const openTarget = (data: Record<string, unknown>) => {
      const url = (data.deeplink || data.action_url) as string | undefined;
      if (!url) return;
      if (url.startsWith("http")) Linking.openURL(url);
      else router.push(url as never);
    };

    // Warm tap — user taps the notification while the app is open.
    const tapSub = Notifications.addNotificationResponseReceivedListener(
      (response) => {
        openTarget(response.notification.request.content.data || {});
      },
    );

    // Cold-start tap — app was killed, user tapped the notification to open it.
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (!response) return;
      openTarget(response.notification.request.content.data || {});
    });

    return () => {
      tapSub.remove();
    };
  }, [router]);

  if (!ready) return null;

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <KeyboardProvider>
        <SafeAreaProvider>
          <ThemeProvider>
            <ThemedApp />
          </ThemeProvider>
        </SafeAreaProvider>
      </KeyboardProvider>
    </GestureHandlerRootView>
  );
}
