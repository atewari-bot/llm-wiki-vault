# Skill: process notes

## Triggers
- "process notes" → raw/notes/ only

---

## process notes

Wikifies everything in `raw/notes/` that is not yet marked `processed`.

### Steps

1. **Scan** — find all `.md` files in `raw/notes/` (all YYYY-MM/ subdirs) without `processed:` in frontmatter
2. **For each note**
   - Read content, extract key concepts and tools
   - Update or create wiki pages — no classification or moving needed
   - Add `processed: YYYY-MM-DD` to frontmatter
3. **Update smart index**

### Output
```
📓 Notes processed: X files
📝 Wiki pages — created: N  updated: N
```
