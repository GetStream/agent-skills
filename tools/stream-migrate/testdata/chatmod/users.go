package main

import (
	"context"
	"log"

	stream "github.com/GetStream/stream-chat-go/v8"
)

// onboard creates the users the room needs and reads a couple of responses
// back, the way real code does.
func (a *app) onboard(ctx context.Context) error {
	resp, err := a.client.UpsertUser(ctx, &stream.User{
		ID:    "user-alice",
		Name:  "Alice",
		Role:  "user",
		Image: "https://example.com/alice.jpg",
		ExtraData: map[string]interface{}{
			"country": "NL",
		},
	})
	if err != nil {
		return err
	}
	log.Printf("upserted %s", resp.User.ID)

	if _, err := a.client.UpsertUsers(ctx,
		&stream.User{ID: "user-bob", Name: "Bob"},
		&stream.User{ID: "user-carol", Name: "Carol"},
	); err != nil {
		return err
	}

	admins, err := a.client.QueryUsers(ctx, &stream.QueryUsersOptions{
		QueryOption: stream.QueryOption{
			Filter: map[string]interface{}{"role": map[string]string{"$eq": "admin"}},
			Limit:  10,
		},
	})
	if err != nil {
		return err
	}
	log.Printf("found %d admins", len(admins.Users))

	if _, err := a.client.PartialUpdateUser(ctx, stream.PartialUserUpdate{
		ID:    "user-bob",
		Set:   map[string]interface{}{"name": "Bob Updated"},
		Unset: []string{"image"},
	}); err != nil {
		return err
	}
	return nil
}

// retire deactivates a user and then removes them entirely.
func (a *app) retire(ctx context.Context, userID string) error {
	if _, err := a.client.DeactivateUser(ctx, userID,
		stream.DeactivateUserWithMarkMessagesDeleted()); err != nil {
		return err
	}
	_, err := a.client.DeleteUser(ctx, userID,
		stream.DeleteUserWithHardDelete(),
		stream.DeleteUserWithMarkMessagesDeleted())
	return err
}
