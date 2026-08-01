package main

import (
	"context"
	"log"

	stream "github.com/GetStream/stream-chat-go/v8"
)

// moderate covers the moderation surface: moderators, bans, mutes, flags and
// per-user blocking.
func (a *app) moderate(ctx context.Context) error {
	ch := a.client.Channel("messaging", "general")

	if _, err := ch.AddModerators(ctx, "user-alice"); err != nil {
		return err
	}
	if _, err := ch.DemoteModerators(ctx, "user-alice"); err != nil {
		return err
	}

	if _, err := a.client.BanUser(ctx, "user-bob", "user-alice",
		stream.BanWithReason("Spam"),
		stream.BanWithExpiration(60)); err != nil {
		return err
	}
	if _, err := a.client.UnBanUser(ctx, "user-bob"); err != nil {
		return err
	}
	if _, err := a.client.ShadowBan(ctx, "user-carol", "user-alice"); err != nil {
		return err
	}

	if _, err := a.client.MuteUser(ctx, "user-carol", "user-alice",
		stream.MuteWithExpiration(60)); err != nil {
		return err
	}
	if _, err := a.client.UnmuteUser(ctx, "user-carol", "user-alice"); err != nil {
		return err
	}

	banned, err := a.client.QueryBannedUsers(ctx, &stream.QueryBannedUsersOptions{
		QueryOption: &stream.QueryOption{
			Filter: map[string]interface{}{"channel_cid": "messaging:general"},
			Limit:  10,
		},
	})
	if err != nil {
		return err
	}
	log.Printf("%d bans", len(banned.Bans))

	return a.handleReports(ctx)
}

// handleReports is the flag and review workflow.
func (a *app) handleReports(ctx context.Context) error {
	if _, err := a.client.FlagMessage(ctx, "message-id", "user-alice"); err != nil {
		return err
	}
	if _, err := a.client.FlagUser(ctx, "user-carol", "user-alice"); err != nil {
		return err
	}

	flags, err := a.client.QueryMessageFlags(ctx, &stream.QueryOption{
		Filter: map[string]interface{}{"channel_cid": "messaging:general"},
	})
	if err != nil {
		return err
	}
	log.Printf("%d message flags", len(flags.Flags))

	reports, err := a.client.QueryFlagReports(ctx, &stream.QueryFlagReportsRequest{})
	if err != nil {
		return err
	}
	for _, report := range reports.FlagReports {
		if _, err := a.client.ReviewFlagReport(ctx, report.ID, &stream.ReviewFlagReportRequest{
			ReviewResult: "reviewed",
		}); err != nil {
			return err
		}
	}
	return nil
}

// blockPeer is the per-user block list, which is separate from banning.
func (a *app) blockPeer(ctx context.Context) error {
	if _, err := a.client.BlockUser(ctx, "user-carol", "user-alice"); err != nil {
		return err
	}
	blocked, err := a.client.GetBlockedUser(ctx, "user-alice")
	if err != nil {
		return err
	}
	log.Printf("%d blocked users", len(blocked.BlockedUsers))

	_, err = a.client.UnblockUser(ctx, "user-carol", "user-alice")
	return err
}
