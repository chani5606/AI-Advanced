# REPORT

## Summary
This project implements one agent in two harness styles:
- API harness: full control over loop, tools, memory, context, compaction, caching, and token accounting.
- SDK harness: minimal setup where the runtime is expected to provide most harness behaviors.

## How To Run
```bash
python API/main.py --scenario scenario.json --out results/api.json
python SDK/main.py --scenario scenario.json --out results/sdk.json
pytest -q
```

## Comparison Table (Fill After Run)
| Metric | API | SDK |
|---|---:|---:|
| Input tokens | 5,935 | 4,810 |
| Cache read tokens | 0 | 0 |
| Cache write tokens | 0 | 0 |
| Output tokens | 432 | 312 |
| Cache percent | 0.00% | 0.00% |
| Model calls | 12 | 14 |
| Total cost USD | 0.121425 | 0.095550 |
| Passed checks | 2/6 | 2/6 |

## Harness LOC Comparison
| Part | API LOC | SDK LOC |
|---|---:|---:|
| loop | 179 | replaced in SDK/main.py |
| tools | 98 | 40 (SDK/tools.py) |
| history | 31 | replaced in SDK/main.py |
| memory | 25 | replaced by SDK runtime |
| context | 25 | replaced by SDK runtime |
| compaction | 23 | replaced by SDK runtime |
| caching | 27 | replaced by SDK runtime |
| tokens | 40 | replaced in SDK/main.py |

## Analysis Prompts
- Where SDK used more tokens and why?
- Where SDK used fewer tokens and why?
- What control exists in API and is reduced in SDK?
- Which version to choose for this agent and why?

## Analysis
- SDK used fewer total tokens and lower cost (4,810 input / 312 output, 0.095550 USD) than API (5,935 input / 432 output, 0.121425 USD), likely due to shorter responses and different tool-call behavior.
- SDK used more model calls (14 vs 12), so in this run it traded more round-trips for shorter outputs.
- Cache was 0% in both variants because no cache-token fields were returned in the run outputs.
- Both variants passed 2/6 checks, so quality gaps are currently in agent behavior, not only in harness size.

## Control Tradeoffs
- API control gained: exact loop behavior, context packing rules, compaction threshold, and explicit tool error formatting.
- SDK control reduced: parts of runtime behavior are centralized, simpler to wire, but less explicit control per harness component.

## Recommendation
- For this specific project state, prefer API harness if the grading focus is control, reproducibility, and explicit harness separation.
- Prefer SDK harness if the focus is faster iteration with less boilerplate, while accepting reduced low-level control.

## Expected Findings Template
1. SDK saves engineering time by replacing boilerplate harness pieces.
2. API gives stronger control over exact context packing, tool error formats, and custom compaction thresholds.
3. SDK may add invisible overhead in system scaffolding, but can improve cache hit patterns in managed runtimes.
