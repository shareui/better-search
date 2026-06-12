# Better Search

A plugin for exteraGram / AyuGram that improves search quality across the app using a native scoring engine.

## What it does

- **Plugin list** — fuzzy search with relevance scoring and automatic keyboard layout fix (e.g. typing in Russian when Latin is expected)
- **Chat messages** — reorders search results by how closely they match the query
- **Dialogs** — reorders dialog search results by name/username relevance score

All three areas can be toggled independently in settings.

> Note: Since dialogs and messages are retrieved through the server, the improvement isn't that significant. However, I plan to create a standalone method in the future.

## Requirements

- Client `>=12.6.4`
- exteraGram SDK `>=1.4.3.3`
- Arch `arm64-v8a`

## License

Apache License 2.0
