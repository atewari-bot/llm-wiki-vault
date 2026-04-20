# Skill: process inbox / process notes / process all

## Triggers
- "process inbox" → raw/inbox/ only
- "process notes" → raw/notes/ only  
- "process all" or "process" → raw/inbox/ + raw/notes/ together

---

## process inbox

Drains `raw/inbox/` — classify, route, wikify.

### Steps

1. **Inventory** — list all `.md` files in `raw/inbox/`
2. **Classify each file**
   - `article` → move to `raw/articles/`, run full ingest
   - `note` / `idea` → move to `raw/notes/`, extract concepts
   - `transcript` → move to `raw/notes/`, extract quotes + people
   - `reference` → move to `raw/articles/`, add to relevant wiki pages
3. **Wikify** — for each file, update or create wiki pages
4. **Mark processed** — add `processed: YYYY-MM-DD` to frontmatter
5. **Update smart index** — run the index update (see smart-index skill)

### Output
```
📥 Inbox processed: X files
  → raw/articles/: N  raw/notes/: N
📝 Wiki pages — created: N  updated: N
⚠️  Skipped: [list any unclear files]
```

---

## process notes

Wikifies everything in `raw/notes/` that is not yet marked `processed`.

### Steps

1. **Scan** — find all `.md` files in `raw/notes/` without `processed:` in frontmatter
2. **For each note**
   - Read content, extract key concepts, people, tools
   - Update or create wiki pages — no classification or moving needed
   - Add `processed: YYYY-MM-DD` to frontmatter
3. **Update smart index**

### Output
```
📓 Notes processed: X files
📝 Wiki pages — created: N  updated: N
```

---

## process all

Runs process inbox first, then process notes. Combined output summary at the end.
