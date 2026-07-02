import { Platform } from "react-native";

/** Free STUN-only config (no paid TURN). */
export const RTC_CONFIG = {
  iceServers: [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
  ],
};

// Native WebRTC (react-native-webrtc) — available in production/dev builds,
// gracefully absent in Expo Go.
let NativeWebRTC: any = null;
if (Platform.OS !== "web") {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    NativeWebRTC = require("react-native-webrtc");
  } catch {
    NativeWebRTC = null;
  }
}

export interface RTCEnv {
  PC: any;
  mediaDevices: any;
  native: boolean;
}

export const getRTC = (): RTCEnv | null => {
  if (Platform.OS === "web") {
    if (
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices &&
      typeof (window as any).RTCPeerConnection === "function"
    ) {
      return {
        PC: (window as any).RTCPeerConnection,
        mediaDevices: navigator.mediaDevices,
        native: false,
      };
    }
    return null;
  }
  if (NativeWebRTC?.RTCPeerConnection && NativeWebRTC?.mediaDevices) {
    return {
      PC: NativeWebRTC.RTCPeerConnection,
      mediaDevices: NativeWebRTC.mediaDevices,
      native: true,
    };
  }
  return null;
};

export const webrtcAvailable = () => !!getRTC();
