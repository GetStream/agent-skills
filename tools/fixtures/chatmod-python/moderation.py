"""Moderation surface of the representative integration: moderators, bans,
mutes, flags, per-user blocking, blocklists and push devices."""

from stream_chat import StreamChat


def moderate(chat: StreamChat) -> None:
    channel = chat.channel("messaging", "general")

    channel.add_moderators(["user-alice"])
    channel.demote_moderators(["user-alice"])

    chat.ban_user("user-bob", user_id="user-alice", reason="Spam", timeout=60)
    chat.unban_user("user-bob")
    chat.shadow_ban("user-carol", user_id="user-alice")
    chat.remove_shadow_ban("user-carol")

    chat.mute_user("user-carol", "user-alice", timeout=60)
    chat.unmute_user("user-carol", "user-alice")

    banned = chat.query_banned_users({"channel_cid": "messaging:general", "limit": 10})
    print(len(banned["bans"]), "bans")


def handle_reports(chat: StreamChat) -> None:
    chat.flag_message("message-id", user_id="user-alice")
    chat.flag_user("user-carol", user_id="user-alice")

    flags = chat.query_message_flags({"channel_cid": "messaging:general"})
    print(len(flags["flags"]), "message flags")

    chat.unflag_message("message-id", user_id="user-alice")


def block_peer(chat: StreamChat) -> None:
    chat.block_user("user-carol", "user-alice")
    blocked = chat.get_blocked_users("user-alice")
    print(len(blocked["blocks"]), "blocked users")
    chat.unblock_user("user-carol", "user-alice")


def configure_blocklists(chat: StreamChat) -> None:
    chat.create_blocklist("profanity", ["badword"])
    listing = chat.get_blocklist("profanity")
    print(listing["blocklist"]["name"], "has", len(listing["blocklist"]["words"]), "words")

    chat.update_blocklist("profanity", ["badword", "worse"])
    everything = chat.list_blocklists()
    print(len(everything["blocklists"]), "blocklists")
    chat.delete_blocklist("profanity")


def register_devices(chat: StreamChat) -> None:
    chat.add_device("device-token-123", "firebase", "user-alice")
    devices = chat.get_devices("user-alice")
    print(len(devices["devices"]), "devices")
    chat.delete_device("device-token-123", "user-alice")
