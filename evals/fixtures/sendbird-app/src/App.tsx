import { useState } from 'react';
import SendbirdProvider from '@sendbird/uikit-react/SendbirdProvider';
import GroupChannelList from '@sendbird/uikit-react/GroupChannelList';
import GroupChannel from '@sendbird/uikit-react/GroupChannel';
import '@sendbird/uikit-react/dist/index.css';
import { colorSet, stringSet } from './theme';
import { ModerationBar } from './ModerationBar';

const appId = import.meta.env.VITE_SENDBIRD_APP_ID;
const userId = import.meta.env.VITE_USER_ID || 'alice';
const nickname = import.meta.env.VITE_NICKNAME || 'Alice';

export default function App() {
  const [channelUrl, setChannelUrl] = useState<string>();
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  return (
    <SendbirdProvider appId={appId} userId={userId} nickname={nickname} theme={theme} colorSet={colorSet} stringSet={stringSet}>
      <div className="app">
        <header className="topbar">
          <span>Acme Support Chat</span>
          <button onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}>Toggle theme</button>
        </header>
        <div className="panes">
          <GroupChannelList onChannelSelect={(channel) => setChannelUrl(channel?.url)} onChannelCreated={(channel) => setChannelUrl(channel.url)} />
          {channelUrl && (
            <div className="conversation">
              <GroupChannel channelUrl={channelUrl} />
              <ModerationBar channelUrl={channelUrl} />
            </div>
          )}
        </div>
      </div>
    </SendbirdProvider>
  );
}
