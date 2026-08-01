package main

import (
	"go/ast"
	"go/token"
	"strconv"
)

// rule describes how one legacy operation maps onto the generated SDK.
//
// Exactly one of review or build is meaningful. A rule with review set is
// reported for a human to finish, because the mapping needs a judgment the
// tool cannot make. behavior is set when the rewrite is correct but runtime
// behavior differs, which the customer has to know even though it compiles.
//
// A build func returns nil when the call does not match the shape it expects.
// That degrades the call to "needs a decision" instead of emitting a rewrite
// that happens to compile but means something else.
type rule struct {
	review   string
	behavior string
	// object marks a call that returns an SDK object rather than a response
	// envelope, so reads off its result must not be moved under Data.
	object bool
	build  func(recv ast.Expr, c *ast.CallExpr) ast.Expr
}

const (
	behaviorEnvVars = "reads STREAM_API_KEY and STREAM_API_SECRET instead of STREAM_KEY and STREAM_SECRET; update the deployment environment or the client will not authenticate"
	behaviorAsync   = "was synchronous; now a batch call that returns a task ID and completes asynchronously, so code that assumed the work was done on return has to poll the task"
	behaviorFlagV2  = "the legacy call wrote the v1 chat flags store while this writes v2 moderation; flags written here may not be visible to QueryMessageFlags, so migrate flagging, querying and review together"
)

// typeRewrites maps legacy type names that appear in declarations (struct
// fields, parameters, variables) onto their generated equivalents. Only
// unambiguous types belong here: stream.User, for example, splits into request
// and response types in the generated SDK, so it is reported rather than
// guessed at.
var typeRewrites = map[string]string{
	"Client":  "Stream",
	"Channel": "Channels",
}

var callRules = map[string]rule{
	// Setup and authentication.
	"NewClient": {build: func(_ ast.Expr, c *ast.CallExpr) ast.Expr { return gsCall("NewClient", c.Args...) }},
	"NewClientFromEnvVars": {
		behavior: behaviorEnvVars,
		build:    func(_ ast.Expr, c *ast.CallExpr) ast.Expr { return gsCall("NewClientFromEnvVars", c.Args...) },
	},
	"CreateToken": {review: "the expiry argument changed from an absolute time.Time to a WithExpiration(duration) option, so the value has to be recomputed as a duration"},

	// Users.
	"UpsertUser":        {build: buildUpsertUser},
	"UpsertUsers":       {build: buildUpsertUsers},
	"QueryUsers":        {build: buildQueryUsers},
	"PartialUpdateUser": {build: buildPartialUpdateUser},
	"DeactivateUser":    {build: buildDeactivateUser},
	"DeleteUser":        {behavior: behaviorAsync, build: buildDeleteUser},

	// Channels.
	"Channel": {object: true, build: func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		return call(sel(sub(recv, "Chat"), "Channel"), c.Args...)
	}},
	"CreateChannel":    {build: buildCreateChannel},
	"QueryChannels":    {build: buildQueryChannels},
	"DeleteChannels":   {behavior: behaviorAsync, build: moveTo("Chat", "DeleteChannels", reqOf("DeleteChannelsRequest", "Cids", "HardDelete"))},
	"PartialUpdate":    {build: buildChannelPartialUpdate},
	"AddMembers":       {build: memberUpdate("AddMembers", true)},
	"RemoveMembers":    {build: memberUpdate("RemoveMembers", false)},
	"AddModerators":    {build: variadicUpdate("AddModerators")},
	"DemoteModerators": {build: variadicUpdate("DemoteModerators")},
	"QueryMembers":     {review: "the channel type and id move from the channel object onto QueryMembersPayload, so the call has to be rebuilt against client.Chat().QueryMembers"},
	"Truncate":         {build: appendReq("TruncateChannelRequest", 1)},
	"MarkRead":         {review: "marking read moved to the Chat sub-client and takes a request struct; confirm the shape in the guide"},

	// Messages and reactions.
	"SendMessage":          {build: buildSendMessage},
	"GetMessage":           {build: moveTo("Chat", "GetMessage", appendEmpty("GetMessageRequest", 2))},
	"UpdateMessage":        {build: buildUpdateMessage},
	"PartialUpdateMessage": {build: buildPartialUpdateMessage},
	"DeleteMessage":        {build: moveTo("Chat", "DeleteMessage", appendEmpty("DeleteMessageRequest", 2))},
	"SendReaction":         {build: buildSendReaction},
	"GetReactions":         {build: moveTo("Chat", "GetReactions", appendEmpty("GetReactionsRequest", 2))},
	"DeleteReaction":       {build: buildDeleteReaction},

	// Moderation.
	"BanUser":          {build: buildBan},
	"UnBanUser":        {build: buildUnban},
	"ShadowBan":        {build: buildShadowBan},
	"MuteUser":         {build: buildMute("Mute", "MuteRequest")},
	"UnmuteUser":       {build: buildMute("Unmute", "UnmuteRequest")},
	"QueryBannedUsers": {review: "the filter moves under QueryBannedUsersRequest.Payload on the Chat sub-client"},

	// User blocking.
	"BlockUser":      {build: buildBlockUser("BlockUsers")},
	"UnblockUser":    {build: buildBlockUser("UnblockUsers")},
	"GetBlockedUser": {build: buildGetBlockedUsers},

	// Blocklists. Note the spelling change: Blocklist becomes BlockList.
	"CreateBlocklist": {build: buildCreateBlockList},
	"GetBlocklist":    {build: appendReqNamed("GetBlockList", "GetBlockListRequest")},
	"UpdateBlocklist": {build: buildUpdateBlockList},
	"ListBlocklists":  {build: buildListBlockLists},
	"DeleteBlocklist": {build: appendReqNamed("DeleteBlockList", "DeleteBlockListRequest")},

	// Flags and review.
	"FlagMessage":       {behavior: behaviorFlagV2, build: buildFlag("message")},
	"FlagUser":          {behavior: behaviorFlagV2, build: buildFlag("user")},
	"QueryMessageFlags": {review: "the filter moves under QueryMessageFlagsRequest.Payload on the Chat sub-client"},
	"QueryFlagReports":  {review: "flag reports were replaced by the v2 review queue; rebuild this against Moderation().QueryReviewQueue"},
	"ReviewFlagReport":  {review: "reviewing is now an action submitted against a review-queue item via Moderation().SubmitAction; this is a workflow change, not a rename"},

	// Devices.
	"AddDevice":    {build: buildAddDevice},
	"GetDevices":   {build: buildListDevices},
	"DeleteDevice": {build: buildDeleteDevice},
}

// ---------- rule helpers ----------

// moveTo calls the method on a sub-client, transforming the argument list.
func moveTo(subClient, to string, args func(*ast.CallExpr) []ast.Expr) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		a := args(c)
		if a == nil {
			return nil
		}
		return call(sel(sub(recv, subClient), to), a...)
	}
}

// appendEmpty keeps the first n arguments and appends an empty request struct,
// which is the shape of the generated calls that took no options before.
func appendEmpty(reqType string, n int) func(*ast.CallExpr) []ast.Expr {
	return func(c *ast.CallExpr) []ast.Expr {
		if len(c.Args) < n {
			return nil
		}
		return append(append([]ast.Expr{}, c.Args[:n]...), addr(lit(gs(reqType))))
	}
}

// reqOf maps the remaining positional arguments onto named request fields.
func reqOf(reqType string, fields ...string) func(*ast.CallExpr) []ast.Expr {
	return func(c *ast.CallExpr) []ast.Expr {
		rest := c.Args[1:]
		if len(rest) > len(fields) {
			return nil
		}
		var elts []ast.Expr
		for i, arg := range rest {
			v := arg
			if isBoolLit(arg) {
				v = ptr(arg)
			}
			elts = append(elts, kv(fields[i], v))
		}
		return []ast.Expr{c.Args[0], addr(lit(gs(reqType), elts...))}
	}
}

// appendReq keeps n args on the same receiver and appends an empty request.
func appendReq(reqType string, n int) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) < n {
			return nil
		}
		args := append(append([]ast.Expr{}, c.Args[:n]...), addr(lit(gs(reqType))))
		return call(sel(recv, "Truncate"), args...)
	}
}

// appendReqNamed renames a client method and appends an empty request struct.
func appendReqNamed(to, reqType string) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) < 2 {
			return nil
		}
		return call(sel(recv, to), c.Args[0], c.Args[1], addr(lit(gs(reqType))))
	}
}

// ---------- users ----------

func buildUpsertUser(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	idExpr, ok := f["ID"]
	if !ok {
		return nil
	}
	entry := &ast.KeyValueExpr{Key: idExpr, Value: lit(nil, userRequestFields(f)...)}
	users := lit(mapType("string", gs("UserRequest")), entry)
	return call(sel(recv, "UpdateUsers"), c.Args[0], addr(lit(gs("UpdateUsersRequest"), kv("Users", users))))
}

func buildUpsertUsers(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 2 {
		return nil
	}
	var entries []ast.Expr
	for _, arg := range c.Args[1:] {
		f := fieldsOf(arg)
		idExpr, ok := f["ID"]
		if !ok {
			return nil
		}
		entries = append(entries, &ast.KeyValueExpr{Key: idExpr, Value: lit(nil, userRequestFields(f)...)})
	}
	users := lit(mapType("string", gs("UserRequest")), entries...)
	return call(sel(recv, "UpdateUsers"), c.Args[0], addr(lit(gs("UpdateUsersRequest"), kv("Users", users))))
}

// userRequestFields converts a legacy stream.User literal into UserRequest fields.
func userRequestFields(f map[string]ast.Expr) []ast.Expr {
	var elts []ast.Expr
	if v, ok := f["ID"]; ok {
		elts = append(elts, kv("ID", v))
	}
	for _, name := range []string{"Name", "Image", "Role", "Language"} {
		optPtr(&elts, name, f, name)
	}
	if v, ok := f["Teams"]; ok {
		elts = append(elts, kv("Teams", v))
	}
	if v, ok := f["ExtraData"]; ok {
		elts = append(elts, kv("Custom", v))
	}
	return elts
}

func buildQueryUsers(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	q := queryFields(c.Args[1])
	if q == nil {
		return nil
	}
	payload := addr(lit(gs("QueryUsersPayload"), q...))
	return call(sel(recv, "QueryUsers"), c.Args[0], addr(lit(gs("QueryUsersRequest"), kv("Payload", payload))))
}

func buildPartialUpdateUser(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	var elts []ast.Expr
	for _, name := range []string{"ID", "Set", "Unset"} {
		if v, ok := f[name]; ok {
			elts = append(elts, kv(name, v))
		}
	}
	users := lit(&ast.ArrayType{Elt: gs("UpdateUserPartialRequest")}, lit(nil, elts...))
	return call(sel(recv, "UpdateUsersPartial"), c.Args[0],
		addr(lit(gs("UpdateUsersPartialRequest"), kv("Users", users))))
}

func buildDeactivateUser(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 2 {
		return nil
	}
	var elts []ast.Expr
	for _, opt := range c.Args[2:] {
		name, _, ok := optionCall(opt)
		if !ok {
			return nil
		}
		if name == "DeactivateUserWithMarkMessagesDeleted" {
			elts = append(elts, kv("MarkMessagesDeleted", ptr(boolLit(true))))
			continue
		}
		return nil
	}
	return call(sel(recv, "DeactivateUser"), c.Args[0], c.Args[1], addr(lit(gs("DeactivateUserRequest"), elts...)))
}

func buildDeleteUser(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 2 {
		return nil
	}
	elts := []ast.Expr{kv("UserIds", lit(&ast.ArrayType{Elt: id("string")}, c.Args[1]))}
	for _, opt := range c.Args[2:] {
		name, _, ok := optionCall(opt)
		if !ok {
			return nil
		}
		switch name {
		case "DeleteUserWithHardDelete":
			elts = append(elts, kv("User", ptr(strLit("hard"))))
		case "DeleteUserWithMarkMessagesDeleted":
			elts = append(elts, kv("Messages", ptr(strLit("hard"))))
		default:
			return nil
		}
	}
	return call(sel(recv, "DeleteUsers"), c.Args[0], addr(lit(gs("DeleteUsersRequest"), elts...)))
}

// ---------- channels ----------

func buildCreateChannel(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 5 {
		return nil
	}
	ctx, ctype, cid, creator := c.Args[0], c.Args[1], c.Args[2], c.Args[3]
	data := []ast.Expr{kv("CreatedByID", ptr(creator))}
	if members := membersOf(fieldsOf(c.Args[4])["Members"]); members != nil {
		data = append(data, kv("Members", members))
	}
	req := addr(lit(gs("GetOrCreateChannelRequest"), kv("Data", addr(lit(gs("ChannelInput"), data...)))))
	channel := call(sel(sub(recv, "Chat"), "Channel"), ctype, cid)
	return call(sel(channel, "GetOrCreate"), ctx, req)
}

func buildQueryChannels(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	q := queryFields(c.Args[1])
	if q == nil {
		return nil
	}
	return call(sel(sub(recv, "Chat"), "QueryChannels"), c.Args[0], addr(lit(gs("QueryChannelsRequest"), q...)))
}

func buildChannelPartialUpdate(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	var elts []ast.Expr
	for _, name := range []string{"Set", "Unset"} {
		if v, ok := f[name]; ok {
			elts = append(elts, kv(name, v))
		}
	}
	return call(sel(recv, "UpdateChannelPartial"), c.Args[0], addr(lit(gs("UpdateChannelPartialRequest"), elts...)))
}

// memberUpdate rewrites AddMembers/RemoveMembers onto ch.Update. Added members
// become ChannelMemberRequest values; removed members stay a slice of ids.
func memberUpdate(field string, asObjects bool) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) < 2 {
			return nil
		}
		value := c.Args[1]
		if asObjects {
			members := membersOf(value)
			if members == nil {
				return nil
			}
			value = members
		}
		return call(sel(recv, "Update"), c.Args[0], addr(lit(gs("UpdateChannelRequest"), kv(field, value))))
	}
}

// variadicUpdate rewrites AddModerators(ctx, ids...) onto ch.Update.
func variadicUpdate(field string) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) < 2 {
			return nil
		}
		var value ast.Expr
		if len(c.Args) == 2 && !isStringLit(c.Args[1]) {
			value = c.Args[1] // already a slice
		} else {
			value = lit(&ast.ArrayType{Elt: id("string")}, c.Args[1:]...)
		}
		return call(sel(recv, "Update"), c.Args[0], addr(lit(gs("UpdateChannelRequest"), kv(field, value))))
	}
}

// membersOf turns a []string of user ids into []ChannelMemberRequest.
func membersOf(e ast.Expr) ast.Expr {
	cl, ok := e.(*ast.CompositeLit)
	if !ok {
		return nil
	}
	var out []ast.Expr
	for _, el := range cl.Elts {
		out = append(out, lit(nil, kv("UserID", el)))
	}
	return lit(&ast.ArrayType{Elt: gs("ChannelMemberRequest")}, out...)
}

// ---------- messages ----------

func buildSendMessage(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 3 {
		return nil
	}
	msg := messageRequest(fieldsOf(c.Args[1]), c.Args[2])
	if msg == nil {
		return nil
	}
	return call(sel(recv, "SendMessage"), c.Args[0], addr(lit(gs("SendMessageRequest"), kv("Message", msg))))
}

func buildUpdateMessage(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 3 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	msg := messageRequest(f, nil)
	if msg == nil {
		return nil
	}
	return call(sel(sub(recv, "Chat"), "UpdateMessage"), c.Args[0], c.Args[2],
		addr(lit(gs("UpdateMessageRequest"), kv("Message", msg))))
}

func buildPartialUpdateMessage(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 3 {
		return nil
	}
	f := fieldsOf(c.Args[2])
	inner := f
	if nested, ok := f["PartialUpdate"]; ok {
		inner = fieldsOf(nested)
	}
	var elts []ast.Expr
	for _, name := range []string{"Set", "Unset"} {
		if v, ok := inner[name]; ok {
			elts = append(elts, kv(name, v))
		}
	}
	optPtr(&elts, "UserID", f, "UserID")
	return call(sel(sub(recv, "Chat"), "UpdateMessagePartial"), c.Args[0], c.Args[1],
		addr(lit(gs("UpdateMessagePartialRequest"), elts...)))
}

// messageRequest builds a MessageRequest from a legacy stream.Message literal,
// optionally folding in the user id that used to be a separate argument.
func messageRequest(f map[string]ast.Expr, userID ast.Expr) ast.Expr {
	if f == nil {
		return nil
	}
	var elts []ast.Expr
	for _, name := range []string{"Text", "ParentID", "HTML", "MML", "QuotedMessageID"} {
		optPtr(&elts, name, f, name)
	}
	if v, ok := f["ShowInChannel"]; ok {
		elts = append(elts, kv("ShowInChannel", ptr(v)))
	}
	if v, ok := f["Attachments"]; ok {
		elts = append(elts, kv("Attachments", v))
	}
	if v, ok := f["ExtraData"]; ok {
		elts = append(elts, kv("Custom", v))
	}
	if userID != nil {
		elts = append(elts, kv("UserID", ptr(userID)))
	}
	return lit(gs("MessageRequest"), elts...)
}

func buildSendReaction(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 4 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	typ, ok := f["Type"]
	if !ok {
		return nil
	}
	elts := []ast.Expr{kv("Type", typ), kv("UserID", ptr(c.Args[3]))}
	if v, ok := f["ExtraData"]; ok {
		elts = append(elts, kv("Custom", v))
	}
	req := addr(lit(gs("SendReactionRequest"), kv("Reaction", lit(gs("ReactionRequest"), elts...))))
	return call(sel(sub(recv, "Chat"), "SendReaction"), c.Args[0], c.Args[2], req)
}

func buildDeleteReaction(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 4 {
		return nil
	}
	req := addr(lit(gs("DeleteReactionRequest"), kv("UserID", ptr(c.Args[3]))))
	return call(sel(sub(recv, "Chat"), "DeleteReaction"), c.Args[0], c.Args[1], c.Args[2], req)
}

// ---------- moderation ----------

var banOptionFields = map[string]string{
	"BanWithReason":     "Reason",
	"BanWithExpiration": "Timeout",
	"BanWithIPBan":      "IpBan",
}

func buildBan(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 3 {
		return nil
	}
	elts := []ast.Expr{kv("TargetUserID", c.Args[1]), kv("BannedByID", ptr(c.Args[2]))}
	rest, ok := banOptions(c.Args[3:])
	if !ok {
		return nil
	}
	elts = append(elts, rest...)
	return call(sel(sub(recv, "Moderation"), "Ban"), c.Args[0], addr(lit(gs("BanRequest"), elts...)))
}

func buildShadowBan(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 3 {
		return nil
	}
	elts := []ast.Expr{
		kv("TargetUserID", c.Args[1]),
		kv("BannedByID", ptr(c.Args[2])),
		kv("Shadow", ptr(boolLit(true))),
	}
	rest, ok := banOptions(c.Args[3:])
	if !ok {
		return nil
	}
	elts = append(elts, rest...)
	return call(sel(sub(recv, "Moderation"), "Ban"), c.Args[0], addr(lit(gs("BanRequest"), elts...)))
}

func buildUnban(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) < 2 {
		return nil
	}
	if len(c.Args) > 2 {
		return nil // channel-scoped options need a ChannelCid, decide by hand
	}
	req := addr(lit(gs("UnbanRequest"), kv("TargetUserID", c.Args[1])))
	return call(sel(sub(recv, "Moderation"), "Unban"), c.Args[0], req)
}

func banOptions(args []ast.Expr) ([]ast.Expr, bool) {
	var elts []ast.Expr
	for _, opt := range args {
		name, optArgs, ok := optionCall(opt)
		if !ok {
			return nil, false
		}
		field, known := banOptionFields[name]
		if !known || len(optArgs) != 1 {
			return nil, false
		}
		elts = append(elts, kv(field, ptr(optArgs[0])))
	}
	return elts, true
}

func buildMute(to, reqType string) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) < 3 {
			return nil
		}
		elts := []ast.Expr{
			kv("TargetIds", lit(&ast.ArrayType{Elt: id("string")}, c.Args[1])),
			kv("UserID", ptr(c.Args[2])),
		}
		for _, opt := range c.Args[3:] {
			name, optArgs, ok := optionCall(opt)
			if !ok || name != "MuteWithExpiration" || len(optArgs) != 1 {
				return nil
			}
			elts = append(elts, kv("Timeout", ptr(optArgs[0])))
		}
		return call(sel(sub(recv, "Moderation"), to), c.Args[0], addr(lit(gs(reqType), elts...)))
	}
}

func buildFlag(entity string) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) != 3 {
			return nil
		}
		req := addr(lit(gs("FlagRequest"),
			kv("EntityType", strLit(entity)),
			kv("EntityID", c.Args[1]),
			kv("UserID", ptr(c.Args[2])),
		))
		return call(sel(sub(recv, "Moderation"), "Flag"), c.Args[0], req)
	}
}

// ---------- user blocking and blocklists ----------

func buildBlockUser(to string) func(ast.Expr, *ast.CallExpr) ast.Expr {
	return func(recv ast.Expr, c *ast.CallExpr) ast.Expr {
		if len(c.Args) != 3 {
			return nil
		}
		req := addr(lit(gs(to+"Request"), kv("BlockedUserID", c.Args[1]), kv("UserID", ptr(c.Args[2]))))
		return call(sel(recv, to), c.Args[0], req)
	}
}

func buildGetBlockedUsers(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	req := addr(lit(gs("GetBlockedUsersRequest"), kv("UserID", ptr(c.Args[1]))))
	return call(sel(recv, "GetBlockedUsers"), c.Args[0], req)
}

func buildCreateBlockList(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	if base, ok := f["BlocklistBase"]; ok {
		f = fieldsOf(base)
	}
	var elts []ast.Expr
	for _, name := range []string{"Name", "Words"} {
		v, ok := f[name]
		if !ok {
			return nil
		}
		elts = append(elts, kv(name, v))
	}
	if v, ok := f["Type"]; ok {
		elts = append(elts, kv("Type", ptr(v)))
	}
	return call(sel(recv, "CreateBlockList"), c.Args[0], addr(lit(gs("CreateBlockListRequest"), elts...)))
}

func buildUpdateBlockList(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 3 {
		return nil
	}
	req := addr(lit(gs("UpdateBlockListRequest"), kv("Words", c.Args[2])))
	return call(sel(recv, "UpdateBlockList"), c.Args[0], c.Args[1], req)
}

func buildListBlockLists(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 1 {
		return nil
	}
	return call(sel(recv, "ListBlockLists"), c.Args[0], addr(lit(gs("ListBlockListsRequest"))))
}

// ---------- devices ----------

func buildAddDevice(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	f := fieldsOf(c.Args[1])
	idExpr, ok := f["ID"]
	if !ok {
		return nil
	}
	elts := []ast.Expr{kv("ID", idExpr)}
	optPtr(&elts, "UserID", f, "UserID")
	if v, ok := f["PushProvider"]; ok {
		elts = append(elts, kv("PushProvider", pushProvider(v)))
	}
	return call(sel(recv, "CreateDevice"), c.Args[0], addr(lit(gs("CreateDeviceRequest"), elts...)))
}

func buildListDevices(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 2 {
		return nil
	}
	req := addr(lit(gs("ListDevicesRequest"), kv("UserID", ptr(c.Args[1]))))
	return call(sel(recv, "ListDevices"), c.Args[0], req)
}

func buildDeleteDevice(recv ast.Expr, c *ast.CallExpr) ast.Expr {
	if len(c.Args) != 3 {
		return nil
	}
	req := addr(lit(gs("DeleteDeviceRequest"), kv("ID", c.Args[2]), kv("UserID", ptr(c.Args[1]))))
	return call(sel(recv, "DeleteDevice"), c.Args[0], req)
}

// pushProvider turns the legacy typed constant into the plain string the
// generated SDK expects.
func pushProvider(e ast.Expr) ast.Expr {
	sel, ok := e.(*ast.SelectorExpr)
	if !ok {
		return e
	}
	switch sel.Sel.Name {
	case "PushProviderFirebase":
		return strLit("firebase")
	case "PushProviderAPN":
		return strLit("apn")
	case "PushProviderXiaomi":
		return strLit("xiaomi")
	case "PushProviderHuawei":
		return strLit("huawei")
	}
	return e
}

// ---------- shared AST helpers ----------

func id(name string) *ast.Ident                     { return ast.NewIdent(name) }
func sel(x ast.Expr, name string) *ast.SelectorExpr { return &ast.SelectorExpr{X: x, Sel: id(name)} }
func call(fn ast.Expr, args ...ast.Expr) *ast.CallExpr {
	return &ast.CallExpr{Fun: fn, Args: args}
}
func gs(name string) ast.Expr                    { return sel(id("getstream"), name) }
func gsCall(name string, a ...ast.Expr) ast.Expr { return call(gs(name), a...) }
func ptr(e ast.Expr) ast.Expr                    { return call(gs("PtrTo"), e) }
func addr(e ast.Expr) ast.Expr                   { return &ast.UnaryExpr{Op: token.AND, X: e} }
func kv(k string, v ast.Expr) ast.Expr           { return &ast.KeyValueExpr{Key: id(k), Value: v} }
func lit(t ast.Expr, elts ...ast.Expr) *ast.CompositeLit {
	return &ast.CompositeLit{Type: t, Elts: elts}
}
func strLit(s string) ast.Expr { return &ast.BasicLit{Kind: token.STRING, Value: strconv.Quote(s)} }
func boolLit(b bool) ast.Expr  { return id(strconv.FormatBool(b)) }
func sub(recv ast.Expr, s string) ast.Expr {
	return call(sel(recv, s))
}
func mapType(key string, value ast.Expr) *ast.MapType {
	return &ast.MapType{Key: id(key), Value: value}
}

// fieldsOf returns the keyed fields of a composite literal, unwrapping a
// leading address-of if present.
func fieldsOf(e ast.Expr) map[string]ast.Expr {
	if u, ok := e.(*ast.UnaryExpr); ok && u.Op == token.AND {
		e = u.X
	}
	cl, ok := e.(*ast.CompositeLit)
	if !ok {
		return nil
	}
	out := map[string]ast.Expr{}
	for _, el := range cl.Elts {
		kve, ok := el.(*ast.KeyValueExpr)
		if !ok {
			continue
		}
		if key, ok := kve.Key.(*ast.Ident); ok {
			out[key.Name] = kve.Value
		}
	}
	return out
}

// optPtr appends a pointer-wrapped field only when the source field is present.
func optPtr(elts *[]ast.Expr, field string, src map[string]ast.Expr, key string) {
	if v, ok := src[key]; ok {
		*elts = append(*elts, kv(field, ptr(v)))
	}
}

// queryFields flattens a legacy QueryOption (possibly embedded in a wrapper
// such as QueryUsersOptions) into generated filter and pagination fields.
func queryFields(e ast.Expr) []ast.Expr {
	f := fieldsOf(e)
	if f == nil {
		return nil
	}
	if inner, ok := f["QueryOption"]; ok {
		f = fieldsOf(inner)
	}
	var elts []ast.Expr
	if v, ok := f["Filter"]; ok {
		elts = append(elts, kv("FilterConditions", v))
	}
	for _, name := range []string{"Limit", "Offset"} {
		optPtr(&elts, name, f, name)
	}
	return elts
}

// optionCall destructures a functional option such as stream.BanWithReason("x").
func optionCall(e ast.Expr) (name string, args []ast.Expr, ok bool) {
	c, ok := e.(*ast.CallExpr)
	if !ok {
		return "", nil, false
	}
	s, ok := c.Fun.(*ast.SelectorExpr)
	if !ok {
		return "", nil, false
	}
	return s.Sel.Name, c.Args, true
}

func isStringLit(e ast.Expr) bool {
	b, ok := e.(*ast.BasicLit)
	return ok && b.Kind == token.STRING
}

func isBoolLit(e ast.Expr) bool {
	i, ok := e.(*ast.Ident)
	return ok && (i.Name == "true" || i.Name == "false")
}
