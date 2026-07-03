import { Ionicons } from "@expo/vector-icons";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/src/context/AuthContext";
import { api } from "@/src/utils/api";

const BRAND = "#0EA5E9";
const DANGER = "#EF4444";
const OK = "#22C55E";
const GOLD = "#F59E0B";

const confirmAction = (message: string, onConfirm: () => void) => {
  if (Platform.OS === "web") {
    if (window.confirm(message)) onConfirm();
  } else {
    Alert.alert("Confirm", message, [
      { text: "Cancel", style: "cancel" },
      { text: "OK", style: "destructive", onPress: onConfirm },
    ]);
  }
};

interface AdminStats {
  total_users: number;
  vip_users: number;
  banned_users: number;
  new_users_today: number;
  online_now: number;
  total_moments: number;
  total_messages: number;
  total_conversations: number;
  live_rooms: number;
  coins_in_circulation: number;
}

interface AdminUserRow {
  id: string;
  name: string;
  email: string;
  coins: number;
  is_vip: boolean;
  vip_tier?: string | null;
  is_admin: boolean;
  banned: boolean;
  restricted: boolean;
  is_online: boolean;
  country?: string;
  created_at?: string;
}

interface AdminMarketItem {
  id: string;
  name: string;
  emoji: string;
  type: string;
  price: number;
  default_price: number;
  disabled: boolean;
}

interface AdminMoment {
  id: string;
  text?: string;
  author_name: string;
  author_email?: string;
  like_count: number;
  comment_count: number;
  has_image: boolean;
  created_at?: string;
}

const TABS = ["Overview", "Users", "Market", "Moments", "Settings"] as const;
type Tab = (typeof TABS)[number];

export default function AdminPanel() {
  const { user, loading, login, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("Overview");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const doLogin = async () => {
    setAuthBusy(true);
    setAuthError(null);
    try {
      await login(email.trim(), password);
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setAuthBusy(false);
    }
  };

  if (loading) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={BRAND} />
      </View>
    );
  }

  if (!user) {
    return (
      <SafeAreaView style={s.container} testID="admin-login-screen">
        <View style={s.loginCard}>
          <View style={s.loginIcon}>
            <Ionicons name="shield-checkmark" size={34} color={BRAND} />
          </View>
          <Text style={s.loginTitle}>Admin Console</Text>
          <Text style={s.loginSub}>Restricted area — authorized staff only</Text>
          <TextInput
            testID="admin-email-input"
            style={s.input}
            placeholder="Admin email"
            placeholderTextColor="#64748B"
            autoCapitalize="none"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            testID="admin-password-input"
            style={s.input}
            placeholder="Password"
            placeholderTextColor="#64748B"
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />
          {authError ? <Text style={s.error}>{authError}</Text> : null}
          <Pressable testID="admin-login-btn" style={s.primaryBtn} onPress={doLogin} disabled={authBusy}>
            {authBusy ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={s.primaryBtnText}>Sign in</Text>
            )}
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (!user.is_admin) {
    return (
      <SafeAreaView style={s.container} testID="admin-denied-screen">
        <View style={s.loginCard}>
          <Ionicons name="lock-closed" size={40} color={DANGER} />
          <Text style={s.loginTitle}>Access denied</Text>
          <Text style={s.loginSub}>This account does not have admin privileges.</Text>
          <Pressable style={[s.primaryBtn, { backgroundColor: DANGER }]} onPress={logout}>
            <Text style={s.primaryBtnText}>Log out</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container} edges={["top", "bottom"]} testID="admin-dashboard">
      <View style={s.topBar}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Ionicons name="shield-checkmark" size={22} color={BRAND} />
          <Text style={s.topTitle}>Admin Console</Text>
        </View>
        <Pressable testID="admin-logout-btn" onPress={logout} style={s.logoutBtn}>
          <Ionicons name="log-out-outline" size={18} color={DANGER} />
          <Text style={{ color: DANGER, fontSize: 13, fontWeight: "600" }}>Logout</Text>
        </Pressable>
      </View>
      <View style={s.tabBar}>
        {TABS.map((t) => (
          <Pressable
            key={t}
            testID={`admin-tab-${t.toLowerCase()}`}
            style={[s.tabBtn, tab === t && s.tabBtnActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[s.tabText, tab === t && s.tabTextActive]}>{t}</Text>
          </Pressable>
        ))}
      </View>
      {tab === "Overview" && <Overview />}
      {tab === "Users" && <Users />}
      {tab === "Market" && <Market />}
      {tab === "Moments" && <Moments />}
      {tab === "Settings" && <Settings />}
    </SafeAreaView>
  );
}

function Overview() {
  const [stats, setStats] = useState<AdminStats | null>(null);

  useEffect(() => {
    api.get<AdminStats>("/admin/stats").then(setStats).catch(() => {});
  }, []);

  if (!stats) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={BRAND} />
      </View>
    );
  }

  const cards: [string, number, string][] = [
    ["Total users", stats.total_users, "people"],
    ["Online now", stats.online_now, "radio-button-on"],
    ["New today", stats.new_users_today, "person-add"],
    ["VIP users", stats.vip_users, "diamond"],
    ["Banned", stats.banned_users, "ban"],
    ["Moments", stats.total_moments, "images"],
    ["Messages", stats.total_messages, "chatbubbles"],
    ["Conversations", stats.total_conversations, "mail"],
    ["Live rooms", stats.live_rooms, "mic"],
    ["Coins in circulation", stats.coins_in_circulation, "logo-bitcoin"],
  ];

  return (
    <ScrollView contentContainerStyle={s.grid} testID="admin-overview">
      {cards.map(([label, value, icon]) => (
        <View key={label} style={s.statCard}>
          <Ionicons name={icon as never} size={20} color={BRAND} />
          <Text style={s.statValue}>{value}</Text>
          <Text style={s.statLabel}>{label}</Text>
        </View>
      ))}
    </ScrollView>
  );
}

function Users() {
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [coinEdit, setCoinEdit] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      const qs = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
      setRows(await api.get<AdminUserRow[]>(`/admin/users${qs}`));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(load, search ? 350 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  const patchRow = (id: string, patch: Partial<AdminUserRow>) =>
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const toggleBan = async (u: AdminUserRow) => {
    const res = await api.post<{ banned: boolean }>(`/admin/users/${u.id}/ban`);
    patchRow(u.id, { banned: res.banned });
  };
  const toggleRestrict = async (u: AdminUserRow) => {
    const res = await api.post<{ restricted: boolean }>(`/admin/users/${u.id}/restrict`);
    patchRow(u.id, { restricted: res.restricted });
  };
  const toggleVip = async (u: AdminUserRow) => {
    const res = await api.put<{ is_vip: boolean; vip_tier: string | null }>(
      `/admin/users/${u.id}/vip`,
      { is_vip: !u.is_vip, tier: "lifetime" },
    );
    patchRow(u.id, { is_vip: res.is_vip, vip_tier: res.vip_tier });
  };
  const saveCoins = async (u: AdminUserRow) => {
    const val = parseInt(coinEdit[u.id] ?? "", 10);
    if (isNaN(val) || val < 0) return;
    await api.put(`/admin/users/${u.id}/coins`, { coins: val });
    patchRow(u.id, { coins: val });
    setCoinEdit((prev) => ({ ...prev, [u.id]: "" }));
  };
  const removeUser = (u: AdminUserRow) =>
    confirmAction(`Delete ${u.name} (${u.email}) permanently?`, async () => {
      await api.delete(`/admin/users/${u.id}`);
      setRows((prev) => prev.filter((r) => r.id !== u.id));
    });

  return (
    <View style={{ flex: 1 }} testID="admin-users">
      <View style={s.searchBox}>
        <Ionicons name="search" size={16} color="#64748B" />
        <TextInput
          testID="admin-user-search"
          style={s.searchInput}
          placeholder="Search by name or email..."
          placeholderTextColor="#64748B"
          value={search}
          onChangeText={setSearch}
        />
      </View>
      {loading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color={BRAND} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 12, gap: 10, paddingBottom: 40 }}>
          {rows.map((u) => (
            <View key={u.id} style={s.userCard} testID={`admin-user-${u.id}`}>
              <View style={s.userTop}>
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <Text style={s.userName}>{u.name}</Text>
                    {u.is_admin && <Chip label="ADMIN" color={BRAND} />}
                    {u.is_vip && <Chip label={`VIP ${u.vip_tier || ""}`} color={GOLD} />}
                    {u.banned && <Chip label="BANNED" color={DANGER} />}
                    {u.restricted && <Chip label="RESTRICTED" color="#F97316" />}
                    {u.is_online && <Chip label="ONLINE" color={OK} />}
                  </View>
                  <Text style={s.userMeta}>
                    {u.email} · {u.country || "—"} · 🪙 {u.coins}
                  </Text>
                </View>
              </View>
              {!u.is_admin && (
                <View style={s.userActions}>
                  <ActionBtn
                    testID={`admin-ban-${u.id}`}
                    label={u.banned ? "Unban" : "Ban"}
                    color={DANGER}
                    onPress={() => toggleBan(u)}
                  />
                  <ActionBtn
                    testID={`admin-restrict-${u.id}`}
                    label={u.restricted ? "Unrestrict" : "Restrict"}
                    color="#F97316"
                    onPress={() => toggleRestrict(u)}
                  />
                  <ActionBtn
                    testID={`admin-vip-${u.id}`}
                    label={u.is_vip ? "Revoke VIP" : "Grant VIP"}
                    color={GOLD}
                    onPress={() => toggleVip(u)}
                  />
                  <ActionBtn
                    testID={`admin-delete-${u.id}`}
                    label="Delete"
                    color="#7F1D1D"
                    onPress={() => removeUser(u)}
                  />
                  <View style={s.coinRow}>
                    <TextInput
                      testID={`admin-coins-input-${u.id}`}
                      style={s.coinInput}
                      placeholder={String(u.coins)}
                      placeholderTextColor="#64748B"
                      keyboardType="numeric"
                      value={coinEdit[u.id] ?? ""}
                      onChangeText={(v) => setCoinEdit((prev) => ({ ...prev, [u.id]: v }))}
                    />
                    <ActionBtn
                      testID={`admin-coins-save-${u.id}`}
                      label="Set coins"
                      color={BRAND}
                      onPress={() => saveCoins(u)}
                    />
                  </View>
                </View>
              )}
            </View>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

function Market() {
  const [items, setItems] = useState<AdminMarketItem[]>([]);
  const [priceEdit, setPriceEdit] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api.get<AdminMarketItem[]>("/admin/market").then(setItems).catch(() => {});
  }, []);

  useEffect(load, [load]);

  const save = async (item: AdminMarketItem) => {
    const val = parseInt(priceEdit[item.id] ?? "", 10);
    if (isNaN(val) || val < 0) return;
    await api.put(`/admin/market/${item.id}`, { price: val });
    setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, price: val } : i)));
    setPriceEdit((prev) => ({ ...prev, [item.id]: "" }));
  };

  const toggleDisabled = async (item: AdminMarketItem) => {
    await api.put(`/admin/market/${item.id}`, { disabled: !item.disabled });
    setItems((prev) =>
      prev.map((i) => (i.id === item.id ? { ...i, disabled: !item.disabled } : i)),
    );
  };

  return (
    <ScrollView contentContainerStyle={{ padding: 12, gap: 10, paddingBottom: 40 }} testID="admin-market">
      {items.map((item) => (
        <View key={item.id} style={s.userCard} testID={`admin-market-${item.id}`}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <Text style={{ fontSize: 22 }}>{item.emoji}</Text>
            <View style={{ flex: 1 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <Text style={s.userName}>{item.name}</Text>
                <Chip label={item.type.toUpperCase()} color="#8B5CF6" />
                {item.disabled && <Chip label="DISABLED" color={DANGER} />}
              </View>
              <Text style={s.userMeta}>
                Current: 🪙 {item.price} (default {item.default_price})
              </Text>
            </View>
          </View>
          <View style={s.userActions}>
            <View style={s.coinRow}>
              <TextInput
                testID={`admin-price-input-${item.id}`}
                style={s.coinInput}
                placeholder={String(item.price)}
                placeholderTextColor="#64748B"
                keyboardType="numeric"
                value={priceEdit[item.id] ?? ""}
                onChangeText={(v) => setPriceEdit((prev) => ({ ...prev, [item.id]: v }))}
              />
              <ActionBtn
                testID={`admin-price-save-${item.id}`}
                label="Set price"
                color={BRAND}
                onPress={() => save(item)}
              />
            </View>
            <ActionBtn
              testID={`admin-market-toggle-${item.id}`}
              label={item.disabled ? "Enable" : "Disable"}
              color={item.disabled ? OK : DANGER}
              onPress={() => toggleDisabled(item)}
            />
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

function Moments() {
  const [rows, setRows] = useState<AdminMoment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<AdminMoment[]>("/admin/moments")
      .then(setRows)
      .finally(() => setLoading(false));
  }, []);

  const remove = (m: AdminMoment) =>
    confirmAction("Delete this moment permanently?", async () => {
      await api.delete(`/admin/moments/${m.id}`);
      setRows((prev) => prev.filter((r) => r.id !== m.id));
    });

  if (loading) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={BRAND} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 12, gap: 10, paddingBottom: 40 }} testID="admin-moments">
      {rows.map((m) => (
        <View key={m.id} style={s.userCard} testID={`admin-moment-${m.id}`}>
          <Text style={s.userName}>{m.author_name}</Text>
          <Text style={s.userMeta}>{m.author_email}</Text>
          <Text style={{ color: "#CBD5E1", fontSize: 13, marginVertical: 6 }} numberOfLines={3}>
            {m.text || "(photo only)"}
          </Text>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Text style={s.userMeta}>
              ❤️ {m.like_count} · 💬 {m.comment_count} {m.has_image ? "· 📷" : ""}
            </Text>
            <View style={{ flex: 1 }} />
            <ActionBtn
              testID={`admin-moment-delete-${m.id}`}
              label="Delete"
              color={DANGER}
              onPress={() => remove(m)}
            />
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

function Settings() {
  const [cfg, setCfg] = useState<Record<string, string>>({});
  const [loaded, setLoaded] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get<Record<string, number | string>>("/admin/config").then((d) => {
      setCfg(Object.fromEntries(Object.entries(d).map(([k, v]) => [k, String(v)])));
      setLoaded(true);
    });
  }, []);

  const FIELDS: [string, string][] = [
    ["free_translations_per_day", "Free translations / day"],
    ["free_rooms_per_day", "Free room hosting / day"],
    ["free_new_chats_per_day", "Free new chats / day"],
    ["vip_new_chats_per_day", "VIP new chats / day"],
  ];

  const save = async () => {
    const body: Record<string, number> = {};
    for (const [key] of FIELDS) {
      const v = parseInt(cfg[key] ?? "", 10);
      if (!isNaN(v) && v >= 0) body[key] = v;
    }
    await api.put("/admin/config", body);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!loaded) {
    return (
      <View style={s.center}>
        <ActivityIndicator size="large" color={BRAND} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }} testID="admin-settings">
      <Text style={{ color: "#94A3B8", fontSize: 13 }}>
        App-wide limits — changes apply instantly to all users.
      </Text>
      {FIELDS.map(([key, label]) => (
        <View key={key} style={s.settingField}>
          <Text style={s.settingLabel}>{label}</Text>
          <TextInput
            testID={`admin-cfg-${key}`}
            style={s.coinInput}
            keyboardType="numeric"
            value={cfg[key] ?? ""}
            onChangeText={(v) => setCfg((prev) => ({ ...prev, [key]: v }))}
            placeholderTextColor="#64748B"
          />
        </View>
      ))}
      <Pressable testID="admin-cfg-save" style={s.primaryBtn} onPress={save}>
        <Text style={s.primaryBtnText}>{saved ? "Saved ✓" : "Save settings"}</Text>
      </Pressable>
    </ScrollView>
  );
}

const Chip: React.FC<{ label: string; color: string }> = ({ label, color }) => (
  <View style={[s.chip, { backgroundColor: `${color}22`, borderColor: color }]}>
    <Text style={{ color, fontSize: 9, fontWeight: "700" }}>{label}</Text>
  </View>
);

const ActionBtn: React.FC<{
  label: string;
  color: string;
  onPress: () => void;
  testID?: string;
}> = ({ label, color, onPress, testID }) => (
  <Pressable
    testID={testID}
    style={[s.actionBtn, { backgroundColor: color }]}
    onPress={onPress}
  >
    <Text style={s.actionBtnText}>{label}</Text>
  </Pressable>
);

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0F172A" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", minHeight: 200 },
  loginCard: {
    margin: 20,
    marginTop: 80,
    backgroundColor: "#1E293B",
    borderRadius: 16,
    padding: 24,
    gap: 12,
    alignItems: "center",
    maxWidth: 420,
    width: "92%",
    alignSelf: "center",
  },
  loginIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "rgba(14,165,233,0.14)",
    alignItems: "center",
    justifyContent: "center",
  },
  loginTitle: { color: "#F8FAFC", fontSize: 22, fontWeight: "700" },
  loginSub: { color: "#94A3B8", fontSize: 13, textAlign: "center" },
  input: {
    width: "100%",
    backgroundColor: "#0F172A",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#334155",
    color: "#F8FAFC",
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
  },
  error: { color: DANGER, fontSize: 13 },
  primaryBtn: {
    width: "100%",
    backgroundColor: BRAND,
    borderRadius: 10,
    paddingVertical: 13,
    alignItems: "center",
  },
  primaryBtnText: { color: "#FFF", fontSize: 15, fontWeight: "700" },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#1E293B",
  },
  topTitle: { color: "#F8FAFC", fontSize: 18, fontWeight: "700" },
  logoutBtn: { flexDirection: "row", alignItems: "center", gap: 5 },
  tabBar: {
    flexDirection: "row",
    paddingHorizontal: 10,
    gap: 6,
    paddingVertical: 8,
    flexWrap: "wrap",
  },
  tabBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#1E293B",
  },
  tabBtnActive: { backgroundColor: BRAND },
  tabText: { color: "#94A3B8", fontSize: 13, fontWeight: "600" },
  tabTextActive: { color: "#FFF" },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    padding: 12,
    paddingBottom: 40,
  },
  statCard: {
    backgroundColor: "#1E293B",
    borderRadius: 12,
    padding: 14,
    gap: 4,
    minWidth: 150,
    flexGrow: 1,
  },
  statValue: { color: "#F8FAFC", fontSize: 24, fontWeight: "800" },
  statLabel: { color: "#94A3B8", fontSize: 12 },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#1E293B",
    borderRadius: 10,
    marginHorizontal: 12,
    marginTop: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  searchInput: { flex: 1, color: "#F8FAFC", fontSize: 14, paddingVertical: 2 },
  userCard: { backgroundColor: "#1E293B", borderRadius: 12, padding: 14, gap: 8 },
  userTop: { flexDirection: "row", alignItems: "center" },
  userName: { color: "#F8FAFC", fontSize: 15, fontWeight: "700" },
  userMeta: { color: "#94A3B8", fontSize: 12, marginTop: 2 },
  userActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    alignItems: "center",
  },
  actionBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  actionBtnText: { color: "#FFF", fontSize: 12, fontWeight: "700" },
  chip: {
    borderRadius: 6,
    borderWidth: 1,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  coinRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  coinInput: {
    backgroundColor: "#0F172A",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 8,
    color: "#F8FAFC",
    paddingHorizontal: 10,
    paddingVertical: 7,
    fontSize: 13,
    minWidth: 90,
  },
  settingField: { gap: 6 },
  settingLabel: { color: "#CBD5E1", fontSize: 14, fontWeight: "600" },
});
