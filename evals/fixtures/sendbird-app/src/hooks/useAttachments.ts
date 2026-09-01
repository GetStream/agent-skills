import type SendbirdChat from '@sendbird/chat';
import type { GroupChannelModule } from '@sendbird/chat/groupChannel';
import type { FileMessage } from '@sendbird/chat/message';

type Sdk = SendbirdChat & { groupChannel: GroupChannelModule };

export function useAttachments(sdk: Sdk, channelUrl: string) {
  const sendPhoto = async (file: File, caption: string) => {
    const channel = await sdk.groupChannel.getChannel(channelUrl);
    return new Promise<FileMessage>((resolve, reject) => {
      channel
        .sendFileMessage({ file, fileName: file.name, message: caption })
        .onSucceeded((m) => resolve(m as FileMessage))
        .onFailed((e) => reject(e));
    });
  };
  return { sendPhoto };
}
