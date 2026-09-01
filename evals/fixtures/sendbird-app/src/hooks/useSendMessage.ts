import { useState } from 'react';
import type SendbirdChat from '@sendbird/chat';
import type { GroupChannelModule } from '@sendbird/chat/groupChannel';
import type { UserMessage } from '@sendbird/chat/message';

type Sdk = SendbirdChat & { groupChannel: GroupChannelModule };

export function useSendMessage(sdk: Sdk, channelUrl: string) {
  const [messages, setMessages] = useState<UserMessage[]>([]);

  const send = async (text: string) => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    channel
      .sendUserMessage({ message: text })
      .onSucceeded((m) => setMessages((prev) => [...prev, m as UserMessage]))
      .onFailed((err) => console.error('send failed', err));
  };

  return { messages, send };
}
