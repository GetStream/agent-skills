package main

import (
	"bytes"
	"go/ast"
	"go/parser"
	"go/printer"
	"go/token"
	"strings"
	"testing"
)

// render prints a synthetic node and collapses whitespace, so expectations stay
// readable without depending on how the printer happens to wrap a line.
func render(t *testing.T, node ast.Node) string {
	t.Helper()
	var buf bytes.Buffer
	if err := printer.Fprint(&buf, token.NewFileSet(), node); err != nil {
		t.Fatalf("print: %v", err)
	}
	return strings.Join(strings.Fields(buf.String()), " ")
}

// rewrite runs the rule for a legacy call written as source, the way the engine
// does: the receiver is the expression the method is called on.
func rewrite(t *testing.T, src string) (string, bool) {
	t.Helper()
	expr, err := parser.ParseExpr(src)
	if err != nil {
		t.Fatalf("parse %q: %v", src, err)
	}
	call, ok := expr.(*ast.CallExpr)
	if !ok {
		t.Fatalf("%q is not a call", src)
	}
	sel := call.Fun.(*ast.SelectorExpr)
	r, ok := callRules[sel.Sel.Name]
	if !ok {
		t.Fatalf("no rule for %s", sel.Sel.Name)
	}
	if r.build == nil {
		t.Fatalf("%s has no builder", sel.Sel.Name)
	}
	out := r.build(sel.X, call)
	if out == nil {
		return "", false
	}
	return render(t, out), true
}

func TestRewrites(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want string
	}{
		{
			name: "upsert user becomes a keyed map and optional fields become pointers",
			in:   `client.UpsertUser(ctx, &stream.User{ID: "u1", Name: "Alice", ExtraData: map[string]interface{}{"country": "NL"}})`,
			want: `client.UpdateUsers(ctx, &getstream.UpdateUsersRequest{Users: map[string]getstream.UserRequest{"u1": {ID: "u1", Name: getstream.PtrTo("Alice"), Custom: map[string]interface{}{"country": "NL"}}}})`,
		},
		{
			name: "create channel moves to the chat sub-client and members become objects",
			in:   `client.CreateChannel(ctx, "messaging", "general", "u1", &stream.ChannelRequest{Members: []string{"u1", "u2"}})`,
			want: `client.Chat().Channel("messaging", "general").GetOrCreate(ctx, &getstream.GetOrCreateChannelRequest{Data: &getstream.ChannelInput{CreatedByID: getstream.PtrTo("u1"), Members: []getstream.ChannelMemberRequest{{UserID: "u1"}, {UserID: "u2"}}}})`,
		},
		{
			name: "send message folds the user id into the message",
			in:   `ch.SendMessage(ctx, &stream.Message{Text: "hi"}, "u1")`,
			want: `ch.SendMessage(ctx, &getstream.SendMessageRequest{Message: getstream.MessageRequest{Text: getstream.PtrTo("hi"), UserID: getstream.PtrTo("u1")}})`,
		},
		{
			name: "ban folds functional options into request fields",
			in:   `client.BanUser(ctx, "target", "mod", stream.BanWithReason("Spam"), stream.BanWithExpiration(60))`,
			want: `client.Moderation().Ban(ctx, &getstream.BanRequest{TargetUserID: "target", BannedByID: getstream.PtrTo("mod"), Reason: getstream.PtrTo("Spam"), Timeout: getstream.PtrTo(60)})`,
		},
		{
			name: "shadow ban is a ban with a flag rather than its own method",
			in:   `client.ShadowBan(ctx, "target", "mod")`,
			want: `client.Moderation().Ban(ctx, &getstream.BanRequest{TargetUserID: "target", BannedByID: getstream.PtrTo("mod"), Shadow: getstream.PtrTo(true)})`,
		},
		{
			name: "delete user becomes a batch call with string modes",
			in:   `client.DeleteUser(ctx, "u1", stream.DeleteUserWithHardDelete())`,
			want: `client.DeleteUsers(ctx, &getstream.DeleteUsersRequest{UserIds: []string{"u1"}, User: getstream.PtrTo("hard")})`,
		},
		{
			name: "add members becomes an update carrying member objects",
			in:   `ch.AddMembers(ctx, []string{"u1"})`,
			want: `ch.Update(ctx, &getstream.UpdateChannelRequest{AddMembers: []getstream.ChannelMemberRequest{{UserID: "u1"}}})`,
		},
		{
			name: "remove members keeps plain ids",
			in:   `ch.RemoveMembers(ctx, []string{"u1"}, nil)`,
			want: `ch.Update(ctx, &getstream.UpdateChannelRequest{RemoveMembers: []string{"u1"}})`,
		},
		{
			name: "variadic moderators become a slice on the update",
			in:   `ch.AddModerators(ctx, "u1", "u2")`,
			want: `ch.Update(ctx, &getstream.UpdateChannelRequest{AddModerators: []string{"u1", "u2"}})`,
		},
		{
			name: "push provider constants become plain strings",
			in:   `client.AddDevice(ctx, &stream.Device{ID: "tok", UserID: "u1", PushProvider: stream.PushProviderFirebase})`,
			want: `client.CreateDevice(ctx, &getstream.CreateDeviceRequest{ID: "tok", UserID: getstream.PtrTo("u1"), PushProvider: "firebase"})`,
		},
		{
			name: "blocklist keeps its data but gains the capital L spelling",
			in:   `client.CreateBlocklist(ctx, &stream.BlocklistCreateRequest{BlocklistBase: stream.BlocklistBase{Name: "profanity", Words: []string{"bad"}}})`,
			want: `client.CreateBlockList(ctx, &getstream.CreateBlockListRequest{Name: "profanity", Words: []string{"bad"}})`,
		},
		{
			name: "blocking a user moves the ids onto a request",
			in:   `client.BlockUser(ctx, "target", "actor")`,
			want: `client.BlockUsers(ctx, &getstream.BlockUsersRequest{BlockedUserID: "target", UserID: getstream.PtrTo("actor")})`,
		},
		{
			name: "flagging a message describes the entity instead of naming a method",
			in:   `client.FlagMessage(ctx, "m1", "actor")`,
			want: `client.Moderation().Flag(ctx, &getstream.FlagRequest{EntityType: "message", EntityID: "m1", UserID: getstream.PtrTo("actor")})`,
		},
		{
			name: "query filters move under the generated payload",
			in:   `client.QueryUsers(ctx, &stream.QueryUsersOptions{QueryOption: stream.QueryOption{Filter: map[string]interface{}{"role": "admin"}, Limit: 10}})`,
			want: `client.QueryUsers(ctx, &getstream.QueryUsersRequest{Payload: &getstream.QueryUsersPayload{FilterConditions: map[string]interface{}{"role": "admin"}, Limit: getstream.PtrTo(10)}})`,
		},
		{
			name: "a call that took no options gains an empty request",
			in:   `client.GetMessage(ctx, "m1")`,
			want: `client.Chat().GetMessage(ctx, "m1", &getstream.GetMessageRequest{})`,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := rewrite(t, tc.in)
			if !ok {
				t.Fatalf("rule declined to rewrite %q", tc.in)
			}
			if got != tc.want {
				t.Errorf("\n in:   %s\n got:  %s\n want: %s", tc.in, got, tc.want)
			}
		})
	}
}

// TestUnexpectedShapesDegrade is the safety property that matters most: when a
// call is not shaped the way a rule expects, the rule must decline so the call
// is reported for a human, rather than emit a rewrite that compiles but means
// something else.
func TestUnexpectedShapesDegrade(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{"user built elsewhere, so no fields to map", `client.UpsertUser(ctx, existingUser)`},
		{"members built elsewhere", `client.CreateChannel(ctx, "messaging", "general", "u1", &stream.ChannelRequest{Members: memberIDs})`},
		{"an unrecognized ban option", `client.BanUser(ctx, "t", "m", stream.BanWithSomethingNew(1))`},
		{"an unrecognized delete option", `client.DeleteUser(ctx, "u1", stream.DeleteUserWithSomethingNew())`},
		{"channel-scoped unban needs a channel cid", `client.UnBanUser(ctx, "u1", stream.UnbanWithChannel("messaging", "general"))`},
		{"a device built elsewhere", `client.AddDevice(ctx, existingDevice)`},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got, ok := rewrite(t, tc.in); ok {
				t.Errorf("expected %q to be left for a human, but it was rewritten to: %s", tc.in, got)
			}
		})
	}
}

// TestResponseReadsMoveUnderData covers the pass that follows a rewrite: the
// generated calls return an envelope, so reads have to move down one level.
func TestResponseReadsMoveUnderData(t *testing.T) {
	src := `package p

func f() {
	resp, _ := client.UpsertUser(ctx, u)
	_ = resp.User.ID
	ch, _ := client.Channel("messaging", "general")
	_ = ch.ID
}
`
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, "p.go", src, 0)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	// Only resp holds a response; ch holds an SDK object and must be left alone.
	if n := migrateResponseFields(file, map[string]bool{"resp": true}); n != 1 {
		t.Fatalf("moved %d reads, want 1", n)
	}
	out := render(t, file)
	if !strings.Contains(out, "resp.Data.User.ID") {
		t.Errorf("response read was not moved under Data: %s", out)
	}
	if strings.Contains(out, "ch.Data") {
		t.Errorf("a read off an SDK object was wrongly moved under Data: %s", out)
	}
}
