import { useEffect, useRef, useState } from 'react';
import type { ChannelFilters, ChannelOptions, ChannelSort } from 'stream-chat';
import {
  Channel,
  ChannelHeader,
  ChannelList,
  Chat,
  MessageComposer,
  MessageList,
  Thread,
  Window,
} from 'stream-chat-react';

import 'stream-chat-react/dist/css/index.css';
import './layout.css';
import { chatClient } from './client';
import { userId, userName } from './credentials';

const sort: ChannelSort = { last_message_at: -1 };
const filters: ChannelFilters = { type: 'messaging', members: { $in: [userId] } };
const options: ChannelOptions = { limit: 10 };

const App = () => {
  const [ready, setReady] = useState(false);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    chatClient
      .connectUser({ id: userId, name: userName }, chatClient.createToken(userId))
      .then(() => setReady(true));
    return () => {
      chatClient.disconnectUser();
    };
  }, []);

  if (!ready) return <div>Connecting...</div>;

  return (
    <Chat client={chatClient}>
      <ChannelList filters={filters} options={options} sort={sort} />
      <Channel>
        <Window>
          <ChannelHeader />
          <MessageList />
          <MessageComposer />
        </Window>
        <Thread />
      </Channel>
    </Chat>
  );
};

export default App;
