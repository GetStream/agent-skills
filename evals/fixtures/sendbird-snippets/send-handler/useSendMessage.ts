import { useState } from 'react';
import type { GroupChannel, UserMessage } from '@sendbird/chat/groupChannel';

export function useSendMessage(channel: GroupChannel) {
  const [messages, setMessages] = useState<UserMessage[]>([]);

  const send = (text: string) => {
    channel
      .sendUserMessage({ message: text })
      .onSucceeded((m) => setMessages((prev) => [...prev, m as UserMessage]))
      .onFailed((err) => console.error('send failed', err));
  };

  return { messages, send };
}
