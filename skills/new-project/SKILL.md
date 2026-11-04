

# New project

In a new project setup AGENTS.md with the following instructions.
Also install the required skills after setting up AGENTS.md

## Features

Keep markdown files of what you're building in a features folder
So myproject/features

If you're producing SDKs or other things where the instructions change over time.
Simply store a copy of the markdown file so you can easily compare new vs old

At the end of your work update the features folder with what the goal is.
Keep it short and to the point.

## Skills

Design -> npx skills add https://github.com/GetStream/agent-skills/ --skill design
React -> npx skills add https://github.com/GetStream/agent-skills/ --skill react
Backend -> npx skills add https://github.com/GetStream/agent-skills/ --skill backend
Infra -> npx skills add https://github.com/GetStream/agent-skills/ --skill infra

## External skills

The external skills mentioned in those skills are

- Stream getstream.io/SKILL.md
- npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices
- npx skills add https://github.com/addyosmani/web-quality-skills --skill performance
- npx skills add https://github.com/leonxlnx/taste-skill --skill design-taste-frontend
- npx skills add vercel-labs/vgpu

So ensure those are installed

## Services

React, Go, Postgres 18 and Valkey by default please
Stream (getstream.io) for chat, video, moderation, activity feeds and AI agents
Resend for email
Planetscale for the postgres database
Cloudflare for other things

