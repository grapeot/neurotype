# Recorded self-improvement sessions

Each folder is one run of the self-improvement step, started from `checkpoint-c` (best version v2,
CER 0.051). The prompt files are what the coach wrote; the log is its own account of each decision.
These prompts are records, not part of the reference path in `prompts/`.

| Folder | Driver | Iterations | Time | Outcome |
|---|---|---:|---:|---|
| `A/` | `auto_improve.py`, coach `gpt-5` | 2 | 108 s | glossary (kept, 0.034), shifted hands (kept, 0.024) |
| `B/` | `auto_improve.py`, coach `gpt-5` | 2 | 104 s | glossary (kept, 0.035), shifted hands (kept, 0.025) |
| `E/` | `auto_improve.py`, coach `gpt-5` | 2 | 103 s | glossary (kept, 0.036 on three runs), pasted text (kept, 0.022). Measured cost of the whole session: about $0.32 |
| `C/` | `auto_improve.py`, coach `gpt-5` | 4 | 305 s | glossary, shifted hands, pasted text (kept on a three-run mean, shifted hands flagged as worse), shifted hands again; best 0.013 |
| `D-codex/` | Codex CLI with the one-line meta-prompt | 2 | 103 s | glossary (kept, 0.034), shifted hands (kept on a narrow single-run margin, 0.027); it also flagged an ambiguous label (case 66) for human review |
| `leak-example/` | `auto_improve.py` before the leak rule existed | 4 | 290 s | The coach copied benchmark cases into its worked examples, and in v6 added names it could only know from the expected outputs (Caoimhe, Eamonn, Oisin). Kept here as the example of why SOP.md forbids it. |
