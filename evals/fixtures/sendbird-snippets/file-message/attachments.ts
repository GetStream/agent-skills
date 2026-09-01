import type { GroupChannel, FileMessage } from '@sendbird/chat/groupChannel';

export function sendPhoto(
  channel: GroupChannel,
  file: File,
  caption: string,
  onDone: (message: FileMessage) => void,
) {
  channel
    .sendFileMessage({ file, fileName: file.name, message: caption })
    .onSucceeded((m) => onDone(m as FileMessage))
    .onFailed((e) => console.error(e));
}
