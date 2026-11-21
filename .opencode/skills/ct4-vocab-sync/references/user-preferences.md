# User preferences

## Family-group spacing

- 3 blank lines before the first word of a family group
- 3 blank lines after the last word of a family group
- 1 blank line between members of the same family
- 1 blank line between ordinary entries
- notes such as `- 变形:`, `- 辨析:`, `- 记:`, `- 错:` stay directly below their word

Example:

```text
accumulate ...



account ...          [族:account]

accountability ...   [族:account]

accounting ...       [族:account]



accuse ...
```

## Git

Never run:

```text
git add
git commit
git push
```

Only describe what changed and the validation result. The user commits manually.

## Minimal new-word input

The user may provide only:

```text
word n. 中文
```

Add the rest:

- IPA, preferring US and falling back to UK
- `[族:x]` when an obvious family exists
- `[混:a,b]` for clear confusables
- `[近:a,b]` for clear synonyms
- useful `- 辨析:`, `- 记:`, `- 错:` notes

When a relation is uncertain, leave it out rather than guessing.
