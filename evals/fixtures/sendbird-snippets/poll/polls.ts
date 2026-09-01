import type { GroupChannel } from '@sendbird/chat/groupChannel';
import type { PollModule } from '@sendbird/chat/poll';

export async function createLunchPoll(channel: GroupChannel, polls: PollModule) {
  const created = await polls.create({
    title: 'Lunch?',
    optionTexts: ['Pizza', 'Sushi', 'Salad'],
    allowMultipleVotes: true,
    allowUserSuggestion: false,
  });
  await channel.sendUserMessage({ message: 'Vote!', pollId: created.id });
}

export async function voteMany(channel: GroupChannel, pollId: number, optionIds: number[]) {
  await channel.votePoll(pollId, optionIds);
}
