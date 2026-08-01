// A representative legacy Chat + Moderation integration, used to exercise the
// migration end to end. Lives under testdata so the repo's own build ignores it.
module chatmod

go 1.23

require github.com/GetStream/stream-chat-go/v8 v8.5.0

require github.com/golang-jwt/jwt/v4 v4.5.1 // indirect
