# Feeds React Native - Screen and Component Blueprints

Load only the section you are implementing. For `llms.txt` manifest search, see [DOCS.md](DOCS.md). For setup, packages, and gotchas, see [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md).

Stream Feeds has **no pre-built UI components** - every screen is custom React Native built against the SDK's reactive contexts and hooks.

The blueprints use generic React Native primitives (`View`, `Text`, `FlatList`, `Pressable`, `TextInput`). Replace with the host app's themed components as needed.

---

## Request -> Blueprint section

| Request | Read section |
|---|---|
| root setup, providers, auth gate, login | App Provider and Auth Gate |
| brand new React Native or Expo app | Fresh App Scaffold |
| share `user` + `timeline` feed instances across screens | Own Feeds Context |
| timeline / home feed, activity list | Activity List Screen |
| activity row UI | Activity Component |
| compose / post an activity | Activity Composer |
| Explore / discover feed (newest posts across the app) | Explore Screen |
| For You feed (algorithmic, requires follows + popularity signal) | For You Feed (selector-based, see note) |
| follow / unfollow another user's feed | Follow Button |
| like / heart / unreact | Reactions |
| comments modal, activity-details navigation | Comments Modal |
| notification feed, unread badge, mark read | Notification Feed |
| theming, design tokens | Theming / Customization Note |
| sign-out cleanup | Sign-out |

If no row matches, read [DOCS.md](DOCS.md) and [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) first, then verify symbols in manifest-selected docs before coding.

---

## App Provider and Auth Gate

Use this when adding Stream Feeds to the app root. The pattern mirrors the [tutorial](https://getstream.io/activity-feeds/docs/react-native/) `app/_layout.tsx`. Replace the static credentials with values from the host app's auth flow.

```tsx
import React, { useState } from "react";
import { ActivityIndicator, Button, TextInput, View } from "react-native";
import {
  StreamFeeds,
  useCreateFeedsClient,
} from "@stream-io/feeds-react-native-sdk";
import { OwnFeedsContextProvider } from "@/contexts/own-feeds-context";

type Session = {
  apiKey: string;
  token: string;
  userId: string;
  userName: string;
};

const ConnectedFeeds = ({
  children,
  session,
}: {
  children: React.ReactNode;
  session: Session;
}) => {
  const client = useCreateFeedsClient({
    apiKey: session.apiKey,
    tokenOrProvider: session.token,
    userData: { id: session.userId, name: session.userName },
  });

  if (!client) {
    return (
      <View style={{ alignItems: "center", flex: 1, justifyContent: "center" }}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <StreamFeeds client={client}>
      <OwnFeedsContextProvider>{children}</OwnFeedsContextProvider>
    </StreamFeeds>
  );
};

export const StreamFeedsRoot = ({
  children,
  demoDefaults,
}: {
  children: React.ReactNode;
  demoDefaults?: Partial<Session>;
}) => {
  const [session, setSession] = useState<Session | null>(null);

  if (!session) {
    return <LoginScreen demoDefaults={demoDefaults} onSession={setSession} />;
  }

  return <ConnectedFeeds session={session}>{children}</ConnectedFeeds>;
};
```

Wiring:

- `useCreateFeedsClient` returns `undefined` while connecting; render a spinner / placeholder until the client resolves.
- Clearing `session` unmounts `ConnectedFeeds` and lets the hook disconnect the user.
- Mount `<StreamFeeds>` above any screen that uses Feeds hooks. Most apps mount it once at the root.
- `OwnFeedsContextProvider` (next section) creates the user + timeline feeds once so they can be shared across screens.
- For production, fetch tokens from the app backend; never expose the API secret to the client.
- Do not print user tokens in final summaries or logs.

---

## Fresh App Scaffold

Use this when the current directory is empty or the user asks for a brand-new React Native or Expo Feeds app. Scaffold the app, install the package + mandatory peer, wire the providers, and create the first feed screens.

Expo:

```bash
npx create-expo-app@latest MyFeedsApp
cd MyFeedsApp
npm view @stream-io/feeds-react-native-sdk version dist-tags --json
npx expo install @stream-io/feeds-react-native-sdk @react-native-community/netinfo
npx expo install react-native-safe-area-context
```

RN CLI:

```bash
npx @react-native-community/cli@latest init MyFeedsApp
cd MyFeedsApp
npm view @stream-io/feeds-react-native-sdk version dist-tags --json
npm install @stream-io/feeds-react-native-sdk @react-native-community/netinfo
npm install react-native-safe-area-context
npx pod-install
```

**Install navigation.** Expo apps from `create-expo-app` ship Expo Router under `app/` - use that. For RN CLI without navigation, `npm install @react-navigation/native @react-navigation/native-stack react-native-screens` then `npx pod-install`. Expo Router SDK 56+ is incompatible with `@react-navigation/*` packages - do not install them there.

After scaffolding, continue in order: App Provider and Auth Gate, Own Feeds Context, Activity List Screen, Activity Composer. Start Expo with `npx expo start`.

---

## Own Feeds Context

Use this to share the current user's `user` feed and `timeline` feed across screens without recreating them. Also wires the self-follow on first run.

```tsx
import {
  Feed,
  useClientConnectedUser,
  useFeedsClient,
} from "@stream-io/feeds-react-native-sdk";
import {
  createContext,
  PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from "react";

type OwnFeedsContextValue = {
  ownFeed: Feed | undefined;
  ownTimeline: Feed | undefined;
};

const OwnFeedsContext = createContext<OwnFeedsContextValue>({
  ownFeed: undefined,
  ownTimeline: undefined,
});

export const OwnFeedsContextProvider = ({ children }: PropsWithChildren) => {
  const [ownFeed, setOwnFeed] = useState<Feed>();
  const [ownTimeline, setOwnTimeline] = useState<Feed>();
  const client = useFeedsClient();
  const connectedUser = useClientConnectedUser();

  useEffect(() => {
    if (!connectedUser || !client) return;

    const feed = client.feed("user", connectedUser.id);
    const timeline = client.feed("timeline", connectedUser.id);
    setOwnFeed(feed);
    setOwnTimeline(timeline);

    Promise.all([
      feed.getOrCreate({ watch: true }),
      timeline.getOrCreate({ watch: true }),
    ]).then(() => {
      // Self-follow: own posts only appear on own timeline once timeline follows user.
      const alreadyFollows = feed.currentState.own_follows?.find(
        (follow) => follow.source_feed.feed === timeline.feed,
      );
      if (!alreadyFollows) timeline.follow(feed.feed);
    });

    return () => {
      setOwnFeed(undefined);
      setOwnTimeline(undefined);
    };
  }, [client, connectedUser]);

  return (
    <OwnFeedsContext.Provider value={{ ownFeed, ownTimeline }}>
      {children}
    </OwnFeedsContext.Provider>
  );
};

export const useOwnFeedsContext = () => useContext(OwnFeedsContext);
```

Wiring:

- The context is `undefined` until both feeds have been created and loaded.
- Self-follow is idempotent: the `own_follows` check skips it after the first run.
- Most apps mount this exactly once, above the navigator.
- Do not pass `Feed` objects through navigation params. Instead, read them from this context on the destination screen.

---

## Activity List Screen

Renders the timeline (or any feed) with pagination. Wraps a `FlatList` in `<StreamFeed>` so descendant hooks can resolve the feed from context.

```tsx
import React, { useCallback } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { ActivityResponse } from "@stream-io/feeds-react-native-sdk";
import {
  StreamFeed,
  useFeedActivities,
} from "@stream-io/feeds-react-native-sdk";
import { useOwnFeedsContext } from "@/contexts/own-feeds-context";
import { Activity } from "@/components/activity/Activity";

const keyExtractor = (item: ActivityResponse) => item.id;
const renderItem = ({ item }: { item: ActivityResponse }) => (
  <Activity activity={item} />
);
const Separator = () => <View style={styles.separator} />;

export const ActivityList = () => {
  const { activities, is_loading, has_next_page, loadNextPage } =
    useFeedActivities() ?? {};

  const ListFooterComponent = useCallback(
    () =>
      is_loading && has_next_page && (activities?.length ?? 0) > 0 ? (
        <ActivityIndicator />
      ) : null,
    [is_loading, has_next_page, activities?.length],
  );

  if (is_loading && (!activities || activities.length === 0)) {
    return (
      <View style={styles.empty}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No posts yet</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={activities}
      keyExtractor={keyExtractor}
      renderItem={renderItem}
      ItemSeparatorComponent={Separator}
      ListFooterComponent={ListFooterComponent}
      onEndReachedThreshold={0.2}
      onEndReached={loadNextPage}
    />
  );
};

export const HomeScreen = () => {
  const { ownTimeline } = useOwnFeedsContext();
  if (!ownTimeline) return null;
  return (
    <StreamFeed feed={ownTimeline}>
      <ActivityList />
    </StreamFeed>
  );
};

const styles = StyleSheet.create({
  separator: { height: 12 },
  empty: { alignItems: "center", flex: 1, justifyContent: "center" },
  emptyText: { color: "#6B7280", fontSize: 14 },
});
```

Wiring:

- `useFeedActivities()` (no argument) resolves the feed from the nearest `<StreamFeed>` provider.
- `loadNextPage` is safe to call from `onEndReached`; the hook ignores calls when there is no next page.
- For high-volume timelines, swap `FlatList` for `@shopify/flash-list` and feed `data` + `renderItem` through the same hook.

---

## Activity Component

Renders a single activity row. SDK is headless, so this is plain React Native. Add slots for follow / reactions / comments by composing the components from those sections.

```tsx
import React from "react";
import { Pressable, StyleSheet, View, Text } from "react-native";
import { useRouter } from "expo-router";
import type { ActivityResponse } from "@stream-io/feeds-react-native-sdk";
import { useClientConnectedUser } from "@stream-io/feeds-react-native-sdk";
import { FollowButton } from "@/components/follows/FollowButton";
import { Reaction } from "@/components/activity/Reaction";

type ActivityProps = { activity: ActivityResponse };

export const Activity = ({ activity }: ActivityProps) => {
  const router = useRouter();
  const connectedUser = useClientConnectedUser();
  const name = activity.user?.name || activity.user?.id || "Unknown";
  const initial = name.charAt(0).toUpperCase();
  const createdAt =
    activity.created_at instanceof Date
      ? activity.created_at
      : new Date(activity.created_at);
  const isOwnActivity =
    activity.current_feed?.feed === `user:${connectedUser?.id}`;

  return (
    <View style={styles.card}>
      {!isOwnActivity && activity.current_feed ? (
        <View style={styles.actionsRow}>
          <FollowButton feed={activity.current_feed} />
        </View>
      ) : null}

      <View style={styles.row}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initial}</Text>
        </View>
        <View style={styles.content}>
          <View style={styles.headerRow}>
            <Text numberOfLines={1} style={styles.name}>
              {name}
            </Text>
            <Text numberOfLines={1} style={styles.timestamp}>
              {createdAt.toLocaleString()}
            </Text>
          </View>
          {activity.text ? <Text style={styles.text}>{activity.text}</Text> : null}
        </View>
      </View>

      <View style={styles.bottomRow}>
        <Reaction activity={activity} />
        <Pressable
          style={({ pressed }) => [
            styles.commentButton,
            pressed && styles.pressed,
          ]}
          onPress={() =>
            router.push({
              pathname: "/comments-modal",
              params: { activityId: activity.id },
            })
          }
        >
          <Text style={styles.commentLabel}>Comments</Text>
          <Text>{activity.comment_count ?? 0}</Text>
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderColor: "#E5E7EB",
    borderRadius: 12,
    borderWidth: 1,
    padding: 12,
    width: "100%",
  },
  actionsRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "flex-end",
    marginBottom: 4,
  },
  row: { alignItems: "flex-start", flexDirection: "row" },
  avatar: {
    alignItems: "center",
    backgroundColor: "#6366F1",
    borderRadius: 20,
    height: 40,
    justifyContent: "center",
    marginRight: 12,
    width: 40,
  },
  avatarText: { color: "#FFFFFF", fontSize: 18, fontWeight: "600" },
  content: { flex: 1 },
  headerRow: {
    alignItems: "center",
    flexDirection: "row",
    marginBottom: 4,
  },
  name: { fontSize: 14, fontWeight: "600", marginRight: 8, maxWidth: "50%" },
  timestamp: { color: "#6B7280", flexShrink: 1, fontSize: 12 },
  text: { color: "#111827", fontSize: 14 },
  bottomRow: { flexDirection: "row", marginTop: 8 },
  commentButton: {
    alignItems: "center",
    flexDirection: "row",
    marginLeft: 12,
  },
  commentLabel: { fontSize: 14, marginRight: 4 },
  pressed: { opacity: 0.7 },
});
```

Wiring:

- Read `activity.current_feed` to know which feed the activity belongs to. In Reddit-style apps this is independent of `activity.user`.
- `useClientConnectedUser` gates the follow button so it does not appear on the user's own posts.
- Pass `activityId` (string) to the comments modal route, never the activity object.
- For images / videos / files, render `activity.attachments` (out of scope for this skill, but the field is on `ActivityResponse`).

---

## Activity Composer

Posts a text activity to the current user's `user` feed. Read the feed from `<StreamFeed>` context.

```tsx
import React, { useCallback, useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useFeedContext } from "@stream-io/feeds-react-native-sdk";

export const ActivityComposer = () => {
  const feed = useFeedContext();
  const [draft, setDraft] = useState("");
  const canPost = draft.trim().length > 0;

  const post = useCallback(async () => {
    if (!feed || !canPost) return;
    await feed.addActivity({ text: draft, type: "post" });
    setDraft("");
  }, [feed, canPost, draft]);

  return (
    <View style={styles.card}>
      <TextInput
        multiline
        onChangeText={setDraft}
        placeholder="What is happening?"
        placeholderTextColor="#9CA3AF"
        style={styles.input}
        textAlignVertical="top"
        value={draft}
      />
      <View style={styles.footerRow}>
        <Pressable
          disabled={!canPost}
          onPress={post}
          style={({ pressed }) => [
            styles.button,
            !canPost && styles.buttonDisabled,
            pressed && canPost && styles.buttonPressed,
          ]}
        >
          <Text style={styles.buttonText}>Post</Text>
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderColor: "#E5E7EB",
    borderRadius: 12,
    borderWidth: 1,
    margin: 12,
    padding: 12,
  },
  input: {
    borderColor: "#E5E7EB",
    borderRadius: 10,
    borderWidth: 1,
    color: "#111827",
    fontSize: 14,
    maxHeight: 160,
    minHeight: 80,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 10 : 8,
  },
  footerRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 8,
  },
  button: {
    backgroundColor: "#2563EB",
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  buttonDisabled: { backgroundColor: "#93C5FD" },
  buttonPressed: { opacity: 0.8 },
  buttonText: { color: "#FFFFFF", fontSize: 14, fontWeight: "600" },
});
```

Mount inside a screen wrapped with the user's own feed (so `feed.addActivity` posts to the right place):

```tsx
import { StreamFeed } from "@stream-io/feeds-react-native-sdk";
import { useOwnFeedsContext } from "@/contexts/own-feeds-context";

export const HomeScreen = () => {
  const { ownFeed, ownTimeline } = useOwnFeedsContext();
  if (!ownFeed || !ownTimeline) return null;
  return (
    <View style={{ flex: 1 }}>
      <StreamFeed feed={ownFeed}>
        <ActivityComposer />
      </StreamFeed>
      <StreamFeed feed={ownTimeline}>
        <ActivityList />
      </StreamFeed>
    </View>
  );
};
```

Wiring:

- The composer posts to `ownFeed` (user feed); the list reads `ownTimeline`. Self-follow makes own posts appear on the timeline automatically.
- For attachments, use `client.uploadImage(...)` and pass `attachments: [{ type: "image", image_url, custom: {} }]` to `addActivity`. The blueprint stays text-only for brevity.
- Disable the post button while `canPost === false` so the user cannot submit empty content.

---

## Explore Screen

The right tool for a general "Explore" / "Discover" tab that shows newest posts across the whole app is `client.queryActivities(...)`, **not** the `foryou` feed. Reasons:

- `foryou` is a selector-driven feed (its built-in selectors are following + popular + interest). In a fresh app with no follows, no popularity signal, and no interest tags, it returns an empty list **by design** - the API call succeeds but there is nothing matching the selectors yet.
- `queryActivities` is purpose-built for "exploratory search and filtering across all activities" (per the live docs). It searches across all visible feeds, respects activity visibility, and accepts simple filter + sort + pagination.

The trade-off: `queryActivities` returns a one-shot response, not a reactive feed. You manage state locally instead of using `<StreamFeed>` + `useFeedActivities`. Pull-to-refresh re-issues the query without `next`; pagination passes the prior response's `next` cursor.

```tsx
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { ActivityResponse } from "@stream-io/feeds-react-native-sdk";
import { useFeedsClient } from "@stream-io/feeds-react-native-sdk";
import { Activity } from "@/components/activity/Activity";

const PAGE_SIZE = 20;
const keyExtractor = (item: ActivityResponse) => item.id;
const renderItem = ({ item }: { item: ActivityResponse }) => (
  <Activity activity={item} />
);

export const ExploreScreen = () => {
  const client = useFeedsClient();
  const [activities, setActivities] = useState<ActivityResponse[]>([]);
  const [nextCursor, setNextCursor] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingNext, setIsLoadingNext] = useState(false);

  const load = useCallback(async () => {
    if (!client) return;
    setIsLoading(true);
    // No filter = every post across the app. The filter field is
    // `activity_type` (NOT `type` - that's a different field on activities and
    // a filter on `type` silently matches zero rows).
    const res = await client.queryActivities({
      sort: [{ field: "created_at", direction: -1 }],
      limit: PAGE_SIZE,
    });
    setActivities(res.activities ?? []);
    setNextCursor(res.next);
    setIsLoading(false);
  }, [client]);

  const loadNext = useCallback(async () => {
    if (!client || !nextCursor || isLoadingNext) return;
    setIsLoadingNext(true);
    const res = await client.queryActivities({
      sort: [{ field: "created_at", direction: -1 }],
      limit: PAGE_SIZE,
      next: nextCursor,
    });
    setActivities((prev) => [...prev, ...(res.activities ?? [])]);
    setNextCursor(res.next);
    setIsLoadingNext(false);
  }, [client, nextCursor, isLoadingNext]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading && activities.length === 0) {
    return (
      <View style={styles.empty}>
        <ActivityIndicator />
      </View>
    );
  }

  if (activities.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>No posts yet</Text>
      </View>
    );
  }

  return (
    <FlatList
      data={activities}
      keyExtractor={keyExtractor}
      renderItem={renderItem}
      onEndReachedThreshold={0.2}
      onEndReached={loadNext}
      ListFooterComponent={isLoadingNext ? <ActivityIndicator /> : null}
      refreshing={isLoading}
      onRefresh={load}
    />
  );
};

const styles = StyleSheet.create({
  empty: { alignItems: "center", flex: 1, justifyContent: "center" },
  emptyText: { color: "#6B7280", fontSize: 14 },
});
```

Wiring:

- Default sort `[{ field: "created_at", direction: -1 }]` gives newest-first - the right default for an Explore tab.
- Filter field is **`activity_type`** (not `type`). A `filter: { type: "post" }` clause silently matches zero rows because `type` here means something else internally. If you want only one activity type, use `filter: { activity_type: "post" }`. Most explore tabs want every post type, so leave `filter` off entirely.
- Reuse the same `Activity` component the timeline uses - it accepts any `ActivityResponse`.
- Pagination cursor is `res.next`. Pass it back in as `{ next }` on the follow-up call.
- For a tab nested in a navigator with a native iOS tab bar, add `contentContainerStyle={{ paddingBottom: insets.bottom + 12 }}` to the `FlatList` so the last item clears the tab bar.
- For real-time updates of new explore posts (out of scope for a basic showcase), you'd subscribe to client-level events. `queryActivities` itself is non-reactive.

### For You Feed (selector-based)

If you specifically want the algorithmic For You feed (only useful once your app has follow + popularity signal), the `foryou` group does still exist:

```tsx
const feed = useMemo(() => client?.feed("foryou", connectedUser?.id), [client, connectedUser?.id]);
useEffect(() => {
  if (feed) feed.getOrCreate({ limit: 10 });
}, [feed]);
// Render with <StreamFeed feed={feed}><ActivityList /></StreamFeed>
```

Note that `foryou`:

- Does not support real-time `watch: true` (passing it is a silent no-op).
- Returns empty in a fresh single-user app because there is no follow / popularity / interest signal yet. Seed follows and a few activities first (or use the Explore Screen pattern above).

---

## Follow Button

Toggles the timeline's follow on a target feed and refreshes the timeline so new activities appear / disappear.

```tsx
import React, { useCallback, useMemo } from "react";
import { Pressable, StyleSheet, Text } from "react-native";
import {
  FeedResponse,
  FollowResponse,
  useFeedsClient,
  useOwnFollows,
} from "@stream-io/feeds-react-native-sdk";
import { useOwnFeedsContext } from "@/contexts/own-feeds-context";

type FollowButtonProps = { feed?: FeedResponse };

export const FollowButton = ({ feed: activityFeed }: FollowButtonProps) => {
  const client = useFeedsClient();
  const { ownTimeline } = useOwnFeedsContext();

  const feed = useMemo(() => {
    if (!activityFeed || !client) return undefined;
    return client.feed(activityFeed.group_id, activityFeed.id);
  }, [client, activityFeed]);

  const { own_follows: ownFollows } = useOwnFollows(feed) ?? {};
  const ownFollow = useMemo(
    () =>
      ownFollows?.find(
        (follow: FollowResponse) => follow.source_feed.group_id === "timeline",
      ),
    [ownFollows],
  );
  const isFollowing = ownFollow?.status === "accepted";

  const toggle = useCallback(async () => {
    if (!feed || !ownTimeline) return;
    if (isFollowing) {
      await ownTimeline.unfollow(feed.feed);
    } else {
      await ownTimeline.follow(feed.feed);
    }
    // Refresh the timeline so activities are pulled in or removed.
    await ownTimeline.getOrCreate({ watch: true });
  }, [feed, ownTimeline, isFollowing]);

  return (
    <Pressable
      onPress={toggle}
      style={({ pressed }) => [
        styles.button,
        isFollowing ? styles.unfollow : styles.follow,
        pressed && styles.pressed,
      ]}
    >
      <Text style={styles.label}>{isFollowing ? "Unfollow" : "Follow"}</Text>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    alignItems: "center",
    borderRadius: 8,
    justifyContent: "center",
    minWidth: 80,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  follow: { backgroundColor: "#2563EB" },
  unfollow: { backgroundColor: "#DC2626" },
  pressed: { opacity: 0.8 },
  label: { color: "#FFFFFF", fontSize: 14, fontWeight: "600" },
});
```

Wiring:

- Pass `activity.current_feed` from the `ActivityResponse` so the button knows which feed to follow.
- Re-create a `Feed` instance from `client.feed(group_id, id)` so the SDK can subscribe to its `own_follows` state.
- Reload the timeline (`getOrCreate({ watch: true })`) after toggling so the activity list updates.
- For follow requests against private feeds (`visibility: "followers"`), `follow()` returns a pending status. Inspect `ownFollow?.status === "pending"` if you want to render that explicitly.

---

## Reactions

Adds / removes a single reaction type. State updates automatically from the reactive feed state - no local mirror required.

```tsx
import React, { useCallback } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { ActivityResponse } from "@stream-io/feeds-react-native-sdk";
import { useFeedsClient } from "@stream-io/feeds-react-native-sdk";

const REACTION_TYPE = "like";

type ReactionProps = { activity: ActivityResponse };

export const Reaction = ({ activity }: ReactionProps) => {
  const client = useFeedsClient();
  const hasReacted = (activity.own_reactions?.length ?? 0) > 0;
  const likeCount = activity.reaction_groups?.[REACTION_TYPE]?.count ?? 0;

  const toggle = useCallback(async () => {
    if (!client) return;
    if (hasReacted) {
      await client.deleteActivityReaction({
        activity_id: activity.id,
        type: REACTION_TYPE,
      });
    } else {
      await client.addActivityReaction({
        activity_id: activity.id,
        type: REACTION_TYPE,
      });
    }
  }, [client, activity.id, hasReacted]);

  return (
    <Pressable
      onPress={toggle}
      style={({ pressed }) => [
        styles.button,
        hasReacted && styles.active,
        pressed && styles.pressed,
      ]}
    >
      <View style={styles.row}>
        <Text style={styles.label}>{hasReacted ? "Liked" : "Like"}</Text>
        <Text style={styles.count}>{likeCount}</Text>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  button: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#E5E7EB",
    borderRadius: 50,
    borderWidth: 1,
    justifyContent: "center",
    paddingHorizontal: 12,
    paddingVertical: 6,
    width: 80,
  },
  active: { backgroundColor: "#2563EB20", borderColor: "#2563EB" },
  pressed: { opacity: 0.7 },
  row: { alignItems: "center", flexDirection: "row", gap: 4 },
  label: { fontSize: 12, fontWeight: "600", marginRight: 4 },
  count: { color: "#111827", fontSize: 14, fontWeight: "600" },
});
```

Wiring:

- `client.addActivityReaction` / `client.deleteActivityReaction` live on the client - not on the `Feed`.
- `activity.own_reactions` is updated reactively whenever the SDK pushes state - no local `useState` mirror needed.
- A single user can add multiple reactions to an activity. To enforce one reaction per user, pass `enforce_unique: true` and read the first / latest item from `own_reactions`.
- Comments can have reactions too via `client.addCommentReaction({ comment_id, type })`.

---

## Comments Modal

Loads comments for an activity that may not be present in the current feed (e.g. a "For You" tap, a deep link). Uses `client.activityWithStateUpdates` so comments live-update.

`app/comments-modal.tsx` (Expo Router):

```tsx
import React, { useEffect, useState } from "react";
import { Keyboard, Platform, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams } from "expo-router";
import {
  ActivityWithStateUpdates,
  useFeedsClient,
} from "@stream-io/feeds-react-native-sdk";
import { CommentList } from "@/components/comments/CommentList";
import { CommentComposer } from "@/components/comments/CommentComposer";

export default function CommentsModal() {
  const client = useFeedsClient();
  const insets = useSafeAreaInsets();
  const { activityId } = useLocalSearchParams<{ activityId: string }>();
  const [activity, setActivity] = useState<ActivityWithStateUpdates>();
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  useEffect(() => {
    if (!client || !activityId) return;
    const handle = client.activityWithStateUpdates(activityId);
    // The `comments` request shape is REQUIRED here. Without it, get() fetches
    // the activity but does NOT hydrate state.comments_by_entity_id, which is
    // what useActivityComments reads from - so the comment list would render
    // empty even when the activity has comments. See FEEDS-REACT-NATIVE.md
    // > Activity details for the full explanation.
    handle
      .get({ comments: { limit: 25, sort: "last", depth: 2 } })
      .then(() => setActivity(handle));
    return () => {
      handle.dispose();
    };
  }, [client, activityId]);

  // Keyboard avoidance via OS events + paddingBottom on the modal root.
  // KeyboardAvoidingView is unreliable inside native-stack `presentation: "modal"`
  // sheets - its math mixes parent-relative (frame.y from onLayout) with screen-
  // relative (keyboardScreenY from the event), which don't agree inside a modal
  // sheet, leaving keyboardVerticalOffset as a magic-number knob. The OS events
  // are absolute and work everywhere.
  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const showSub = Keyboard.addListener(showEvent, (e) =>
      setKeyboardHeight(e.endCoordinates.height),
    );
    const hideSub = Keyboard.addListener(hideEvent, () => setKeyboardHeight(0));
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  if (!activity) return null;

  // iOS: endCoordinates.height already extends to the screen bottom (covers the
  // home-indicator area). Adding insets.bottom on top would double-count.
  // Android edge-to-edge: endCoordinates.height is just the IME, so the nav-bar
  // inset has to be added back. +16 is a visual breather on both.
  const bottomPadding =
    keyboardHeight > 0
      ? keyboardHeight + (Platform.OS === "android" ? insets.bottom + 16 : 16)
      : insets.bottom;

  return (
    <View
      style={[
        styles.container,
        { paddingTop: insets.top, paddingBottom: bottomPadding },
      ]}
    >
      <CommentList activity={activity} />
      <CommentComposer activity={activity} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: "white", flex: 1 },
});
```

`CommentList`:

```tsx
import React, { useCallback } from "react";
import { ActivityIndicator, FlatList, StyleSheet, View } from "react-native";
import {
  ActivityWithStateUpdates,
  CommentResponse,
  useActivityComments,
} from "@stream-io/feeds-react-native-sdk";
import { Comment } from "@/components/comments/Comment";

type CommentListProps = { activity: ActivityWithStateUpdates };

const renderItem = ({ item }: { item: CommentResponse }) => (
  <Comment comment={item} />
);
const keyExtractor = (item: CommentResponse) => item.id;
const maintainVisibleContentPosition = {
  autoscrollToTopThreshold: 10,
  minIndexForVisible: 0,
};

export const CommentList = ({ activity }: CommentListProps) => {
  const {
    comments = [],
    loadNextPage,
    has_next_page,
    is_loading_next_page,
  } = useActivityComments({ activity });

  const onEndReached = useCallback(() => {
    if (!loadNextPage || !has_next_page || is_loading_next_page) return;
    loadNextPage({ limit: 10, sort: "last" });
  }, [loadNextPage, has_next_page, is_loading_next_page]);

  return (
    <View style={styles.container}>
      <FlatList
        data={comments}
        keyExtractor={keyExtractor}
        renderItem={renderItem}
        maintainVisibleContentPosition={maintainVisibleContentPosition}
        onEndReachedThreshold={0.2}
        onEndReached={onEndReached}
        ListFooterComponent={
          is_loading_next_page && has_next_page ? <ActivityIndicator /> : null
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, marginTop: 8, width: "100%" },
});
```

`Comment`:

```tsx
import React from "react";
import { StyleSheet, Text, View } from "react-native";
import type { CommentResponse } from "@stream-io/feeds-react-native-sdk";

type CommentItemProps = { comment: CommentResponse };

export const Comment = ({ comment }: CommentItemProps) => {
  const name = comment.user?.name || comment.user?.id || "Unknown";
  const initial = name.charAt(0).toUpperCase();
  const createdAt = comment.created_at
    ? new Date(comment.created_at).toLocaleString()
    : "";

  return (
    <View style={styles.row}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{initial}</Text>
      </View>
      <View style={styles.bubble}>
        <View style={styles.header}>
          <Text numberOfLines={1} style={styles.author}>
            {name}
          </Text>
          {createdAt ? <Text style={styles.timestamp}> {createdAt}</Text> : null}
        </View>
        <Text style={styles.text}>{comment.text}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  row: {
    alignItems: "center",
    flexDirection: "row",
    paddingHorizontal: 12,
    paddingVertical: 6,
    width: "100%",
  },
  avatar: {
    alignItems: "center",
    backgroundColor: "#6366F1",
    borderRadius: 16,
    height: 32,
    justifyContent: "center",
    marginRight: 8,
    width: 32,
  },
  avatarText: { color: "#FFFFFF", fontSize: 16, fontWeight: "600" },
  bubble: {
    backgroundColor: "#F3F4F6",
    borderRadius: 12,
    flex: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  header: { alignItems: "baseline", flexDirection: "row", marginBottom: 2 },
  author: { color: "#111827", fontSize: 14, fontWeight: "600", marginRight: 4 },
  timestamp: { color: "#6B7280", fontSize: 11 },
  text: { color: "#111827", fontSize: 14, lineHeight: 18 },
});
```

`CommentComposer`:

Note: `CommentComposer` is a leaf component. The parent modal screen is responsible for keyboard avoidance (see `app/comments-modal.tsx` above) - do NOT wrap this component in a `KeyboardAvoidingView`. KAV inside a `presentation: "modal"` sheet mixes parent-relative and screen-relative coordinates and produces drift that varies by device, header style, and sheet style; the modal-root `Keyboard.addListener` + `paddingBottom` pattern is the cross-platform fix.

```tsx
import React, { useCallback, useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  ActivityWithStateUpdates,
  useFeedsClient,
} from "@stream-io/feeds-react-native-sdk";

type CommentComposerProps = { activity: ActivityWithStateUpdates };

export const CommentComposer = ({ activity }: CommentComposerProps) => {
  const client = useFeedsClient();
  const [draft, setDraft] = useState("");
  const canReply = draft.trim().length > 0;

  const submit = useCallback(async () => {
    if (!client || !canReply) return;
    await client.addComment({
      object_id: activity.id,
      object_type: "activity",
      comment: draft,
    });
    setDraft("");
  }, [client, activity.id, draft, canReply]);

  return (
    <View style={styles.container}>
      <TextInput
        onChangeText={setDraft}
        onSubmitEditing={submit}
        placeholder="Post your reply"
        placeholderTextColor="#9CA3AF"
        returnKeyType="send"
        style={styles.input}
        value={draft}
      />
      <Pressable
        disabled={!canReply}
        onPress={submit}
        style={({ pressed }) => [
          styles.button,
          !canReply && styles.buttonDisabled,
          pressed && canReply && styles.buttonPressed,
        ]}
      >
        <Text style={styles.buttonText}>Reply</Text>
      </Pressable>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    marginTop: 8,
    paddingHorizontal: 12,
    width: "100%",
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderColor: "#E5E7EB",
    borderRadius: 999,
    borderWidth: 1,
    color: "#111827",
    flex: 1,
    fontSize: 14,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 10 : 8,
  },
  button: {
    alignItems: "center",
    backgroundColor: "#2563EB",
    borderRadius: 999,
    justifyContent: "center",
    minWidth: 70,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  buttonDisabled: { backgroundColor: "#93C5FD" },
  buttonPressed: { opacity: 0.8 },
  buttonText: { color: "#FFFFFF", fontSize: 14, fontWeight: "600" },
});
```

Wiring:

- Pass only `activityId` (string) through navigation params, never the `ActivityResponse`.
- `client.activityWithStateUpdates(id)` returns a handle that subscribes to live state. Call `.get({ comments: { limit, sort, depth } })` to load the activity **and** hydrate the comments state slice, then `.dispose()` on unmount.
- **Do not call `handle.get()` without the `comments` request.** Bare `get()` fetches the activity but skips comment hydration entirely - `state.comments_by_entity_id[activityId]` stays undefined, and `useActivityComments` (which reads from that slice) renders an empty list even when comments exist. The `comments` field on the activity response itself is NOT what the hook reads.
- `useActivityComments({ activity })` resolves comments from the handle. Inside `<StreamActivityWithStateUpdates>` you can omit the `activity` argument.
- For nested replies, pass `parent_id` to `addComment` and `parentComment` to `useActivityComments`. The `depth` option on `get({ comments })` controls how many reply levels are pre-hydrated.
- Use `View` + `useSafeAreaInsets()` + explicit padding rather than `<SafeAreaView>` from `react-native-safe-area-context`. On RN 0.85 + Expo 56 + new architecture, the package's `SafeAreaView` no-ops at the native boundary, so the inset never lands (the reply composer ends up behind the home indicator). The hook works because it goes through a different code path.
- **Do not use `KeyboardAvoidingView` inside a native-stack `presentation: "modal"` sheet.** KAV's internal math computes `frame.y + frame.height - keyboardScreenY`, mixing parent-relative coordinates (from `onLayout`) with screen-relative coordinates (from the keyboard event). Inside a modal sheet those two spaces don't agree, so `keyboardVerticalOffset` becomes a magic-number knob that varies by device, header style, and sheet style. On Android with `behavior={undefined}` KAV does nothing at all. Handle keyboard avoidance at the modal root with `Keyboard.addListener` and adjust `paddingBottom` on the root `View` (see snippet). OS keyboard events are absolute and work the same in modals and non-modals.
- iOS / Android padding math is asymmetric: iOS `endCoordinates.height` already covers the home-indicator area, so adding `insets.bottom` would double-count - use `keyboardHeight + 16`. Android (edge-to-edge) `endCoordinates.height` is just the IME, so add `insets.bottom + 16` back for the nav bar. When the keyboard is hidden, fall back to `insets.bottom` so the composer sits above the home indicator / nav bar.
- Do not reach for `useHeaderHeight` from `@react-navigation/elements` to compute the offset - it only solves half the problem (header height is not the modal sheet's screen-top offset), and every helper from that package is deprecated and scheduled for removal in expo-router 56.
- Register the modal route in your navigator: with Expo Router, `presentation: "modal"` on `<Stack.Screen name="comments-modal" />` in the parent layout.

---

## Notification Feed

Aggregated notifications (likes, follows, comments) live on the `notification` feed group. Read aggregated activities with `useAggregatedActivities` and unread / unseen counts with `useNotificationStatus`.

```tsx
import React, { useEffect, useMemo } from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import {
  AggregatedActivityResponse,
  useAggregatedActivities,
  useClientConnectedUser,
  useFeedsClient,
  useNotificationStatus,
} from "@stream-io/feeds-react-native-sdk";

const keyExtractor = (item: AggregatedActivityResponse) => item.group;

export const NotificationFeedScreen = () => {
  const client = useFeedsClient();
  const connectedUser = useClientConnectedUser();

  const notificationFeed = useMemo(() => {
    if (!client || !connectedUser?.id) return undefined;
    return client.feed("notification", connectedUser.id);
  }, [client, connectedUser?.id]);

  useEffect(() => {
    if (notificationFeed) notificationFeed.getOrCreate({ watch: true });
  }, [notificationFeed]);

  const { aggregated_activities = [], loadNextPage, has_next_page } =
    useAggregatedActivities(notificationFeed) ?? {};
  const { unread = 0 } = useNotificationStatus(notificationFeed) ?? {};

  const markAllRead = async () => {
    if (!notificationFeed) return;
    await notificationFeed.markActivity({ mark_all_read: true });
  };

  const renderItem = ({ item }: { item: AggregatedActivityResponse }) => (
    <View style={styles.row}>
      <Text style={styles.activityText}>
        {item.activities[0]?.user?.name ?? item.activities[0]?.user?.id ?? "Someone"}{" "}
        {item.verb}
      </Text>
    </View>
  );

  if (!notificationFeed) return null;

  return (
    <View style={styles.container}>
      {unread > 0 ? (
        <Pressable onPress={markAllRead} style={styles.markAll}>
          <Text style={styles.markAllText}>Mark all as read ({unread})</Text>
        </Pressable>
      ) : null}
      <FlatList
        data={aggregated_activities}
        keyExtractor={keyExtractor}
        renderItem={renderItem}
        onEndReachedThreshold={0.2}
        onEndReached={has_next_page ? loadNextPage : undefined}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  markAll: {
    alignItems: "center",
    backgroundColor: "#2563EB20",
    paddingVertical: 8,
  },
  markAllText: { color: "#2563EB", fontWeight: "600" },
  row: { borderBottomColor: "#E5E7EB", borderBottomWidth: 1, padding: 12 },
  activityText: { color: "#111827", fontSize: 14 },
});
```

Wiring:

- The notification feed uses `aggregated_activities` (grouped), not `activities`.
- `useNotificationStatus` exposes `unread`, `unseen`, `last_read_at`, `last_seen_at`, `read_activities`, `seen_activities`.
- Mark all read / seen with `mark_all_read: true` / `mark_all_seen: true`. To mark a specific aggregation group, pass `mark_read: [groupId]` or `mark_seen: [groupId]`. JS uses snake_case here.
- For a badge on a header icon, read `unread` from `useNotificationStatus` and render the count.

---

## Theming / Customization Note

The Feeds RN SDK is headless. There is no `WithComponents` slot system (Chat) or theme variant object (Video). Customization is the same as customizing any React Native UI:

- Edit the components you wrote (Activity, ActivityComposer, Reaction, ...) directly.
- Extract design tokens (`colors`, `spacing`) into your existing theme system.
- Wrap shared layout in your own components.

The SDK only owns the state layer. No styling decisions are exposed by the package.

---

## Sign-out

Cleanly disconnect the user before connecting another. Clearing the session (the state that gates `<StreamFeeds client={...}>`) lets `useCreateFeedsClient` cleanup run automatically. For explicit disconnects:

```tsx
import React, { useCallback } from "react";
import { Button } from "react-native";
import { useFeedsClient } from "@stream-io/feeds-react-native-sdk";

export const SignOutButton = ({ onSignedOut }: { onSignedOut: () => void }) => {
  const client = useFeedsClient();

  const signOut = useCallback(async () => {
    if (client) await client.disconnectUser();
    onSignedOut();
  }, [client, onSignedOut]);

  return <Button onPress={signOut} title="Sign out" />;
};
```

Wiring:

- `client.disconnectUser()` releases the WebSocket and clears the connected user.
- Call `activity.dispose()` (where applicable) on any open `activityWithStateUpdates` handles before signing out, or rely on screen unmount to dispose them.
- Do not print user tokens in final summaries or logs.
