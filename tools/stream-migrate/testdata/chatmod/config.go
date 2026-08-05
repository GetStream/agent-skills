package main

import (
	"context"
	"log"

	stream "github.com/GetStream/stream-chat-go/v8"
)

// configureBlocklists manages the app's word blocklists.
func (a *app) configureBlocklists(ctx context.Context) error {
	if _, err := a.client.CreateBlocklist(ctx, &stream.BlocklistCreateRequest{
		BlocklistBase: stream.BlocklistBase{
			Name:  "profanity",
			Words: []string{"badword"},
		},
	}); err != nil {
		return err
	}

	list, err := a.client.GetBlocklist(ctx, "profanity")
	if err != nil {
		return err
	}
	log.Printf("blocklist %s has %d words", list.Blocklist.Name, len(list.Blocklist.Words))

	if _, err := a.client.UpdateBlocklist(ctx, "profanity", []string{"badword", "worse"}); err != nil {
		return err
	}

	all, err := a.client.ListBlocklists(ctx)
	if err != nil {
		return err
	}
	log.Printf("%d blocklists", len(all.Blocklists))

	_, err = a.client.DeleteBlocklist(ctx, "profanity")
	return err
}

// registerDevices manages push devices for a user.
func (a *app) registerDevices(ctx context.Context) error {
	if _, err := a.client.AddDevice(ctx, &stream.Device{
		ID:           "device-token-123",
		UserID:       "user-alice",
		PushProvider: stream.PushProviderFirebase,
	}); err != nil {
		return err
	}

	devices, err := a.client.GetDevices(ctx, "user-alice")
	if err != nil {
		return err
	}
	log.Printf("%d devices", len(devices.Devices))

	_, err = a.client.DeleteDevice(ctx, "user-alice", "device-token-123")
	return err
}
