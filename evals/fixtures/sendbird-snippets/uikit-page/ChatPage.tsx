import { useState } from 'react';
import SendbirdProvider from '@sendbird/uikit-react/SendbirdProvider';
import GroupChannelList from '@sendbird/uikit-react/GroupChannelList';
import GroupChannel from '@sendbird/uikit-react/GroupChannel';
import '@sendbird/uikit-react/dist/index.css';

type Props = { appId: string; userId: string; nickname: string; accessToken: string };

export default function ChatPage({ appId, userId, nickname, accessToken }: Props) {
  const [channelUrl, setChannelUrl] = useState<string>();
  return (
    <SendbirdProvider appId={appId} userId={userId} nickname={nickname} accessToken={accessToken} theme="dark">
      <div className="chat">
        <GroupChannelList onChannelSelect={(channel) => setChannelUrl(channel?.url)} />
        {channelUrl && <GroupChannel channelUrl={channelUrl} />}
      </div>
    </SendbirdProvider>
  );
}
