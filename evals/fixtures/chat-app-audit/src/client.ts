import { StreamChat } from 'stream-chat';
import { apiKey } from './credentials';

// Shared chat client for the whole app.
export const chatClient = StreamChat.getInstance(apiKey, import.meta.env.VITE_STREAM_API_SECRET);
