# Source and word-bank merge rules

## 1. Headword normalization

Use the same normalization everywhere:

1. lower-case the headword
2. replace curly apostrophes with straight ones
3. remove trailing POS tokens (`n`, `v`, `vt`, `vi`, `adj`, `adv`, etc.)
4. normalize an irregular-verb chain to its base:
   - `sit-sat-sat` → `sit`
   - `fight-fought-fought` → `fight`
   - `stick-stuck` → `stick`
   - `lean-leaned` → `lean`
5. normalize phrases with single spaces

Do not merge different headwords merely because they share a root. `regulate`
and `regulation` are separate entries; their family relationship belongs in
`[族:]`.

## 2. Deduplicating `26_1.md`

For every normalized headword with more than one entry:

1. Keep the first occurrence's position and any blockquote/bullet prefix.
2. Collect all unique senses from every duplicate.
3. Prefer the clearest/most complete wording for the same sense.
4. Merge all notes and relation tags into the kept entry.
5. Delete the later duplicate lines.
6. If a duplicate spans a blockquote group and cannot be removed safely, leave
   it and report it for manual review.

Reference merge from the user:

```md
regulate v.(以规章)管理，约束；vt.调整，调节

...

regulate v.管理,约束
```

Result:

```md
regulate v.(以规章)管理，约束；vt.调整，调节
```

The first occurrence is kept; the later shorter line is removed. The richer
definition wins.

## 3. Merging into `words.md`

`words.md` already contains hand-edited IPA, tags, and notes. Never regenerate
it from the source.

For each normalized word:

### New word

Add one line:

```md
word pos. 中文释义 /ipa/ [族:root] [混:...] [近:...]
```

Use the merged source senses. Add IPA only if it can be obtained without
overwriting an existing value.

### Existing word

- Keep the existing IPA and tags.
- If the source's merged definition is clearly richer, replace only the gloss.
- If the source adds a new sense that the existing line lacks, append it.
- Never duplicate an existing sense.
- Never remove a hand-written note.
- For `regulate`, update the gloss to the merged source definition while
  keeping `/ˈrɛɡjəleɪt/`.

## 4. Families

Add `[族:]` only for transparent groups:

- same derivational stem (`arrange`/`arrangement`)
- same root with a regular suffix (`protect`/`protection`/`protective`)
- the root word itself already exists or is part of the new batch

If unsure, leave the word untagged. Wrong family groups are worse than missing
ones.

When a family name already exists, use the existing name, e.g.:

- `determin`: `determine`, `determination`, `determined`
- `consequ`: `consequence`, `consequent`, `consequently`
- `space`: `space`, `spaceship`, `spacecraft`, `spacious`, `spatial`

## 5. Formatting and validation

After writing:

```bash
python3 tools/letter_headings.py
python3 tools/family_spacing.py --write
python3 tools/check.py
```

`letter_headings.py` rebuilds A–Z headings and already applies family spacing.
If another edit collapses blank lines, run
`scripts/normalize_family_spacing.py --write`.

Spacing rules:

- 3 blank lines before a family group
- 3 blank lines after a family group
- 1 blank line between family members
- 1 blank line between ordinary entries
- notes stay directly below their word

Zero errors for:

- unparseable lines
- duplicate headwords
- missing references
- self references
- missing POS
- empty glosses
- wrong letter headings

Missing IPA is tolerated. If the API is rate-limited, leave it blank rather than
inserting a guessed pronunciation.

## 6. Git

Never run `git add`, `git commit`, or `git push`. Report the changed files and
validation result; the user commits manually.
