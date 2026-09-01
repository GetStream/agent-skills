import { useChannelStateContext, useChatContext } from 'stream-chat-react';

// Lets a member start a quick poll in the current channel.
export const CreatePollButton = () => {
  const { client } = useChatContext();
  const { channel } = useChannelStateContext();

  const createPoll = async () => {
    try {
      const { poll } = await client.createPoll({
        name: 'Quick poll',
        options: [{ text: 'Yes' }, { text: 'No' }],
      });
      await channel.sendMessage({ text: 'Quick poll', poll_id: poll.id });
    } catch (err) {
      console.error('poll failed', err);
    }
  };

  return (
    <button type="button" className="create-poll" onClick={createPoll}>
      Create poll
    </button>
  );
};
