---
name: CT4 Vocab Sync
description: Update the CET-4 word bank when 26_1.md changes. Fix and deduplicate the source in place, sync sources/26_1.md, incrementally merge new words into words.md, add word families, validate, and bump the cache version.
---

# CT4 Vocab Sync

Use this skill when the user asks to update `words.md` from a revised
`D:\Typora\英语\26_1.md`, especially when the request mentions 词库、增量合并、
词族、重复词、或 `26_1.md`.

## Paths

- Source note: `D:\Typora\英语\26_1.md`
  (WSL: `/mnt/d/Typora/英语/26_1.md`)
- Repo: `D:\Typora\英语\ct4`
- Source snapshot: `ct4/sources/26_1.md`
- Word bank: `ct4/words.md`
- Helper tools: `ct4/tools/`

`sources/` is gitignored. Update it on disk, but do not expect it in git.

## Hard rules

1. **Never run `tools/migrate.py` main to regenerate `words.md`.**
   It overwrites manual IPA, family merges, tags, and notes.
2. `words.md` is the only source of truth for the app. Preserve every existing
   line unless the source has a clearly newer merged definition.
3. `26_1.md` is the user's Typora note. Preserve CRLF line endings and its
   overall layout. Only fix errors and merge duplicates.
4. Back up before bulk edits:
   - `/tmp/opencode/ct4-backup/26_1.md`
   - `/tmp/opencode/ct4-backup/words.md`
5. Work in small steps and inspect the diff after each step.

## Workflow

### 1. Inspect the source delta

Compare the current note with the last snapshot:

```bash
diff -u "/mnt/d/Typora/英语/ct4/sources/26_1.md" "/mnt/d/Typora/英语/26_1.md"
```

Count new candidates and duplicate headwords before editing. Do not assume the
new note only adds words; it may move blocks, repeat entries, or introduce
typos.

### 2. Fix the source in place

Apply the known typo fixes from `references/source-typos.md`. Also fix obvious
new errors found in the diff:

- misspelled headword
- wrong Chinese gloss
- missing POS that makes the line unparseable
- glued POS/gloss such as `v.使...n.`
- malformed irregular-verb heads

Do not rewrite the whole note for style. Keep the user's wording where it is
already correct.

Use `scripts/fix_source.py` for the mechanical pass. It preserves CRLF and
writes a report of changed lines.

### 3. Deduplicate the source

Repeated headwords must become one entry, and all of the duplicate's senses,
notes, forms, and relation tags must be merged into the kept entry.

Rules:

1. Normalize the headword:
   - lowercase
   - strip trailing POS tokens
   - normalize irregular forms: `sit-sat-sat` → `sit`,
     `fight-fought-fought` → `fight`
2. Group lines by normalized headword.
3. Keep the **first occurrence** in the file.
4. Merge every unique sense/definition from later occurrences into the first
   occurrence.
5. Merge notes (`- 辨析:`, `- 记:`, `- 错:`, etc.) and tags
   (`[族:]`, `[混:]`, `[近:]`) as a union.
6. Delete the later duplicate lines.
7. Report ambiguous lines for manual review instead of guessing.

Reference example from the user's own merge:

```md
regulate v.(以规章)管理，约束；vt.调整，调节

...

regulate v.管理,约束
```

Must become one entry:

```md
regulate v.(以规章)管理，约束；vt.调整，调节
```

The richer definition wins. Keep the first position.

See `references/merge-rules.md` for the exact algorithm and edge cases.

### 4. Sync the snapshot

After the source is clean:

```bash
cp "/mnt/d/Typora/英语/26_1.md" "/mnt/d/Typora/英语/ct4/sources/26_1.md"
diff -q "/mnt/d/Typora/英语/26_1.md" "/mnt/d/Typora/英语/ct4/sources/26_1.md"
```

### 5. Incrementally merge into `words.md`

Use `scripts/merge_words.py`. It must:

- keep all existing `words.md` entries
- add only words that are not already present
- update an existing entry's gloss only when the source has a clearly richer
  merged definition; keep the existing IPA, tags, and notes
- deduplicate by normalized headword
- preserve `[族:]`, `[混:]`, `[近:]`
- add obvious family tags from `references/family-groups.md`
- run `tools/letter_headings.py` afterward

Useful checks before writing:

```bash
python3 scripts/merge_words.py --dry-run | head -80
```

Then write:

```bash
python3 scripts/merge_words.py --write
python3 tools/letter_headings.py
```

### 6. Fill missing IPA (optional)

If many new words lack IPA, use the Uapi dictionary endpoint:

```bash
UAPI_API_KEY='uapi-...' python3 tools/fetch_ipa_uapi.py --dry-run
UAPI_API_KEY='uapi-...' python3 tools/fetch_ipa_uapi.py --write
```

Rules:

- Only fill blank IPA; never overwrite a hand-written IPA.
- Skip phrases containing spaces.
- Prefer US phonetics, fall back to UK.
- Cache in `tools/uapi-ipa-cache.json` (gitignored).
- Never commit the API key. Read it from `UAPI_API_KEY`.
- If quota or rate limit runs out, leave the rest blank and report it.

### 7. Validate

```bash
python3 tools/check.py
```

Expected:

```text
无法解析：0
重复词头：0
缺失引用：0
自引用：0
缺词性：0
待补释义：0
字母分组放错：0
```

Missing IPA is allowed if the dictionary API is rate-limited; the app can
still use browser TTS. Never replace a hand-written IPA with an API value.

Preview-check in the app:

- data page word count / family count
- A–Z filter includes `# X`
- search for one new word
- one new word detail page
- one new family card

### 8. Finish

- Update `README.md` word/family counts (compute from the app, not by hand).
- Bump the cache version in `index.html`, `sw.js`, and the README note.
- Commit the code/data changes. `sources/26_1.md` stays untracked.
- Tell the user to push manually.
