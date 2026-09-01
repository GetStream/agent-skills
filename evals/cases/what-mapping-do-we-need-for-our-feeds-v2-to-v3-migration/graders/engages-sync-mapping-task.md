---
type: llm
scope: last_message
---
The response engages the Feeds v2 -> v3 sync mapping task specifically: it asks for (or looks for) the v2 app's API key and secret in order to sample the app's real v2 activities and reactions, or explains that the mapping object is derived from what the app's v2 data actually contains. A generic essay about migrating feeds, or an answer that invents the mapping without the app's data, fails.
