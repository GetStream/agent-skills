import type SendbirdChat from '@sendbird/chat';
import type { GroupChannelModule } from '@sendbird/chat/groupChannel';

type Sdk = SendbirdChat & { groupChannel: GroupChannelModule };

// Operator actions: silence a member for an hour.
export function useModeration(sdk: Sdk, channelUrl: string) {
  const silence = async (userId: string) => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    await channel.muteUserWithUserId(userId, 3600, 'spam');
  };
  const unsilence = async (userId: string) => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    await channel.unmuteUserWithUserId(userId);
  };
  return { silence, unsilence };
}
