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
| attach a photo / image / file to a post | Activity Composer with Image |
| Explore / discover feed (newest posts across the app) | Explore Screen |
| For You feed (algorithmic, requires follows + popularity signal) | For You Feed (selector-based, see note) |
| follow / unfollow another user's feed | Follow Button |
| like / heart / unreact | Reactions |
| comments modal, activity-details navigation | Comments Modal |
| notification feed, unread badge, mark read | Notification Feed |
| register a device for OS push notifications | Push Device Registration |
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
  forYouFeed: Feed | undefined;
};

const OwnFeedsContext = createContext<OwnFeedsContextValue>({
  ownFeed: undefined,
  ownTimeline: undefined,
  forYouFeed: undefined,
});

export const OwnFeedsContextProvider = ({ children }: PropsWithChildren) => {
  const [ownFeed, setOwnFeed] = useState<Feed>();
  const [ownTimeline, setOwnTimeline] = useState<Feed>();
  const [forYouFeed, setForYouFeed] = useState<Feed>();
  const client = useFeedsClient();
  const connectedUser = useClientConnectedUser();

  useEffect(() => {
    if (!connectedUser || !client) return;

    const feed = client.feed("user", connectedUser.id);
    const timeline = client.feed("timeline", connectedUser.id);
    // foryou is the connected user's explore / discover feed. The selector
    // (e.g. `popular`) is configured server-side on the feed group itself;
    // see FEEDS-REACT-NATIVE.md > For You feed / Explore for the prerequisite
    // dashboard or `getstream api UpdateFeedGroup --id foryou` setup.
    const foryou = client.feed("foryou", connectedUser.id);
    setOwnFeed(feed);
    setOwnTimeline(timeline);
    setForYouFeed(foryou);

    const setup = async () => {
      try {
        await Promise.all([
          feed.getOrCreate({ watch: true }),
          timeline.getOrCreate({ watch: true }),
          // Watch foryou so reactions / new activities / follows propagate
          // through the WebSocket and the Explore tab re-renders reactively.
          // queryActivities cannot do this - it has no reactive subscription.
          foryou.getOrCreate({ watch: true }),
        ]);
        // Self-follow: own posts only appear on own timeline once timeline follows user.
        const alreadyFollows = feed.currentState.own_follows?.find(
          (follow) => follow.source_feed.feed === timeline.feed,
        );
        if (!alreadyFollows) await timeline.follow(feed.feed);
      } catch (err) {
        console.error("Failed to set up own feeds / self-follow", err);
      }
    };
    setup();

    return () => {
      setOwnFeed(undefined);
      setOwnTimeline(undefined);
      setForYouFeed(undefined);
    };
  }, [client, connectedUser]);

  return (
    <OwnFeedsContext.Provider value={{ ownFeed, ownTimeline, forYouFeed }}>
      {children}
    </OwnFeedsContext.Provider>
  );
};

export const useOwnFeedsContext = () => useContext(OwnFeedsContext);
```

Wiring:

- The context is `undefined` until the feeds have been created and loaded.
- Self-follow is idempotent: the `own_follows` check skips it after the first run.
- Most apps mount this exactly once, above the navigator.
- Do not pass `Feed` objects through navigation params. Instead, read them from this context on the destination screen.
- **`foryou` requires a server-side selector config to return any activities** (its default is empty). Configure it once per app with `getstream api UpdateFeedGroup --id foryou --request '{"activity_selectors":[{"type":"popular","min_popularity":1,"cutoff_window":"7d"}]}'` (or via the dashboard) and seed at least one reaction per activity in dev so the popularity score clears `min_popularity`. See [`../credentials.md`](../credentials.md) > Step C6 / C7. If foryou is not in scope for your app, drop it from the context value - all three feeds are independent.

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
- This blueprint is text-only. To attach an image or file, use the **Activity Composer with Image** blueprint below.
- Disable the post button while `canPost === false` so the user cannot submit empty content.

---

## Activity Composer with Image

Adds image attachment to the text composer. Picks a photo with `expo-image-picker` (Expo lane), uploads it through the **client** (`useFeedsClient`, not the `Feed`), and attaches the returned URL. The upload API and attachment shape are documented in [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > Attachments and file uploads. Install the picker first - see [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > App-side helpers for common Feeds UI (`expo-image-picker` for Expo, `react-native-image-picker` for RN CLI).

```tsx
import React, { useCallback, useState } from "react";
import {
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import {
  useFeedContext,
  useFeedsClient,
} from "@stream-io/feeds-react-native-sdk";

export const ActivityComposerWithImage = () => {
  const feed = useFeedContext();
  const client = useFeedsClient();
  const [draft, setDraft] = useState("");
  const [asset, setAsset] = useState<ImagePicker.ImagePickerAsset>();
  const [isPosting, setIsPosting] = useState(false);
  const canPost = (draft.trim().length > 0 || !!asset) && !isPosting;

  const pickImage = useCallback(async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"], // older expo-image-picker: ImagePicker.MediaTypeOptions.Images
      quality: 0.8,
    });
    if (!result.canceled) setAsset(result.assets[0]);
  }, []);

  const post = useCallback(async () => {
    if (!feed || !client || !canPost) return;
    setIsPosting(true);
    try {
      const attachments = [];
      if (asset) {
        // Upload goes through the client. The resulting URL is on `response.file`.
        const uploaded = await client.uploadImage({
          file: {
            uri: asset.uri,
            name: asset.fileName ?? "photo.jpg",
            type: asset.mimeType ?? "image/jpeg",
          },
        });
        attachments.push({ type: "image", image_url: uploaded.file, custom: {} });
      }
      await feed.addActivity({
        type: "post",
        text: draft,
        ...(attachments.length ? { attachments } : {}),
      });
      setDraft("");
      setAsset(undefined);
    } catch (err) {
      console.error("Failed to post activity", err);
    } finally {
      setIsPosting(false);
    }
  }, [feed, client, canPost, draft, asset]);

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
      {asset ? (
        <View style={styles.previewWrap}>
          <Image source={{ uri: asset.uri }} style={styles.preview} />
          <Pressable onPress={() => setAsset(undefined)} style={styles.remove}>
            <Text style={styles.removeText}>Remove</Text>
          </Pressable>
        </View>
      ) : null}
      <View style={styles.footerRow}>
        <Pressable onPress={pickImage} style={styles.attachButton}>
          <Text style={styles.attachText}>Add photo</Text>
        </Pressable>
        <Pressable
          disabled={!canPost}
          onPress={post}
          style={({ pressed }) => [
            styles.button,
            !canPost && styles.buttonDisabled,
            pressed && canPost && styles.buttonPressed,
          ]}
        >
          <Text style={styles.buttonText}>{isPosting ? "Posting..." : "Post"}</Text>
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
  previewWrap: { marginTop: 8 },
  preview: { borderRadius: 10, height: 180, width: "100%" },
  remove: { marginTop: 4 },
  removeText: { color: "#DC2626", fontSize: 13, fontWeight: "600" },
  footerRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 8,
  },
  attachButton: { paddingHorizontal: 4, paddingVertical: 8 },
  attachText: { color: "#2563EB", fontSize: 14, fontWeight: "600" },
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

Wiring:

- Install first (Expo): `npx expo install expo-image-picker`. `expo-image-picker` ships native code, so add its config plugin to `app.json`, then rebuild the dev client (`npx expo prebuild` if you keep native dirs, then a dev-client build) - Expo Go cannot use it:

  ```json
  { "expo": { "plugins": [["expo-image-picker", { "photosPermission": "Allow $(PRODUCT_NAME) to attach photos to your posts." }]] } }
  ```

  The plugin generates `NSPhotoLibraryUsageDescription` on iOS. RN CLI: `npm install react-native-image-picker` + `npx pod-install`.
- Mount inside `<StreamFeed feed={ownFeed}>` exactly like the text composer - `feed.addActivity` posts to the user's own feed.
- Upload through `useFeedsClient()`, **not** the `Feed`. The returned URL is `uploaded.file`. Images use `image_url`; for a document use `client.uploadFile({ file })` + `expo-document-picker` and attach `{ type: "file", asset_url: uploaded.file, custom: {} }`. `custom` is optional per-attachment metadata - pass `{}` when you have none.
- Uploads are capped at 100MB. For large photos, downscale first with `expo-image-manipulator` to cut upload time.
- `mediaTypes: ["images"]` is the current `expo-image-picker` API; SDKs before the array form used `ImagePicker.MediaTypeOptions.Images`.
- `asset.mimeType` / `asset.fileName` can be undefined on some library picks; the `?? "image/jpeg"` fallback then mislabels a PNG/HEIC. Prefer the asset's real `mimeType` (or derive `type` from the file extension) and only fall back when nothing is available.

---

## Explore Screen

For a tab that shows cross-user activity **and reacts live** to follows, reactions, and new posts from other parts of the app, the right primitive is a **watched feed group** - same pattern Home uses for `timeline`, not `client.queryActivities()`.

Why not `queryActivities`: it is a one-shot HTTP call with **no reactive subscription**. The SDK only applies incoming WebSocket events (`feeds.activity.added`, `feeds.activity.reaction.added`, etc.) to feeds you have loaded with `getOrCreate({ watch: true })`. A `queryActivities` result lives in your local `useState` and never updates - so if the user likes a post on Home, the same post on the Explore tab will not reflect the new reaction until you re-issue the query manually. (`queryActivities` still has a use - one-shot lookups like search and exports - see [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > Querying activities for one-shot lookups.)

The reactive primitive is the **`foryou` feed group** (or any custom group you've configured). The selector that decides which activities show up is configured server-side on the group (`popular`, `following`, `current_feed`, ...). For a showcase / demo with seeded data, `popular` with `min_popularity: 1` is the practical floor - see [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > For You feed / Explore prerequisite for the `UpdateFeedGroup` setup + the reaction-seeding requirement.

```tsx
import React from "react";
import { StreamFeed } from "@stream-io/feeds-react-native-sdk";
import { ActivityList } from "@/components/activity/ActivityList";
import { useOwnFeedsContext } from "@/contexts/own-feeds-context";

export const ExploreScreen = () => {
  const { forYouFeed } = useOwnFeedsContext();
  if (!forYouFeed) return null;

  return (
    <StreamFeed feed={forYouFeed}>
      <ActivityList />
    </StreamFeed>
  );
};
```

Wiring:

- Reuses the same `ActivityList` the timeline uses - it reads `useFeedActivities()` from the nearest `<StreamFeed>` context, so reactions / new activities / follows propagate through the WebSocket and the list re-renders automatically.
- `forYouFeed` comes from `OwnFeedsContextProvider`, which already calls `getOrCreate({ watch: true })` on it. Do not create / `getOrCreate` it again on this screen.
- For a tab nested in a navigator with a native iOS tab bar, pass `contentContainerStyle={{ paddingBottom: insets.bottom + 12 }}` to the `ActivityList`'s underlying `FlatList` so the last item clears the tab bar.
- **Empty list at first run?** That is almost always the server-side selector, not your code. Check that the `foryou` feed group has `activity_selectors` configured (the default is none = empty), and that the seeded activities meet the selector's threshold. With `popular` + `min_popularity: 1`, an activity needs at least one reaction / comment / bookmark / share. Seed one reaction per activity during demo setup ([`../credentials.md`](../credentials.md) > Step C7).
- Layering selectors (e.g. `popular` and `following` together) is a way to show activities the user follows even when they have no reactions yet - useful in real apps where most activities will not be "popular" by the time the user first opens the tab.

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
      <Text
        style={[
          styles.label,
          isFollowing ? styles.unfollowLabel : styles.followLabel,
        ]}
      >
        {isFollowing ? "Unfollow" : "Follow"}
      </Text>
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
  // Follow: solid blue pill with white text.
  follow: { backgroundColor: "#2563EB" },
  followLabel: { color: "#FFFFFF" },
  // Unfollow: transparent pill with gray border + gray text. Twitter/Instagram
  // "Following" pattern - less aggressive than a solid red destructive style,
  // and stays readable on any card background. Keep the label color tied to
  // the border color or it goes invisible the moment someone restyles the pill.
  unfollow: { backgroundColor: "transparent", borderColor: "#9CA3AF", borderWidth: 1 },
  unfollowLabel: { color: "#9CA3AF" },
  pressed: { opacity: 0.8 },
  label: { fontSize: 14, fontWeight: "600" },
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

## Push Device Registration

Registers the device's OS push token with Stream so a backgrounded / killed app receives pushes for follows, comments, reactions, and mentions. This is **separate** from the in-app notification feed above. Read [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > Push notifications first - the dashboard provider must exist and its **name** must match `push_provider_name`. Feeds uses `createDevice` / `deleteDevice` (the Video SDK's `addDevice` does not apply here).

```tsx
import { useEffect } from "react";
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { useFeedsClient } from "@stream-io/feeds-react-native-sdk";

// Provider names must match what you configured on the Stream dashboard.
const PROVIDER_NAME_IOS = "your-apn-provider";
const PROVIDER_NAME_ANDROID = "your-firebase-provider";

export const usePushRegistration = () => {
  const client = useFeedsClient();

  useEffect(() => {
    if (!client || !Device.isDevice) return;
    let token: string | undefined;

    const register = async () => {
      const existing = await Notifications.getPermissionsAsync();
      let granted = existing.granted;
      if (!granted) {
        granted = (await Notifications.requestPermissionsAsync()).granted;
      }
      if (!granted) return;

      // Native APNs / FCM device token (NOT the Expo push token).
      const devicePushToken = await Notifications.getDevicePushTokenAsync();
      token = devicePushToken.data;

      await client.createDevice({
        id: token,
        push_provider: Platform.OS === "ios" ? "apn" : "firebase",
        push_provider_name:
          Platform.OS === "ios" ? PROVIDER_NAME_IOS : PROVIDER_NAME_ANDROID,
      });
    };

    register().catch((err) => console.error("Push registration failed", err));

    return () => {
      if (token) {
        client.deleteDevice({ id: token }).catch((err) => console.error(err));
      }
    };
  }, [client]);
};
```

Wiring:

- Call `usePushRegistration()` from a component mounted **under** `<StreamFeeds>` after the user is connected (e.g. the navigator root). The hook no-ops until the client resolves.
- Needs a dev-client / native build - Expo Go cannot receive remote push. Android also needs `google-services.json` + FCM set up; iOS needs the Push Notifications capability and an APNs key uploaded to the dashboard.
- **RN CLI:** swap `expo-notifications` for `@react-native-firebase/messaging` - get the token with `messaging().getToken()` (FCM) / `messaging().getAPNSToken()` (iOS) and make the same `createDevice` call.
- On sign-out, `deleteDevice` so the next user on the same device does not inherit these pushes (this hook does it on unmount; pair it with `client.disconnectUser()` in the Sign-out blueprint).
- `push_provider` is `"apn"` (iOS) | `"firebase"` (Android); `push_provider_name` must match the dashboard provider name.
- On iOS the native APNs token can be unavailable for a moment after permission is granted (the device registers with APNs asynchronously). If `getDevicePushTokenAsync()` rejects on first launch, retry or register from your push library's token-received listener instead of inline.
- Displaying the push and handling the tap (deep-link to the activity / notification screen) is app-owned - see [FEEDS-REACT-NATIVE.md](FEEDS-REACT-NATIVE.md) > Push notifications > Backend trigger and handling the tap.

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
- If push is wired, unregister the device with `client.deleteDevice({ id: token })` before `disconnectUser()` so the next user on the device does not inherit these pushes (see Push Device Registration).
- Do not print user tokens in final summaries or logs.
