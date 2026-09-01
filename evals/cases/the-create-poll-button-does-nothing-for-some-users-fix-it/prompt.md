---
name: the Create poll button does nothing for some users - fix it
runs: 1
max_turns: 80
timeout_seconds: 900
fixture: chat-app-polls-role
creds: true
after_script: getstream api chat UpdateChannelType --name messaging --request '{"grants":{"guest":["add-links-owner","cast-vote","create-attachment-owner","create-channel","create-mention-owner","create-message-owner","create-reaction-owner","create-reply-owner","delete-attachment-owner","delete-channel-owner","delete-message-owner","delete-reaction-owner","flag-message-owner","mute-channel-owner","pin-message-owner","query-votes","read-channel-members-owner","read-channel-owner","recreate-channel-owner","remove-own-channel-membership-owner","run-message-action-owner","send-custom-event-owner","share-location-any-team","truncate-channel-owner","update-channel-members-owner","update-channel-owner","update-message-owner","update-thread-owner","upload-attachment-owner"]}}' >/dev/null 2>&1 || true
---
The Create poll button does nothing for some users - fix it. It works for me but not for the poll-guest user.
