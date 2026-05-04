# Video UIKit - View Controller Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [VIDEO-UIKIT.md](VIDEO-UIKIT.md).

---

## CallViewController Subclass (Required)

The default `CallViewController.setupVideoView()` creates a `UIHostingController` for the SwiftUI call UI but immediately discards it - ARC releases the hosting controller while its view is still on screen. This tears down SwiftUI's gesture recognizers, making all buttons in the call screen untappable.

**Always use this subclass instead of `CallViewController` directly:**

```swift
// VideoCallViewController.swift
import UIKit
import SwiftUI
import StreamVideoSwiftUI
import StreamVideoUIKit

class VideoCallViewController: CallViewController {
    private var callHostingController: UIViewController?

    override func setupVideoView() {
        let content = CallContainer(viewFactory: DefaultViewFactory.shared, viewModel: viewModel)
        let hosting = UIHostingController(rootView: content)
        addChild(hosting)
        hosting.view.translatesAutoresizingMaskIntoConstraints = false
        hosting.view.backgroundColor = .clear
        view.addSubview(hosting.view)
        NSLayoutConstraint.activate([
            hosting.view.topAnchor.constraint(equalTo: view.topAnchor),
            hosting.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            hosting.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            hosting.view.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        hosting.didMove(toParent: self)
        callHostingController = hosting
    }
}
```

**Why this works:** `addChild` + `didMove(toParent:)` puts the `UIHostingController` in the VC hierarchy so UIKit routes touches through it correctly. Storing it in `callHostingController` keeps it alive for the lifetime of the call screen.

Use `VideoCallViewController` everywhere `CallViewController` would be used.

---

## AppDelegate Blueprint

```swift
// AppDelegate.swift
import UIKit
import StreamVideo
import StreamVideoSwiftUI

class AppDelegate: NSObject, UIApplicationDelegate {
    var streamVideo: StreamVideo?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let user = User(id: "your-user-id", name: "Your Name", imageURL: nil, customData: [:])
        let token = UserToken(rawValue: "your_token")
        let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
        streamVideo = client
        _ = StreamVideoUI(streamVideo: client)
        return true
    }
}
```

**Wiring:**
- `streamVideo` must be a stored strong reference - if it goes out of scope the client disconnects
- `StreamVideoUI` must be created before any call view renders; the `_` discard is intentional - it registers itself globally
- Use `@UIApplicationDelegateAdaptor(AppDelegate.self)` in your `App` struct if the project is SwiftUI-hosted

---

## HomeViewController Blueprint

Lets the user enter a call ID and join or start a new call. Observes `callingState` to dismiss the call screen when the call ends.

```swift
// HomeViewController.swift
import UIKit
import Combine
import StreamVideoSwiftUI
import StreamVideoUIKit

final class HomeViewController: UIViewController {

    private lazy var callViewModel = CallViewModel()
    private var cancellables = Set<AnyCancellable>()

    private let callIdField: UITextField = {
        let tf = UITextField()
        tf.placeholder = "Call ID"
        tf.borderStyle = .roundedRect
        tf.autocorrectionType = .no
        tf.autocapitalizationType = .none
        tf.translatesAutoresizingMaskIntoConstraints = false
        return tf
    }()

    private let startButton: UIButton = {
        var config = UIButton.Configuration.borderedProminent()
        config.title = "Start / Join Call"
        let b = UIButton(configuration: config)
        b.translatesAutoresizingMaskIntoConstraints = false
        return b
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Video Call"
        view.backgroundColor = .systemBackground
        setupLayout()
        startButton.addTarget(self, action: #selector(startCall), for: .touchUpInside)
        observeCallState()
    }

    private func setupLayout() {
        let stack = UIStackView(arrangedSubviews: [callIdField, startButton])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24)
        ])
    }

    @objc private func startCall() {
        let callId = callIdField.text?.isEmpty == false ? callIdField.text! : UUID().uuidString
        let callVC = VideoCallViewController(viewModel: callViewModel)
        callVC.modalPresentationStyle = .fullScreen
        callVC.startCall(callType: "default", callId: callId, members: [])
        present(callVC, animated: true)
    }

    private func observeCallState() {
        callViewModel.$callingState
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                if case .incoming(_) = state, presentedViewController == nil {
                    // Present CallViewController so the SDK's accept/reject buttons
                    // are backed by a proper UIViewController and receive touches.
                    let callVC = VideoCallViewController(viewModel: callViewModel)
                    callVC.modalPresentationStyle = .fullScreen
                    present(callVC, animated: true)
                } else if state == .idle {
                    presentedViewController?.dismiss(animated: true)
                }
            }
            .store(in: &cancellables)
    }
}
```

**Wiring:**
- `callViewModel` is owned here as a stored property - one instance per call flow
- `CallViewController(viewModel:)` shares the same `CallViewModel`; never create a second one
- `startCall` with no `ring:` argument defaults to `false` - joins or creates the call without ringing
- The Combine sink dismisses `CallViewController` automatically when the call ends (`.idle`)
- `callIdField` left empty -> generates a fresh UUID, creating a new call room

---

## Ringing Call Blueprint

Start an outgoing ringing call to specific members.

```swift
@objc private func ringCall() {
    guard let callId = callIdField.text, !callId.isEmpty else { return }
    let members = [Member(userId: "alice"), Member(userId: "bob")]
    let callVC = VideoCallViewController(viewModel: callViewModel)
    callVC.modalPresentationStyle = .fullScreen
    callVC.startCall(callType: "default", callId: callId, members: members, ring: true)
    present(callVC, animated: true)
}
```

**Wiring:**
- `ring: true` sends push notifications to all members - requires APNs and Stream's push integration
- Always use a fresh call ID per ringing attempt - reusing an ID silently skips the ring
- Caller and callee must be different users
