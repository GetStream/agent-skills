import { useState } from 'react';
import { useSendbirdStateContext } from '@sendbird/uikit-react/useSendbirdStateContext';
import { useModeration } from './hooks/useModeration';
import { usePolls } from './hooks/usePolls';
import { useSendMessage } from './hooks/useSendMessage';
import { useAttachments } from './hooks/useAttachments';

export function ModerationBar({ channelUrl }: { channelUrl: string }) {
  const state = useSendbirdStateContext();
  const sdk = state.stores.sdkStore.sdk;
  const [target, setTarget] = useState('');
  const { silence, unsilence } = useModeration(sdk, channelUrl);
  const { createLunchPoll } = usePolls(sdk, channelUrl);
  const { messages, send } = useSendMessage(sdk, channelUrl);
  const { sendPhoto } = useAttachments(sdk, channelUrl);

  return (
    <div className="moderation-bar">
      <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="user id" />
      <button onClick={() => silence(target)}>Mute 1h</button>
      <button onClick={() => unsilence(target)}>Unmute</button>
      <button onClick={createLunchPoll}>Lunch poll</button>
      <button onClick={() => send('ping')}>Send ping ({messages.length} sent)</button>
      <input type="file" onChange={(e) => e.target.files?.[0] && sendPhoto(e.target.files[0], 'photo')} />
    </div>
  );
}
