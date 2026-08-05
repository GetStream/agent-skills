# Stream Unreal - the UMG widget layer

**This layer has no official documentation.** The docs cover the low-level client thoroughly (where they have Unreal tabs); there is no page for the `WBP_*` chat widgets, which is the part most people actually want. So this runbook *is* the source, derived from the plugin headers and the sample project. Read it before putting chat on screen, and read the headers under `Plugins/StreamChat/Source/StreamChatUi/Public/` for exact signatures.

Every failure mode here is **silent**: an empty widget, no log line, no ensure. That is why the ordering rules below are rules and not tips.

---

## Step 1: The two traps, up front

### Trap 1 - the C++ widget classes cannot be instantiated directly

`UTeamChatMobileWidget`, `UChannelWidget`, `UChannelListWidget`, `UMessageListWidget`, `UMessageComposerWidget` and friends are effectively abstract. Their `UPROPERTY(meta = (BindWidget))` members are only satisfied by the widget tree inside the plugin's **Blueprint** assets. `CreateWidget<UTeamChatMobileWidget>(PC)` with no class argument gives you a widget with every bound pointer null - which renders as nothing, logs nothing, and looks like a data problem.

Load the Blueprint class by path instead. **Note the `_C` suffix** - that is the generated class, not the asset:

```cpp
const TCHAR* Path = TEXT("/StreamChat/UI/TeamChat/WBP_TeamChat_Mobile.WBP_TeamChat_Mobile_C");
UClass* WidgetClass = LoadClass<UTeamChatMobileWidget>(nullptr, Path);
check(WidgetClass);   // fail loudly here rather than rendering nothing later
```

The plugin's content root is `/StreamChat/`, so its assets are addressable without any project asset referencing them. **Which is exactly why Step 5 (cooking) is mandatory** - see below.

In a Blueprint project you sidestep this entirely: pick the `WBP_*` asset in a **Create Widget** node's Class pin, which resolves the Blueprint class by construction.

### Trap 2 - `Setup()` must precede `AddToViewport()`

The exact chain, because the failure is invisible:

```
CreateWidget(...)      -> UStreamWidget::Initialize() - auto-calls OnSetup() if you never did
Setup(Client)          -> ClientContextWidget->Setup(Client), then OnSetup()
AddToViewport()        -> NativePreConstruct(): sets bConstructed, SwitchToChannelList()
                            -> CreateWidget<UChannelListWidget>
                              -> its NativePreConstruct builds the Slate list view, but ONLY
                                 `if (GetClient() && ListView)`
```

`GetClient()` walks up the hierarchy for a `UClientContextWidget`, which is only populated by `Setup`. Call `Setup` **after** `AddToViewport` and `GetClient()` is null exactly when the channel list is built, the `SPaginateListWidget` is never created, and **nothing rebuilds it later**. The widget renders empty forever, with no error.

```cpp
UTeamChatMobileWidget* W = CreateWidget<UTeamChatMobileWidget>(PlayerController, WidgetClass);
W->Setup(Client);        // MUST come first
W->AddToViewport();
```

Two related details:

- `UStreamWidget::Initialize()` calls `OnSetup()` itself when `Setup` was never called, so `OnSetup` can run **twice**. Keep any `OnSetup` override idempotent.
- `GetClient()` / `GetChannel()` / `GetClientContext()` / `GetTheme()` all carry `ensureMsgf(bConstructed, "The widget needs to have been added to a parent/viewport first")`. They are `protected`, so only a subclass can trip this - but a subclass that reads the client in its constructor or `OnSetup` will, in development builds.

---

## Step 2: Pick the widget

All paths are under `/StreamChat/UI/`. Append `.<AssetName>_C` for the `LoadClass` path (e.g. `TeamChat/WBP_TeamChat_Mobile` -> `/StreamChat/UI/TeamChat/WBP_TeamChat_Mobile.WBP_TeamChat_Mobile_C`).

### Whole-screen entry points - start here

| Asset | C++ class | `Setup` takes | Use |
|---|---|---|---|
| `TeamChat/WBP_TeamChat_Mobile` | `UTeamChatMobileWidget` | `UStreamChatClientComponent*` | **Full mobile chat app**: channel list + message list with back-navigation. The one-liner for a first integration. |
| `TeamChat/WBP_TeamChat` | `UTeamChatWidget` | `UStreamChatClientComponent*` | Desktop two-pane team chat (list beside conversation). |
| `WBP_InGameChat` | `UInGameChatWidget` | `UChatChannel*` | Fading overlay chat for a game HUD. Needs a `UClientContextWidget` ancestor. |

The two Team Chat widgets are **self-contained** - each owns a `ClientContextWidget` internally, so `Setup(Client)` is all the wiring they need.

### Sub-surfaces - compose these yourself

| Asset | C++ class | `Setup` takes | Notes |
|---|---|---|---|
| `Channel/WBP_Channel_Mobile` / `Channel/WBP_Channel` | `UChannelWidget` | `UChatChannel*` | One conversation: header + message list + composer. Owns its own `ChannelContext`, but still needs a **client** context ancestor. |
| `TeamChat/WBP_ChannelList_Mobile` / `TeamChat/WBP_ChannelList` | `UChannelListWidget` | *(no public `Setup`)* | Channel list only. Reads everything from its ancestor contexts - so it must sit under a `UClientContextWidget`. |
| `Channel/WBP_MessageList` | `UMessageListWidget` | *(none)* | Message list. Reads the channel from the ancestor `UChannelContextWidget`. Paginates itself. |
| `Channel/WBP_FadingMessageList` | `UFadingMessageListWidget` | `UChatChannel*` (+ optional `FTimespan` lifetime) | Messages that fade out - the in-game overlay list. |
| `Input/MessageComposer/WBP_MessageComposer` | `UMessageComposerWidget` | *(none)* | Composer. Finds the channel via `UChannelContextWidget` in `NativeConstruct`, so it **only works inside a channel context**. |
| `Header/WBP_MessageListHeader_Mobile` / `Header/WBP_MessageListHeader` | `UMessageListHeaderWidget` | *(none)* | Conversation header with typing indicator + online status. |
| `Message/WBP_Message`, `Message/WBP_TextBubble` | `UMessageWidget` | `FMessage`, `EMessageSide`, `EMessagePosition` | One message row. The unit to replace for custom message rendering (Step 4). |
| `Avatar/WBP_Avatar`, `Avatar/WBP_NamedAvatar` | `UAvatarWidget`, `UNamedAvatarWidget` | `TArray<FUserRef>` (+ size) / `FUserRef` | Avatars. `UAvatarWidget::SetupWithUrl` for a raw URL. |
| `Reaction/WBP_ReactionPicker`, `Reaction/WBP_BottomReactions`, `Reaction/WBP_MessageReactions` | `UReactionPickerWidget`, `UBottomReactionWidget`, `UMessageReactionsWidget` | - | Reaction picker and display. |
| `ContextMenu/WBP_ContextMenu` | `UContextMenuWidget` | - | Long-press / right-click message actions. Actions are `UContextMenuAction` subclasses: copy, edit, delete, flag, ban, mute (see `Public/ContextMenu/`). |
| `TeamChat/WBP_NewChat` | `UNewChatWidget` | - | Create-a-chat flow with contact selection. |

There are 46 `WBP_*` assets in total; `ls`-equivalent the plugin's `Content/UI` tree if you need one not listed. The C++ class for each lives at the matching path under `Source/StreamChatUi/Public/`.

### Themes

`Themes/LightTheme`, `Themes/DarkTheme`, `Themes/GamingTheme` are `UThemeDataAsset` instances - see Step 3.

---

## Step 3: Wire it

### The context model (this is the whole mental model)

`UStreamWidget::GetClient()` / `GetChannel()` / `GetTheme()` walk **up** the widget hierarchy looking for a `UClientContextWidget` / `UChannelContextWidget` / `UThemeContextWidget`. Anything built outside that hierarchy sees null and renders nothing.

- Using `WBP_TeamChat_Mobile` or `WBP_TeamChat`: nothing to do, they own their client context.
- Composing your own root: put a `UClientContextWidget` at the top and call its `Setup(Client)`, then nest a `UChannelContextWidget` (`Setup(Channel)`) around anything channel-scoped (message list, composer, header).
- `UClientContextWidget` also sets `bApplySafeAreaPadding = true`, and `UContextWidget` wraps its content in `SSafeZone`. **So notch / home-indicator handling is free only if your root is (or is under) a `UClientContextWidget`.** Nested contexts deliberately leave it off to avoid insetting twice - a hand-rolled root must apply `SSafeZone` / `GetSafeZonePadding` itself, because UMG does not honour platform insets otherwise.

`UClientContextWidget` is also the navigation bus: `OnChannelSelected` and `OnBack` are the delegates the Team Chat widgets use to swap panes, and `SelectChannel(Channel)` is how you drive it from your own code.

### The channel list does not load itself

`UChannelListWidget::NativePreConstruct` binds its list to `GetClient()->GetChannels()` and **never queries**. Populate that array first or the UI is permanently empty:

```cpp
const FFilter Filter = FFilter::In(TEXT("members"), {MyUserId});
Client->QueryChannels(
    Filter,
    {{EChannelSortField::LastMessageAt, ESortDirection::Descending}},
    EChannelFlags::State | EChannelFlags::Watch,   // Watch is what keeps it live
    {},                                            // FPaginationOptions
    [](const TArray<UChatChannel*>& Channels) { /* now show the UI */ });
```

Pagination past the first page is handled for you: the widget calls `QueryAdditionalChannels(Limit)` when the user scrolls (`Limit` defaults to 10, editable on the widget). Do not add your own scroll handler.

### Full mobile chat on the HUD

```cpp
void AMyHud::ShowChatUi()
{
    const TCHAR* Path = TEXT("/StreamChat/UI/TeamChat/WBP_TeamChat_Mobile.WBP_TeamChat_Mobile_C");
    UClass* WidgetClass = LoadClass<UTeamChatMobileWidget>(nullptr, Path);
    if (!WidgetClass)
    {
        // Almost always a missing cook directive in a packaged build - see Step 5.
        UE_LOG(LogTemp, Error, TEXT("Could not load %s"), Path);
        return;
    }

    UTeamChatMobileWidget* Widget = CreateWidget<UTeamChatMobileWidget>(GetOwningPlayerController(), WidgetClass);
    Widget->Setup(Client);      // before AddToViewport - see Trap 2
    Widget->AddToViewport();
}
```

Requires `StreamChatUi` and `UMG` in the module's `PrivateDependencyModuleNames` ([`setup.md`](setup.md) 2b), plus `#include "Team/TeamChatMobileWidget.h"`.

For touch platforms this also needs the input config in [`platforms.md`](platforms.md) - without it the virtual joystick swallows every tap and the widget looks frozen.

### Overlay chat on a game HUD

`UInGameChatWidget` takes a **channel**, not a client, and needs a client context above it. The simplest correct shape is a small project-side `WBP` whose root is a `UClientContextWidget` containing the in-game chat widget; then `Setup` the context with the client and the chat widget with the channel. Alternatively, wire it as the sample's In-Game Chat demo does - clone that map's HUD Blueprint rather than reinventing it.

Because it is an overlay on gameplay, keep the input config in mind: chat that captures all input breaks the game, and a game that captures all input breaks chat. Decide which owns the pointer, and toggle `SetInputMode` deliberately.

---

## Step 4: Customize

In order of increasing cost. Do not jump to the last one.

1. **Theme** - swap the `UThemeDataAsset`. `UThemeDataAsset` is a named-color palette (`Palette`, a `TMap<FName, FLinearColor>`) plus semantic slots that reference palette entries by name: `MeBubbleColor`, `YouBubbleColor`, `DeletedBubbleColor`, `MessageComposerBackgroundColor`, `MessageInputBackgroundColor`, `TimestampTextColor`, `bColoredName`, `BubbleHtmlStyles`, and more. So a reskin is: duplicate `LightTheme` (or `GamingTheme`, which is the game-facing one) into project content, edit the palette, and point the `UThemeContextWidget`'s `Theme` property at it. Changing a semantic slot means changing which **palette name** it points to - read `Public/ThemeDataAsset.h` for the full slot list before guessing a name.
2. **Widget-level `EditAnywhere` properties** - several widgets expose knobs without any code: `UChannelListWidget::Limit` and `bAutoSelectFirstChannel`, `UMessageListWidget::Limit`, `UMessageComposerWidget::IconTextureSend` / `IconTextureConfirm` / paddings, `UFadingMessageListWidget`'s message lifetime.
3. **Swap a sub-widget class** - the composite widgets expose `TSubclassOf<>` defaults: `UTeamChatMobileWidget::ChannelListWidgetClass` / `ChannelWidgetClass`, `UTeamChatWidget::ChannelWidgetClass` / `NewChatWidgetClass`, `UChannelListWidget::ChannelStatusWidgetClass` / `NewChatChannelStatusWidgetClass`, `UMessageListWidget::MessageWidgetClass`. Set these on a **derived Blueprint** of the plugin's `WBP_*` (reparent a copy in project content) to change one piece without rebuilding the screen.
4. **Custom message rows** - `UMessageListWidget` exposes `OnGetMessageWidgetEvent`, a Blueprint-bindable delegate `(FMessage, EMessageSide, EMessagePosition) -> UMessageWidget*`. This is the intended hook for bespoke message rendering; it keeps the list, pagination, and scroll-to-bottom behaviour.
5. **Hook the composer** - `UMessageComposerWidget::OnSendMessage` fires **before** the message is sent and **cancels the send if the handler clears the text**. That is the place for a client-side profanity filter, a slash-command parser, or a length guard. `EditMessage(Message)` puts the composer into edit mode.
6. **Build your own UI on the client** - only when the design genuinely is not a messenger. You keep `UStreamChatClientComponent`, `UChatChannel`, and the event subscriptions, and render everything yourself. Costs you avatars, grouping, reactions, pagination, typing indicators, safe-area handling, and the context menu - so choose it deliberately, and say what is being given up.

**Prefer the shipped widgets for a first integration.** They are an early preview and they look like it in places, but they carry behaviour that is tedious and error-prone to reproduce.

---

## Step 5: Cooking - mandatory whenever you load by path

Because the widgets are loaded by **path** at runtime, nothing in the project references them, so the cooker has no reason to include them and a packaged build finds no widget class. The app works in the editor and breaks when packaged, which is the worst class of bug to ship.

```ini
; Config/DefaultGame.ini
[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysCook=(Path="/StreamChat/UI")
+DirectoriesToAlwaysCook=(Path="/StreamChat/Font")
```

`/StreamChat/Font` is separate and also needed - the widget tree references Roboto and `TwemojiMozilla` (the emoji font behind reaction icons).

**Rule: emitting a `LoadClass` on a `/StreamChat/...` path and not emitting these lines is a bug.** They travel together.

The compile-only iOS/Android path never cooks, so a missing directive is **invisible** there - it only surfaces as a missing widget class once you actually package. See [`platforms.md`](platforms.md).

A Blueprint-driven integration that references `WBP_TeamChat_Mobile` from a project asset does not need this, because the reference makes the cooker include it. If you are unsure which shape the project has, add the directives anyway - they are cheap.

---

## Step 6: Verify

Do not call this done until you have run it.

- **Zero `LogUMG` warnings.** Every failed `BindWidget` logs there, so a clean `LogUMG` is real evidence the whole Stream widget tree built. This is the single best signal for this layer.
- **The channel list has rows.** Empty list + no error = either `QueryChannels` was never called (Step 3) or `Setup` came after `AddToViewport` (Trap 2). Both look identical on screen; check the code, not the pixels.
- **A message sent from another client appears without a reload.** If not, `EChannelFlags::Watch` is missing from the query.
- **Tap/scroll works on device**, not just click-in-editor - that is the input config in [`platforms.md`](platforms.md).
- **Package it before declaring the UI done** if the integration loads by path. Editor-only success proves nothing about the cook.
