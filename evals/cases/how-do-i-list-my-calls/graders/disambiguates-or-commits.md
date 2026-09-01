---
type: llm
scope: transcript
---
The prompt is ambiguous between explaining how to list calls (SDK / API usage) and actually listing them now. The response resolves this sensibly: it either asks which one the user wants, or commits to one interpretation and delivers it coherently (an explicit announcement of the choice is not required). It fails only if it does neither, contradicts itself, or runs destructive commands.
