# Source typo fixes

Apply these with `scripts/fix_source.py`. Add new rows when a new revision of
`26_1.md` introduces another clear typo. Keep the original wording when it is
already correct.

## Headword fixes

| Wrong | Correct |
|---|---|
| `batch n.洗澡` | `bath n.洗澡` |
| `essary` | `essay` |
| `dooted` | `dotted` |
| `efficent` | `efficient` |
| `intervence` | `intervention` |
| `learning n.倾向` | `leaning n.倾向` |
| `bibical` | `biblical` |
| `cyperspace` | `cyberspace` |
| `evently` | `evenly` |
| `fabirc` | `fabric` |
| `fuction` | `function` |
| `variat` | `variant` |
| `carryout` | `carry out` |
| `southwast` | `southwest` |
| `lazyness` | `laziness` |
| `enterpriing` | `enterprising` |
| `practic` | `practical` |

## Gloss fixes

| Wrong | Correct |
|---|---|
| `colleague n.同事，通辽` | `colleague n.同事，同行` |
| `employer 雇金` | `employer n.雇主` |
| `colonize ... 聚局` | `colonize ... 聚居` |
| `disgust n.y厌恶，反感vt.使厌恶，使方案` | `disgust n.厌恶，反感；vt.使厌恶，使反感` |
| `regret ... 对...改到抱歉` | `regret ... 对...感到抱歉` |
| `significant 重要的，数量的的` | `significant adj.重要的，显著的；数量可观的` |
| `palm ... 棕桐树` | `palm ... 棕榈树` |
| `theory ... 管带你` | `theory ... 观点` |
| `attack ... 破环` | `attack ... 破坏` |
| `slip ... 悄悄赛` | `slip ... 悄悄塞` |
| `steady ... 是平静` | `steady ... 使平静` |
| `negative ... 否等词` | `negative ... 否定词` |
| `influential ... n. ...的人` | `influential ... n.有影响力的人` |
| `lower 下main的` | `lower 下面的` |
| `loss ... 亏程` | `loss ... 亏损` |
| `emergency ... 意外时间` | `emergency ... 意外情况` |
| `worthy ... 指得尊敬的` | `worthy ... 值得尊敬的` |

## Missing POS / incomplete lines

| Wrong | Correct |
|---|---|
| `employee 雇员` | `employee n.雇员` |
| `stale 不新鲜的，厌倦的v(使)变得不新鲜` | `stale adj.不新鲜的，厌倦的；v.(使)变得不新鲜` |
| `pain ... vi.使疼痛` | `pain ... vt.使疼痛` |
| `dare modal.敢于...` | `dare v./modal.敢于...` |
| `spoil /spoilt vt...` | `spoil v.毁坏...` |

## Duplicate merges

Duplicates are handled by headword, not by the typo table. See
`merge-rules.md`; `regulate` is the reference example.
