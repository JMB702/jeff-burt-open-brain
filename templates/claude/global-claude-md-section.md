
## Deep Context — Open Brain

When you need additional context about {{USER_FIRST_NAME}}'s life, projects, people, or ideas that isn't covered above, search their **Open Brain** knowledge system. Open Brain is an Obsidian vault at:

```
{{VAULT_PATH}}/
```

### How to find information in Open Brain

Follow this order — stop as soon as you have what you need:

1. **Entity index** → Read `entities-index.md` first. It lists every entity (projects, people, events, concepts) with aliases. Use it to resolve names and find the right file path.
2. **Entity file** → Read the entity file directly (e.g., `projects/My Project.md`). It contains every paragraph {{USER_FIRST_NAME}} has written about that topic, chronologically. This is almost always sufficient.
3. **People profile** → For info about a person, read `people/<slug>.md`. Has contact info, relationship context, and mentions.
4. **Raw daily notes** → Only grep `notes/raw-daily-notes/` as a last resort — when the topic isn't tracked yet, or {{USER_FIRST_NAME}} explicitly asks to search notes. Entity files already contain the relevant excerpts.
5. **Historical notes** → Check `notes/historical-notes/` for biographical/historical context about {{USER_FIRST_NAME}}'s past. These are life history entries written from memory — good context but may contain inaccuracies.

**Do not scan raw notes as a first step.** That wastes tokens on irrelevant content.

### When to access Open Brain
- {{USER_FIRST_NAME}} asks about a person, project, or idea not covered in this file
- You need historical context on how a decision evolved
- You need to understand {{USER_FIRST_NAME}}'s relationship with someone
- {{USER_FIRST_NAME}} references something they "wrote about" or "mentioned before"
- You're working on a project and need context about {{USER_FIRST_NAME}}'s goals, preferences, or prior decisions

### Rules when accessing Open Brain
- **Never edit daily notes** — read-only. You may only add `[[wiki links]]`.
- **Never invent facts.** If it's not in the notes, say you don't know.
- **Daily notes are the source of truth** for project status — not source code or other CLAUDE.md files.
- Use the `/open-brain-extract` skill for full chronological extraction of a topic.
