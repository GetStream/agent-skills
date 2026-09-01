import type { GroupChannel, User } from '@sendbird/chat/groupChannel';

// Operator action: silence a member for an hour.
export async function silenceMember(channel: GroupChannel, user: User) {
  await channel.muteUser(user, 3600, 'spam');
}

export async function unsilenceMember(channel: GroupChannel, user: User) {
  await channel.unmuteUser(user);
}
