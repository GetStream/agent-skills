package main

import (
	"context"
	"log"

	stream "github.com/GetStream/stream-chat-go/v8"
)

// runRoom covers the channel and messaging surface a chat backend touches on
// a normal day.
func (a *app) runRoom(ctx context.Context) error {
	created, err := a.client.CreateChannel(ctx, "messaging", "general", "user-alice",
		&stream.ChannelRequest{
			Members: []string{"user-alice", "user-bob"},
		})
	if err != nil {
		return err
	}
	log.Printf("channel %s ready", created.Channel.ID)

	ch := a.client.Channel("messaging", "general")

	if _, err := ch.AddMembers(ctx, []string{"user-carol"}); err != nil {
		return err
	}
	if _, err := ch.RemoveMembers(ctx, []string{"user-carol"}, nil); err != nil {
		return err
	}

	if _, err := ch.PartialUpdate(ctx, stream.PartialUpdate{
		Set:   map[string]interface{}{"name": "General"},
		Unset: []string{"description"},
	}); err != nil {
		return err
	}

	sent, err := ch.SendMessage(ctx, &stream.Message{Text: "Hello world"}, "user-alice")
	if err != nil {
		return err
	}
	messageID := sent.Message.ID

	if _, err := ch.SendMessage(ctx, &stream.Message{
		Text:     "Replying in a thread",
		ParentID: messageID,
	}, "user-bob"); err != nil {
		return err
	}

	fetched, err := a.client.GetMessage(ctx, messageID)
	if err != nil {
		return err
	}
	log.Printf("message text is %q", fetched.Message.Text)

	if _, err := a.client.UpdateMessage(ctx, &stream.Message{Text: "Hello, world"}, messageID); err != nil {
		return err
	}
	if _, err := a.client.PartialUpdateMessage(ctx, messageID, &stream.MessagePartialUpdateRequest{
		PartialUpdate: stream.PartialUpdate{
			Set: map[string]interface{}{"pinned": true},
		},
		UserID: "user-alice",
	}); err != nil {
		return err
	}

	if _, err := a.client.SendReaction(ctx, &stream.Reaction{Type: "like"}, messageID, "user-bob"); err != nil {
		return err
	}
	reactions, err := a.client.GetReactions(ctx, messageID, map[string][]string{"limit": {"10"}})
	if err != nil {
		return err
	}
	log.Printf("%d reactions", len(reactions.Reactions))

	if _, err := a.client.DeleteReaction(ctx, messageID, "like", "user-bob"); err != nil {
		return err
	}
	if _, err := a.client.DeleteMessage(ctx, messageID); err != nil {
		return err
	}

	rooms, err := a.client.QueryChannels(ctx, &stream.QueryOption{
		Filter: map[string]interface{}{"members": map[string]interface{}{"$in": []string{"user-alice"}}},
		Limit:  10,
	})
	if err != nil {
		return err
	}
	log.Printf("%d channels", len(rooms.Channels))
	return nil
}

// archive tears a room down.
func (a *app) archive(ctx context.Context) error {
	ch := a.client.Channel("messaging", "general")
	if _, err := ch.Truncate(ctx); err != nil {
		return err
	}
	_, err := ch.Delete(ctx)
	return err
}
