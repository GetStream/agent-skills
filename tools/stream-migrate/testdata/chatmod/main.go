// Command chatmod is a representative server-side Stream Chat + Moderation
// integration written against the legacy stream-chat-go SDK. It exists to
// exercise the migration on something shaped like real customer code:
// several files, responses actually consumed, and a spread of operations
// rather than a happy-path sample.
package main

import (
	"context"
	"log"
	"time"

	stream "github.com/GetStream/stream-chat-go/v8"
)

type app struct {
	client *stream.Client
}

func main() {
	client, err := stream.NewClientFromEnvVars()
	if err != nil {
		log.Fatalf("stream: %v", err)
	}
	a := &app{client: client}
	ctx := context.Background()

	token, err := a.issueToken("user-alice")
	if err != nil {
		log.Fatalf("token: %v", err)
	}
	log.Printf("issued token of length %d", len(token))

	if err := a.onboard(ctx); err != nil {
		log.Fatalf("onboard: %v", err)
	}
	if err := a.runRoom(ctx); err != nil {
		log.Fatalf("room: %v", err)
	}
	if err := a.moderate(ctx); err != nil {
		log.Fatalf("moderate: %v", err)
	}
	if err := a.configureBlocklists(ctx); err != nil {
		log.Fatalf("blocklists: %v", err)
	}
	if err := a.registerDevices(ctx); err != nil {
		log.Fatalf("devices: %v", err)
	}
}

// issueToken mints a token valid for a day.
func (a *app) issueToken(userID string) (string, error) {
	return a.client.CreateToken(userID, time.Now().Add(24*time.Hour))
}
