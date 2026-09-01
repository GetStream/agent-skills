---
type: llm
scope: files:*.ts
---
The migrated code performs the upload and the send as two steps: it uploads the file first (channel.sendImage / channel.sendFile, obtaining a URL) and then calls channel.sendMessage with an attachments array referencing that URL - or it explicitly defers to stream-chat-react's composer / AttachmentManager pipeline. It does not call a single atomic upload-and-send method, which does not exist in Stream.
