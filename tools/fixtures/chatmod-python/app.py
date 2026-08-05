"""A representative server-side Stream Chat + Moderation integration written
against the legacy stream-chat SDK.

It exists to exercise the migration on something shaped like real customer
code: split across modules, responses actually read, and a spread of
operations rather than a happy path. Python has no compiler to catch a bad
migration, so this doubles as the thing a test suite would run against.
"""

import os
import time

from stream_chat import StreamChat


def client() -> StreamChat:
    return StreamChat(
        api_key=os.environ["STREAM_KEY"],
        api_secret=os.environ["STREAM_SECRET"],
    )


def issue_token(chat: StreamChat, user_id: str) -> str:
    """Token valid for a day, expressed as an absolute expiry."""
    return chat.create_token(user_id, exp=int(time.time()) + 86400)


def onboard(chat: StreamChat) -> None:
    response = chat.upsert_user(
        {
            "id": "user-alice",
            "name": "Alice",
            "role": "user",
            "country": "NL",
        }
    )
    print("upserted", response["users"]["user-alice"]["id"])

    chat.upsert_users(
        [
            {"id": "user-bob", "name": "Bob"},
            {"id": "user-carol", "name": "Carol"},
        ]
    )

    admins = chat.query_users({"role": {"$eq": "admin"}}, limit=10)
    print(len(admins["users"]), "admins")

    chat.update_user_partial(
        {
            "id": "user-bob",
            "set": {"name": "Bob Updated"},
            "unset": ["image"],
        }
    )


def retire(chat: StreamChat, user_id: str) -> None:
    chat.deactivate_user(user_id, mark_messages_deleted=True)
    chat.delete_user(user_id, mark_messages_deleted=True, hard_delete=True)


def run_room(chat: StreamChat) -> None:
    channel = chat.channel("messaging", "general", {"members": ["user-alice", "user-bob"]})
    created = channel.create("user-alice")
    print("channel", created["channel"]["id"])

    channel.add_members(["user-carol"])
    channel.remove_members(["user-carol"])
    channel.update_partial(to_set={"name": "General"}, to_unset=["description"])

    sent = channel.send_message({"text": "Hello world"}, user_id="user-alice")
    message_id = sent["message"]["id"]

    channel.send_message(
        {"text": "Replying in a thread", "parent_id": message_id},
        user_id="user-bob",
    )

    fetched = chat.get_message(message_id)
    print("text is", fetched["message"]["text"])

    chat.update_message({"id": message_id, "text": "Hello, world", "user_id": "user-alice"})
    chat.update_message_partial(message_id, {"set": {"pinned": True}}, user_id="user-alice")

    channel.send_reaction(message_id, {"type": "like"}, user_id="user-bob")
    reactions = channel.get_reactions(message_id, limit=10)
    print(len(reactions["reactions"]), "reactions")

    channel.delete_reaction(message_id, "like", user_id="user-bob")
    chat.delete_message(message_id)

    rooms = chat.query_channels({"members": {"$in": ["user-alice"]}}, limit=10)
    print(len(rooms["channels"]), "channels")


def archive(chat: StreamChat) -> None:
    channel = chat.channel("messaging", "general")
    channel.truncate()
    channel.delete()
