const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

export const getAuthToken = () => authToken;

export const wsUrl = (): string =>
  `${API_URL!.replace(/^http/, "ws")}/api/ws?token=${authToken}`;

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      // keep default detail
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};

export interface User {
  id: string;
  email?: string;
  name: string;
  bio?: string | null;
  country?: string | null;
  avatar_url?: string | null;
  native_language?: string | null;
  learning_language?: string | null;
  proficiency?: string | null;
  proficiencies?: Record<string, string>;
  teach_languages?: string[];
  learning_languages?: string[];
  age?: number | null;
  interests?: string[];
  gender?: "male" | "female" | null;
  username?: string | null;
  username_changed_at?: string | null;
  is_vip?: boolean;
  is_admin?: boolean;
  vip_tier?: "weekly" | "monthly" | "lifetime" | null;
  active_badge?: { id: string; emoji: string; expires_at?: string | null } | null;
  active_frame?: { id: string; color: string; colors?: string[] | null; animated?: boolean; expires_at?: string | null } | null;
  coins?: number;
  privacy?: Record<string, boolean>;
  hidden_moment_users?: string[];
  blocked_users?: string[];
  in_voice_room?: { room_id: string; name?: string } | null;
  is_online?: boolean;
  followers_count?: number;
  following_count?: number;
  is_following?: boolean;
  follows_me?: boolean;
  streak_count?: number;
  profile_views?: number;
  created_at?: string | null;
  places_to_go?: string | null;
  mbti?: string | null;
  blood_type?: string | null;
  hometown?: string | null;
  occupation?: string | null;
  school?: string | null;
  birthday?: string | null;
  cover_url?: string | null;
}

export interface Visitor extends User {
  visited_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  text: string;
  type?: "text" | "voice" | "image";
  audio_id?: string | null;
  image_id?: string | null;
  duration_ms?: number | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  partner: User | null;
  last_message: { text: string; sender_id: string; created_at: string } | null;
  unread: number;
  muted?: boolean;
  updated_at: string;
}

export interface Moment {
  id: string;
  author: User | null;
  text: string;
  image_url?: string | null;
  like_count: number;
  liked_by_me: boolean;
  likers?: User[];
  comment_count: number;
  created_at: string;
  comments?: MomentComment[];
}

export interface MarketItem {
  id: string;
  type: "vip" | "badge" | "frame";
  name: string;
  emoji: string;
  price: number;
  duration_days: number | null;
  color?: string;
  colors?: string[];
  animated?: boolean;
  desc: string;
  active: boolean;
}

export interface AppNotification {
  id: string;
  type: "like" | "comment" | "reply";
  moment_id: string | null;
  text: string | null;
  read: boolean;
  created_at: string;
  actor: User | null;
}

export interface MomentComment {
  id: string;
  author: User | null;
  text: string;
  reply_to?: string | null;
  reply_to_author?: string | null;
  created_at: string;
}

export interface RoomMember extends User {
  role: "host" | "speaker" | "listener";
  mic_on: boolean;
  hand_raised: boolean;
}

export interface TopGifter extends User {
  coins: number;
}

export interface Room {
  id: string;
  title: string;
  language: string;
  languages?: string[];
  host: User | null;
  host_level?: number;
  is_live?: boolean;
  members?: RoomMember[];
  member_count: number;
  chat_muted?: boolean;
  top_gifters?: TopGifter[];
  created_at: string;
}

export interface RoomMessage {
  id: string;
  room_id: string;
  sender: User | null;
  text: string;
  type?: "text" | "system" | "gift";
  gift?: { emoji: string; name: string; to: string } | null;
  created_at: string;
}

export interface RoomGift {
  id: string;
  emoji: string;
  name: string;
  price: number;
}

export const audioUrl = (audioId: string): string =>
  `${API_URL}/api/audio/${audioId}`;

export const mediaUrl = (mediaId: string): string =>
  `${API_URL}/api/media/${mediaId}`;

/** Resolve relative asset paths (e.g. "/api/media/<id>" avatars) to absolute URLs. */
export const assetUrl = (u?: string | null): string | null =>
  !u ? null : u.startsWith("http") || u.startsWith("data:") ? u : `${API_URL}${u}`;
