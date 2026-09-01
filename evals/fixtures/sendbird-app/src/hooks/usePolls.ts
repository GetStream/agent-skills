import type SendbirdChat from '@sendbird/chat';
import type { GroupChannelModule } from '@sendbird/chat/groupChannel';
import type { PollModule } from '@sendbird/chat/poll';

type Sdk = SendbirdChat & { groupChannel: GroupChannelModule; poll: PollModule };

export function usePolls(sdk: Sdk, channelUrl: string) {
  const createLunchPoll = async () => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    const created = await sdk.poll.create({
      title: 'Lunch?',
      optionTexts: ['Pizza', 'Sushi', 'Salad'],
      allowMultipleVotes: true,
      allowUserSuggestion: false,
    });
    channel.sendUserMessage({ message: 'Vote!', pollId: created.id });
  };
  const voteMany = async (pollId: number, optionIds: number[]) => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    await channel.votePoll(pollId, optionIds);
  };
  return { createLunchPoll, voteMany };
}
