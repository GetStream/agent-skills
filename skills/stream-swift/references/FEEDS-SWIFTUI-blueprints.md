# Feeds SwiftUI - View Blueprints

Load only the section you are implementing. For SDK setup, client initialization, and gotchas, see [FEEDS-SWIFTUI.md](FEEDS-SWIFTUI.md).

Stream Feeds has **no pre-built UI components** - every screen is custom SwiftUI built against the SDK's observable state objects.

---

## App Entry Point Blueprint

```swift
import StreamCore
import StreamFeeds
import SwiftUI

@main
struct MyFeedsApp: App {
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()
    private init() {}

    @Published var viewState: ViewState = .loggedOut
    var client: FeedsClient?

    enum ViewState {
        case connecting
        case loggedIn(FeedsClient)
        case loggedOut
    }

    func connect(apiKey: String, userId: String, userName: String, token: String) async {
        viewState = .connecting
        let user = User(id: userId, name: userName, imageURL: nil)
        let userToken = UserToken(rawValue: token)
        let feedsClient = FeedsClient(apiKey: APIKey(apiKey), user: user, token: userToken)
        do {
            try await feedsClient.connect()
            client = feedsClient
            viewState = .loggedIn(feedsClient)
        } catch {
            viewState = .loggedOut
        }
    }

    func disconnect() async {
        guard let client else { return }
        await client.disconnect()
        self.client = nil
        viewState = .loggedOut
    }
}

struct RootView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        switch appState.viewState {
        case .connecting:
            ProgressView()
        case .loggedIn(let client):
            FeedsRootView(client: client)
        case .loggedOut:
            LoginView()
        }
    }
}
```

**Wiring:**
- `@StateObject` in the `App` keeps `AppState` alive across SwiftUI re-creations
- Pass `client` into child views - don't store it in `@EnvironmentObject` directly
- `connect()` is fully async; call it from a `.task` or button action

---

## Main Feed View Blueprint (Twitter-style timeline)

Three `Feed` objects are created once in `init` - regular posts, stories, and notifications. Hold them as `@State` so SwiftUI doesn't recreate them.

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct FeedsRootView: View {
    let client: FeedsClient

    @State private var feed: Feed
    @State private var storiesFeed: Feed
    @State private var notificationFeed: Feed
    @ObservedObject var notificationState: FeedState

    init(client: FeedsClient) {
        self.client = client

        // Posts feed - excludes stories
        let postsQuery = FeedQuery(
            feed: FeedId(group: "user", id: client.user.id),
            activityFilter: .exists(.expiresAt, false),
            data: .init(members: [.init(userId: client.user.id)], visibility: .public)
        )
        let postsFeed = client.feed(for: postsQuery)
        _feed = State(initialValue: postsFeed)

        // Stories feed - only activities with expiresAt set
        let storiesQuery = FeedQuery(
            feed: FeedId(group: "user", id: client.user.id),
            activityFilter: .exists(.expiresAt, true),
            data: .init(members: [.init(userId: client.user.id)], visibility: .public)
        )
        let stories = client.feed(for: storiesQuery)
        _storiesFeed = State(initialValue: stories)

        // Notification feed
        let notifFeed = client.feed(for: FeedId(group: "notification", id: client.user.id))
        _notificationFeed = State(initialValue: notifFeed)
        notificationState = notifFeed.state
    }

    var body: some View {
        NavigationStack {
            ActivityListView(feed: feed, storiesFeed: storiesFeed, client: client)
                .task { try? await notificationFeed.getOrCreate() }
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        NotificationBellButton(state: notificationState) {
                            // present notification feed sheet
                        }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Profile") { /* present profile sheet */ }
                    }
                }
                .navigationTitle("Home")
        }
    }
}

struct NotificationBellButton: View {
    @ObservedObject var state: FeedState
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell")
                if let unread = state.notificationStatus?.unread, unread > 0 {
                    Text("\(unread)")
                        .font(.caption2).bold()
                        .foregroundStyle(.white)
                        .padding(4)
                        .background(Color.red, in: Circle())
                        .offset(x: 8, y: -8)
                }
            }
        }
    }
}
```

---

## Activity List View Blueprint (timeline)

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct ActivityListView: View {
    let feed: Feed
    let storiesFeed: Feed
    let client: FeedsClient

    @ObservedObject var state: FeedState
    @ObservedObject var storiesState: FeedState

    @State private var showComposer = false
    @State private var commentsActivity: ActivityData?

    init(feed: Feed, storiesFeed: Feed, client: FeedsClient) {
        self.feed = feed
        self.storiesFeed = storiesFeed
        self.client = client
        state = feed.state
        storiesState = storiesFeed.state
    }

    var body: some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                // Stories strip
                if !storiesState.activities.isEmpty {
                    StoriesStripView(stories: storiesState.activities)
                        .padding(.bottom, 8)
                    Divider()
                }

                // Activity rows
                ForEach(state.activities) { activity in
                    ActivityRowView(
                        activity: activity,
                        feed: feed,
                        client: client,
                        onComment: { commentsActivity = $0 }
                    )
                    Divider()

                    // Pagination trigger at bottom
                    if activity.id == state.activities.last?.id {
                        Color.clear.frame(height: 1)
                            .task {
                                guard state.canLoadMoreActivities else { return }
                                try? await feed.queryMoreActivities(limit: 10)
                            }
                    }
                }
            }
        }
        .refreshable { try? await feed.getOrCreate() }
        .onAppear { Task { try? await feed.getOrCreate()
                          try? await storiesFeed.getOrCreate() } }
        .overlay(alignment: .bottomTrailing) {
            Button { showComposer = true } label: {
                Image(systemName: "plus")
                    .font(.title2).bold()
                    .foregroundStyle(.white)
                    .frame(width: 56, height: 56)
                    .background(.blue, in: Circle())
                    .shadow(radius: 4)
            }
            .padding(20)
        }
        .sheet(isPresented: $showComposer) {
            ActivityComposerView(feed: feed, client: client)
                .presentationDetents([.medium])
        }
        .sheet(item: $commentsActivity) { activity in
            CommentsView(activityId: activity.id, feed: feed, client: client)
                .presentationDetents([.large])
        }
    }
}
```

**Wiring:**
- `state = feed.state` in `init` - never replace it after init
- Pagination: check `state.canLoadMoreActivities` before calling `queryMoreActivities`
- `refreshable` reruns `getOrCreate()` which resets and reloads

---

## Activity Row View Blueprint

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct ActivityRowView: View {
    let activity: ActivityData
    let feed: Feed
    let client: FeedsClient
    let onComment: (ActivityData) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Repost header
            if let parent = activity.parent {
                Label("\(activity.user.name ?? activity.user.id) reposted", systemImage: "repeat")
                    .font(.caption).foregroundStyle(.secondary)
                ActivityContentView(activity: parent)
            } else {
                ActivityContentView(activity: activity)
            }

            // Action bar
            ActivityActionsView(
                activity: activity,
                feed: feed,
                onComment: { onComment(activity) }
            )
            .padding(.horizontal)
        }
        .padding(.vertical, 12)
        .padding(.horizontal)
        .contextMenu {
            if activity.user.id == client.user.id {
                Button("Edit", systemImage: "pencil") { /* trigger edit sheet */ }
                Button("Delete", systemImage: "trash", role: .destructive) {
                    Task { try? await feed.deleteActivity(id: activity.id) }
                }
            }
        }
    }
}

struct ActivityContentView: View {
    let activity: ActivityData

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            AsyncImage(url: activity.user.imageURL) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Circle().fill(Color.secondary.opacity(0.3))
            }
            .frame(width: 44, height: 44)
            .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(activity.user.name ?? activity.user.id).bold()
                    Spacer()
                    Text(activity.createdAt, style: .relative)
                        .font(.caption).foregroundStyle(.secondary)
                }
                if let text = activity.text, !text.isEmpty {
                    Text(text)
                }
                if !activity.attachments.isEmpty {
                    AttachmentsGridView(attachments: activity.attachments)
                }
            }
        }
    }
}

struct ActivityActionsView: View {
    let activity: ActivityData
    let feed: Feed
    let onComment: () -> Void

    private var hasLiked: Bool { !activity.ownReactions.filter { $0.type == "heart" }.isEmpty }
    private var likeCount: Int { activity.reactionGroups["heart"]?.count ?? 0 }
    private var isBookmarked: Bool { !activity.ownBookmarks.isEmpty }

    var body: some View {
        HStack(spacing: 32) {
            // Comment
            Button { onComment() } label: {
                Label("\(activity.commentCount)", systemImage: "bubble.right")
            }

            // Like
            Button {
                Task {
                    if hasLiked {
                        try? await feed.deleteReaction(activityId: activity.id, type: "heart")
                    } else {
                        try? await feed.addReaction(
                            activityId: activity.id,
                            request: .init(createNotificationActivity: true, type: "heart")
                        )
                    }
                }
            } label: {
                Label("\(likeCount)", systemImage: hasLiked ? "heart.fill" : "heart")
                    .foregroundStyle(hasLiked ? .red : .secondary)
            }

            // Repost
            Button {
                Task { try? await feed.repost(activityId: activity.id, text: nil) }
            } label: {
                Label("\(activity.shareCount)", systemImage: "repeat")
            }

            // Bookmark
            Button {
                Task {
                    if isBookmarked {
                        try? await feed.deleteBookmark(activityId: activity.id)
                    } else {
                        try? await feed.addBookmark(activityId: activity.id)
                    }
                }
            } label: {
                Image(systemName: isBookmarked ? "bookmark.fill" : "bookmark")
                    .foregroundStyle(isBookmarked ? .blue : .secondary)
            }

            Spacer()
        }
        .font(.subheadline)
        .foregroundStyle(.secondary)
        .buttonStyle(.plain)
    }
}
```

---

## Activity Composer View Blueprint

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct ActivityComposerView: View {
    let feed: Feed
    let client: FeedsClient

    @State private var text = ""
    @State private var isPosting = false
    @State private var postAsStory = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                TextEditor(text: $text)
                    .frame(minHeight: 120)
                    .padding(8)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.3)))

                Toggle("Post as Story (expires in 24h)", isOn: $postAsStory)
                    .padding(.horizontal)

                Spacer()
            }
            .padding()
            .navigationTitle("New Post")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Post") { Task { await post() } }
                        .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isPosting)
                }
            }
            .overlay { if isPosting { ProgressView() } }
        }
    }

    private func post() async {
        isPosting = true
        var expiresAt: String? = nil
        if postAsStory {
            expiresAt = ISO8601DateFormatter().string(from: Date().addingTimeInterval(24 * 3600))
        }
        do {
            try await feed.addActivity(
                request: .init(expiresAt: expiresAt, text: text, type: "post")
            )
            dismiss()
        } catch {
            // surface error to user
        }
        isPosting = false
    }
}
```

---

## Comments View Blueprint (3-level threading)

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct CommentsView: View {
    let activityId: String
    let feed: Feed
    let client: FeedsClient

    @State private var activity: Activity
    @StateObject private var activityState: ActivityState
    @State private var replyToId: String?
    @State private var commentText = ""
    @State private var isSubmitting = false

    init(activityId: String, feed: Feed, client: FeedsClient) {
        self.activityId = activityId
        self.feed = feed
        self.client = client
        let a = client.activity(for: activityId, in: feed.feed)
        _activity = State(initialValue: a)
        _activityState = StateObject(wrappedValue: a.state)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(activityState.comments, id: \.id) { threaded in
                        CommentRowView(
                            comment: threaded,
                            activity: activity,
                            currentUserId: client.user.id,
                            onReply: { replyToId = threaded.id }
                        )

                        if let replies = threaded.replies {
                            ForEach(replies, id: \.id) { reply in
                                CommentRowView(
                                    comment: .init(replies: nil, id: reply.id, text: reply.text,
                                                   user: reply.user, reactionGroups: reply.reactionGroups,
                                                   ownReactions: reply.ownReactions, parentId: reply.parentId,
                                                   replyCount: reply.replyCount),
                                    activity: activity,
                                    currentUserId: client.user.id,
                                    onReply: { replyToId = threaded.id }
                                )
                                .padding(.leading, 40)
                            }
                        }
                    }
                }
                .padding()
            }
            .task { try? await activity.get() }
            .safeAreaInset(edge: .bottom) {
                CommentInputBar(
                    text: $commentText,
                    placeholder: replyToId != nil ? "Reply..." : "Add a comment...",
                    isSubmitting: isSubmitting
                ) {
                    Task { await submitComment() }
                }
            }
            .navigationTitle("Comments")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func submitComment() async {
        let trimmed = commentText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        isSubmitting = true
        do {
            try await activity.addComment(
                request: .init(comment: trimmed, createNotificationActivity: true, parentId: replyToId)
            )
            commentText = ""
            replyToId = nil
        } catch { /* surface error */ }
        isSubmitting = false
    }
}

struct CommentRowView: View {
    let comment: ThreadedCommentData
    let activity: Activity
    let currentUserId: String
    let onReply: () -> Void

    private var hasLiked: Bool { !comment.ownReactions.filter { $0.type == "heart" }.isEmpty }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            AsyncImage(url: comment.user.imageURL) { image in
                image.resizable().scaledToFill()
            } placeholder: { Circle().fill(Color.secondary.opacity(0.3)) }
                .frame(width: 32, height: 32).clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                Text(comment.user.name ?? comment.user.id).bold().font(.subheadline)
                if let text = comment.text { Text(text) }

                HStack(spacing: 16) {
                    Button("Reply") { onReply() }
                    Button {
                        Task {
                            if hasLiked {
                                try? await activity.deleteCommentReaction(commentId: comment.id, type: "heart")
                            } else {
                                try? await activity.addCommentReaction(commentId: comment.id, request: .init(type: "heart"))
                            }
                        }
                    } label: {
                        Label("\(comment.reactionGroups["heart"]?.count ?? 0)",
                              systemImage: hasLiked ? "heart.fill" : "heart")
                            .foregroundStyle(hasLiked ? .red : .secondary)
                    }
                }
                .font(.caption)
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
        }
    }
}

struct CommentInputBar: View {
    @Binding var text: String
    let placeholder: String
    let isSubmitting: Bool
    let onSend: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            TextField(placeholder, text: $text, axis: .vertical)
                .lineLimit(1...4)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20))

            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .secondary : .blue)
            }
            .disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSubmitting)
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(.bar)
    }
}
```

**Wiring:**
- `@StateObject` owns `ActivityState` - `@StateObject` keeps it alive for the lifetime of the sheet
- `activity.get()` loads both the activity data and its comments into `activityState.comments`
- `parentId` on `addComment` drives reply threading; `nil` = top-level comment

---

## Profile / Follow Graph View Blueprint

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct ProfileView: View {
    let feed: Feed
    let client: FeedsClient

    @ObservedObject var state: FeedState
    @State private var followSuggestions: [FeedData] = []

    init(feed: Feed, client: FeedsClient) {
        self.feed = feed
        self.client = client
        state = feed.state
    }

    var body: some View {
        NavigationStack {
            List {
                // Follow requests
                if !state.followRequests.isEmpty {
                    Section("Follow Requests") {
                        ForEach(state.followRequests, id: \.sourceFeed.feed.rawValue) { request in
                            HStack {
                                Text(request.sourceFeed.createdBy?.name ?? request.sourceFeed.feed.id)
                                Spacer()
                                Button("Accept") {
                                    Task { try? await feed.acceptFollow(request.sourceFeed.feed) }
                                }.buttonStyle(.borderedProminent).controlSize(.small)
                                Button("Reject") {
                                    Task { try? await feed.rejectFollow(request.sourceFeed.feed) }
                                }.buttonStyle(.bordered).controlSize(.small)
                            }
                        }
                    }
                }

                // Following
                Section("Following (\(state.following.count))") {
                    ForEach(state.following, id: \.targetFeed.feed.rawValue) { follow in
                        HStack {
                            Text(follow.targetFeed.createdBy?.name ?? follow.targetFeed.feed.id)
                            Spacer()
                            Button("Unfollow") {
                                Task { try? await feed.unfollow(follow.targetFeed.feed) }
                            }.buttonStyle(.bordered).controlSize(.small)
                        }
                    }
                }

                // Followers
                Section("Followers (\(state.followers.count))") {
                    ForEach(state.followers, id: \.sourceFeed.feed.rawValue) { follower in
                        Text(follower.sourceFeed.createdBy?.name ?? follower.sourceFeed.feed.id)
                    }
                }

                // Who to follow
                if !followSuggestions.isEmpty {
                    Section("Who to Follow") {
                        ForEach(followSuggestions, id: \.feed.rawValue) { suggestion in
                            HStack {
                                AsyncImage(url: suggestion.createdBy?.imageURL) { image in
                                    image.resizable().scaledToFill()
                                } placeholder: { Circle().fill(Color.secondary.opacity(0.3)) }
                                    .frame(width: 36, height: 36).clipShape(Circle())
                                Text(suggestion.createdBy?.name ?? suggestion.feed.id)
                                Spacer()
                                Button("Follow") {
                                    Task {
                                        try? await feed.follow(suggestion.feed, createNotificationActivity: true)
                                    }
                                }.buttonStyle(.borderedProminent).controlSize(.small)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Profile")
            .task {
                followSuggestions = (try? await feed.queryFollowSuggestions(limit: 10)) ?? []
            }
        }
    }
}
```

---

## Notification Feed View Blueprint

```swift
import StreamCore
import StreamFeeds
import SwiftUI

struct NotificationFeedView: View {
    let notificationFeed: Feed

    @ObservedObject var state: FeedState

    init(notificationFeed: Feed) {
        self.notificationFeed = notificationFeed
        state = notificationFeed.state
    }

    var body: some View {
        NavigationStack {
            List {
                if let status = state.notificationStatus, status.unread > 0 {
                    Button("Mark all as read") {
                        Task {
                            try? await notificationFeed.markActivity(request: .init(markAllRead: true))
                        }
                    }
                    .frame(maxWidth: .infinity)
                }

                ForEach(state.aggregatedActivities, id: \.id) { aggregated in
                    HStack(spacing: 12) {
                        // Avatar of first actor
                        if let firstActivity = aggregated.activities.first {
                            AsyncImage(url: firstActivity.user.imageURL) { image in
                                image.resizable().scaledToFill()
                            } placeholder: { Circle().fill(Color.secondary.opacity(0.3)) }
                                .frame(width: 40, height: 40).clipShape(Circle())
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            Text(aggregated.displayText)
                                .font(.subheadline)
                            Text(aggregated.activities.first?.createdAt ?? Date(), style: .relative)
                                .font(.caption).foregroundStyle(.secondary)
                        }

                        Spacer()

                        // Unread indicator
                        if !isRead(aggregated.id) {
                            Circle().fill(.blue).frame(width: 8, height: 8)
                        }
                    }
                    .padding(.vertical, 4)
                    .listRowBackground(isRead(aggregated.id) ? Color.clear : Color.blue.opacity(0.06))
                    .onTapGesture {
                        Task {
                            try? await notificationFeed.markActivity(request: .init(readActivities: [aggregated.id]))
                        }
                    }
                }
            }
            .listStyle(.plain)
            .navigationTitle("Notifications")
            .task { try? await notificationFeed.getOrCreate() }
        }
    }

    private func isRead(_ id: String) -> Bool {
        state.notificationStatus?.readActivities.contains(id) == true
    }
}

extension AggregatedActivityData {
    var displayText: String {
        let names = activities.prefix(2).map { $0.user.name ?? $0.user.id }.joined(separator: " and ")
        let extra = actorCount > 2 ? " and \(actorCount - 2) others" : ""
        switch verb {
        case "react": return "\(names)\(extra) reacted to your post"
        case "comment": return "\(names)\(extra) commented on your post"
        case "follow": return "\(names)\(extra) followed you"
        default: return "\(names)\(extra) \(verb) your post"
        }
    }
}
```

**Wiring:**
- `state.aggregatedActivities` is the correct property for notification feeds, not `state.activities`
- `state.notificationStatus?.unread` drives the badge count in the bell icon
- `markActivity(request: .init(markAllRead: true))` clears all unread - individual mark uses `readActivities: [id]`

---

## Stories Strip Blueprint

```swift
struct StoriesStripView: View {
    let stories: [ActivityData]
    @State private var selectedStory: ActivityData?

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            LazyHStack(spacing: 12) {
                ForEach(stories) { story in
                    Button { selectedStory = story } label: {
                        AsyncImage(url: story.user.imageURL) { image in
                            image.resizable().scaledToFill()
                        } placeholder: { Circle().fill(Color.secondary.opacity(0.3)) }
                            .frame(width: 56, height: 56)
                            .clipShape(Circle())
                            .overlay(Circle().stroke(
                                LinearGradient(colors: [.purple, .pink, .orange],
                                               startPoint: .topLeading, endPoint: .bottomTrailing),
                                lineWidth: 2
                            ))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal)
        }
        .frame(height: 72)
        .sheet(item: $selectedStory) { story in
            StoryViewer(story: story)
        }
    }
}
```

**Wiring:**
- Stories come from a separate `Feed` with `activityFilter: .exists(.expiresAt, true)`
- `activity.expiresAt` is the ISO8601 string - use `ISO8601DateFormatter` to check remaining time
