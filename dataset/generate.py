#!/usr/bin/env python3
"""Generate the curated Neurotype evaluation dataset.

Every item is a short message that a person "meant" to type (ground_truth)
plus what their fingers actually produced (messy_text). Items are grouped
into deliberate failure patterns, documented in dataset/PATTERNS.md.

The generator is deterministic (fixed seed), so `python dataset/generate.py`
always rebuilds the same data/dataset.json.

How messy_text is produced:
  * A seeded "fast typist" corrupts ordinary words: neighbor-key slips,
    dropped letters, swapped letters, doubled letters, and merged words.
  * Protected spans are never corrupted, because the writer pasted them:
    anything in backticks, URLs, emails, @handles, and "quoted" text.
  * Names from the writer's glossary (data/glossary.md) are replaced with
    hand-written phonetic misspellings, because that is how people type
    names they have only heard.
  * "shifted_hands" items are typed with both hands one key to the right.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dataset.json"
SEED = 7

# ---------------------------------------------------------------------------
# Keyboard model
# ---------------------------------------------------------------------------
ROWS = ["qwertyuiop", "asdfghjkl;", "zxcvbnm,./"]
NEIGHBORS: dict[str, str] = {}
for r, row in enumerate(ROWS):
    for c, ch in enumerate(row):
        if not ch.isalpha():
            continue
        near = []
        if c > 0:
            near.append(row[c - 1])
        if c < len(row) - 1:
            near.append(row[c + 1])
        NEIGHBORS[ch] = "".join(x for x in near if x.isalpha())

SHIFT_RIGHT = {}
for row in ROWS:
    for i, ch in enumerate(row[:-1]):
        SHIFT_RIGHT[ch] = row[i + 1]
SHIFT_RIGHT["p"] = "["
SHIFT_RIGHT["l"] = ";"
SHIFT_RIGHT["m"] = ","


def shift_hands(text: str) -> str:
    """Type every letter one key to the right on a QWERTY keyboard."""
    out = []
    for ch in text:
        low = ch.lower()
        if low in SHIFT_RIGHT and low.isalpha():
            out.append(SHIFT_RIGHT[low])
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Typo engine
# ---------------------------------------------------------------------------
PROTECT = re.compile(
    r"`[^`]*`"  # inline code
    r"|https?://\S+"  # URLs
    r"|[\w.+-]+@[\w-]+\.[\w.]+"  # emails
    r"|@\w+"  # handles
    r"|#\w+"  # hashtags
    r"|\"[^\"]*\""  # quoted text
)


def corrupt_word(word: str, rng: random.Random) -> str:
    letters = [i for i, ch in enumerate(word) if ch.isalpha()]
    if len(letters) < 3:
        return word
    op = rng.choices(
        ["neighbor", "drop", "swap", "double"], weights=[4, 3, 3, 1]
    )[0]
    chars = list(word)
    i = rng.choice(letters[1:]) if len(letters) > 1 else letters[0]
    if op == "neighbor":
        low = chars[i].lower()
        if low in NEIGHBORS and NEIGHBORS[low]:
            rep = rng.choice(NEIGHBORS[low])
            chars[i] = rep.upper() if chars[i].isupper() else rep
    elif op == "drop":
        del chars[i]
    elif op == "swap":
        j = i + 1 if i + 1 < len(chars) and chars[i + 1].isalpha() else i - 1
        if chars[j].isalpha():
            chars[i], chars[j] = chars[j], chars[i]
    elif op == "double":
        chars.insert(i, chars[i])
    return "".join(chars)


def corrupt_plain(text: str, rate: float, rng: random.Random) -> str:
    """Corrupt a stretch of text that contains no protected spans."""
    tokens = re.split(r"(\s+)", text)
    out: list[str] = []
    k = 0
    while k < len(tokens):
        tok = tokens[k]
        if tok.isspace() or not tok:
            out.append(tok)
            k += 1
            continue
        m = re.match(r"^([^\w]*)([\w'’-]+)([^\w]*)$", tok)
        if not m or rng.random() > rate:
            out.append(tok)
            k += 1
            continue
        pre, core, post = m.groups()
        # occasionally merge with the next word (missed space bar)
        if (
            rng.random() < 0.12
            and not post
            and k + 2 < len(tokens)
            and tokens[k + 1] == " "
            and re.match(r"^[a-z]", tokens[k + 2])
        ):
            out.append(pre + core)
            k += 2  # skip the space; next word is appended as-is
            continue
        out.append(pre + corrupt_word(core, rng) + post)
        k += 1
    return "".join(out)


def corrupt(text: str, rate: float, rng: random.Random, names: dict[str, str]) -> str:
    """Corrupt text; retry until at least one ordinary word changed."""
    for _ in range(20):
        out = _corrupt_once(text, rate, rng, names)
        if _strip_names(out, names) != _strip_names(text, names, typed=False):
            return out
    raise ValueError(f"could not corrupt {text!r}")


def _strip_names(text: str, names: dict[str, str], typed: bool = True) -> str:
    for correct, spelled in names.items():
        text = text.replace(spelled if typed else correct, "")
    return text


def _corrupt_once(text: str, rate: float, rng: random.Random, names: dict[str, str]) -> str:
    # Replace glossary names with how the writer actually typed them.
    placeholders: dict[str, str] = {}
    for idx, (correct, typed) in enumerate(names.items()):
        key = f"\u0000{idx}\u0000"
        if correct not in text:
            raise ValueError(f"name {correct!r} not in {text!r}")
        text = text.replace(correct, key)
        placeholders[key] = typed
    # Protect pasted spans.
    parts: list[str] = []
    last = 0
    for m in PROTECT.finditer(text):
        parts.append(corrupt_plain(text[last : m.start()], rate, rng))
        parts.append(m.group(0))
        last = m.end()
    parts.append(corrupt_plain(text[last:], rate, rng))
    out = "".join(parts)
    for key, typed in placeholders.items():
        out = out.replace(key, typed)
    return out


# ---------------------------------------------------------------------------
# Items. Each entry: ground truth, plus optional name misspellings.
# ---------------------------------------------------------------------------

# 1. plain_typos: ordinary keystroke errors. Any reasonable prompt fixes these.
PLAIN = [
    "The quarterly report is due on Friday, so please send me your numbers by Wednesday afternoon.",
    "I left my charger in the conference room on the third floor. Could someone grab it for me?",
    "Thanks for the detailed feedback. I will update the proposal and share a new draft tomorrow.",
    "The flight was delayed by two hours, so I will probably miss the beginning of the workshop.",
    "Can we move our weekly sync to Thursday morning? I have a dentist appointment on Tuesday.",
    "The new coffee machine in the kitchen makes a strange noise, but the espresso is surprisingly good.",
    "Please remember to water the plants while I am away. The small ones need water every day.",
    "Our customer survey shows that most people care about battery life more than screen size.",
    "I finished reading the article you recommended. The section about sleep and memory was fascinating.",
    "The library will close early on Saturday because of the holiday, so plan your visit accordingly.",
    "We should order more printer paper before the end of the month. We are almost out again.",
    "My sister is visiting next weekend, so I will be offline on Saturday and most of Sunday.",
    "The recipe calls for two cups of flour, one egg, and a pinch of salt. It takes forty minutes.",
    "Traffic on the bridge was terrible this morning. I think there was an accident near the exit.",
    "Could you double check the invoice before we send it? The total looks a little high to me.",
    "The kids want to go camping this summer, but I am worried about the weather in the mountains.",
    "I booked a table for six people at the Italian restaurant downtown for seven thirty tonight.",
    "The software update fixed the login problem, but now the dashboard loads much more slowly.",
    "Remember that the office will be closed on Monday for maintenance on the heating system.",
    "I think we need a clearer agenda for the planning meeting, otherwise it will run long again.",
    "The museum has a new exhibition about ancient maps. Would you like to go together next month?",
    "Our team doubled its response rate after we started sending shorter and friendlier emails.",
    "Please bring a jacket tomorrow. The forecast says it will be cold and windy near the coast.",
    "I really enjoyed the concert last night. The drummer was incredible during the final song.",
    "The landlord finally agreed to replace the old windows before the winter arrives.",
    "Please print twenty copies of the handout and leave them on the table near the entrance.",
    "We are thinking about adopting a dog, but our apartment might be too small for a big one.",
    "The battery on my laptop drains quickly when I have too many browser tabs open.",
]

# 2. casual_voice: the writer's own style is informal on purpose: slang, chat
#    abbreviations, nonstandard grammar, all lowercase, no final period.
#    The ground truth keeps all of that and only fixes the keystroke slips.
VOICE = [
    "me and him are gonna grab tacos after work, u want anything?",
    "lol that meeting was sooo long, i kinda zoned out halfway thru",
    "tbh i dunno if we need another dashboard, we got like five already",
    "ya i'm omw, gonna be like 10 min late cuz the bus is slow",
    "imo the old logo looked way better, the new one is kinda meh",
    "idk who ate my yogurt but they owe me big time lol",
    "btw the wifi password changed again, ask the front desk for the new one",
    "ngl this new keyboard is amazing, i type way faster now",
    "ok so basically the client wants everything done yesterday, as usual",
    "brb grabbing coffee, ping me if the build breaks again",
    "just landed in denver, gonna call you once i get to the hotel",
    "the printer on the second floor is jammed again, i already called it support",
    "i moved the budget review to monday since half the team is out on friday",
]

# 3. glossary_names: people, projects and places the writer mentions all the
#    time (data/glossary.md). Typed phonetically. Without the glossary nobody
#    could know the spelling; with it, the fix is easy.
GLOSSARY = [
    ("Can you ask Siobhan whether the Marigold launch is still on track for next Tuesday?",
     {"Siobhan": "shivon", "Marigold": "marygold"}),
    ("Joaquin and Niamh will present the Halcyon roadmap at the offsite in March.",
     {"Joaquin": "wakeen", "Niamh": "neeve", "Halcyon": "halsyon"}),
    ("Please loop in Priyanka before we change anything in the Kestrl pipeline.",
     {"Priyanka": "preyanka", "Kestrl": "kestrel"}),
    ("Tadhg says the Bluefynn dashboard is down again, can someone take a look?",
     {"Tadhg": "tige", "Bluefynn": "bluefin"}),
    ("I had lunch with Aoife and she has great ideas for the Marigold onboarding flow.",
     {"Aoife": "eefa", "Marigold": "marrigold"}),
    ("Xiomara will cover for me on Friday, so send any Halcyon questions to her.",
     {"Xiomara": "seeomara", "Halcyon": "halcion"}),
    ("Biscuit needs to go to the vet on Thursday, can Saoirse pick him up after school?",
     {"Biscuit": "biskit", "Saoirse": "seersha"}),
    ("Ngozi found the root cause of the Kestrl outage, it was an expired certificate.",
     {"Ngozi": "ngozy", "Kestrl": "kestral"}),
    ("Let's meet at Cafe Lumiere with Joaquin to plan the Bluefynn migration.",
     {"Cafe Lumiere": "cafe loomeair", "Joaquin": "joakeen", "Bluefynn": "blue fin"}),
    ("Niamh approved the Marigold budget, so Priyanka can start hiring next month.",
     {"Niamh": "neev", "Marigold": "marigolde", "Priyanka": "priyonka"}),
    ("Saoirse and Tadhg are both out sick today, so the Halcyon review is postponed.",
     {"Saoirse": "sersha", "Tadhg": "taig", "Halcyon": "halsion"}),
    ("Ngozi and Joaquin are pairing on the Bluefynn search feature this sprint.",
     {"Ngozi": "ngozee", "Joaquin": "waukeen", "Bluefynn": "bluefinn"}),
]

# 4. unknown_names: like glossary_names, but these people and projects are new
#    and not in the glossary yet. No prompt can recover their spelling. They
#    are the floor of the curve: the fix is a data fix (update the glossary).
UNKNOWN = [
    ("Caoimhe starts on Monday, can someone set up her laptop before she arrives?",
     {"Caoimhe": "keeva"}),
    ("Eamonn from finance wants the Quillon invoices by Thursday.",
     {"Eamonn": "aymon", "Quillon": "quilon"}),
    ("Please add Oisin to the Marigold channel, he is helping with the launch.",
     {"Oisin": "osheen", "Marigold": "marygold"}),
    ("The Zephyra beta opens next week, so tell Tadhg to prepare the release notes.",
     {"Zephyra": "zefira", "Tadhg": "tige"}),
    ("Dervla and Joaquin are flying to Lisbon for the Halcyon partner meeting.",
     {"Dervla": "dervela", "Joaquin": "wakeen", "Halcyon": "halsion"}),
    ("Can you ask Grainne whether the Nuvola contract is ready to sign?",
     {"Grainne": "grawnya", "Nuvola": "nuvolla"}),
]

# 5. pasted_verbatim: code, paths, URLs, emails, handles, hashtags and quotes
#    were pasted, not typed. They must come back exactly as written, even
#    when they look misspelled. Only the words around them get typos.
VERBATIM = [
    "It literally says \"Paymnet faild, plase try agian\" at checkout.",
    "The popup says \"Your sesion has expird, plese sign in agian\" now.",
    "Banner reads \"Welcom bak, valued costumer! Shop our lastest dealz\".",
    "The store title is \"Trak your expences effortlesly\" right now.",
    "The toast reads \"Somthing went wrong, pleas contact suport\".",
    "Label says \"Adress\" and the button says \"Sumbit\" on mobile.",
    "The menu offers \"expresso\" and \"cappucino\" and nobody cares.",
    "One door says \"Employes only\", the other \"Autorized staff\".",
    "Top searches: \"wirless headphones\" and \"blutooth speaker\".",
    "His commits were just \"fixd stuff\" and \"more fixs\" again.",
    "The log says \"Unable to conect to host\" and \"retrying in 5 secnds\".",
    "The subject line was \"Urgnet: invocie overdue\" so I opened it.",
    "The config is `conf/defualt.yaml` with `MAX_CONECTIONS=50` set.",
    "Run `git chekout -b fix/redirct` then `npm run biuld` to test.",
    "The old `calcualte_total` still calls `get_custmer_id` inside.",
    "Send it to billing@acme-exmaple.com and recieving@acme-exmaple.com.",
    "The guide at https://docs.examplle.dev/instal still says `setpu.sh`.",
    "Tag it #DevFestt and join the `Guest_Netwrok` network tonight.",
]

# 6. shifted_hands: halfway through, both hands drifted one key to the right.
#    Hard. A decoding hint helps, but only partly: this is the ability ceiling.
SHIFTED = [
    ("the train is late again so start without me", 3),
    ("can you pick up milk on the way home", 3),
    ("my phone is almost dead, text me later", 3),
    ("the meeting is moved to thursday afternoon", 2),
    ("please call me back when you are free", 3),
]


def build() -> list[dict]:
    rng = random.Random(SEED)
    items: list[dict] = []

    def add(pattern: str, gt: str, messy: str, note: str = "") -> None:
        items.append(
            {
                "id": len(items) + 1,
                "pattern": pattern,
                "ground_truth": gt,
                "messy_text": messy,
                **({"note": note} if note else {}),
            }
        )

    for gt in PLAIN:
        add("plain_typos", gt, corrupt(gt, 0.45, rng, {}))
    for gt in VOICE:
        add("casual_voice", gt, corrupt(gt, 0.4, rng, {}))
    for gt, names in GLOSSARY:
        add("glossary_names", gt, corrupt(gt, 0.3, rng, names))
    for gt, names in UNKNOWN:
        add("unknown_names", gt, corrupt(gt, 0.3, rng, names))
    for gt in VERBATIM:
        add("pasted_verbatim", gt, corrupt(gt, 0.45, rng, {}))
    for gt, n_shifted in SHIFTED:
        words = gt.split(" ")
        messy = " ".join(words[:-n_shifted] + [shift_hands(w) for w in words[-n_shifted:]])
        add("shifted_hands", gt, messy, note=f"last {n_shifted} words typed one key to the right")

    # Sanity: every item must actually be corrupted.
    for it in items:
        if it["messy_text"] == it["ground_truth"]:
            raise SystemExit(f"item {it['id']} has no corruption; change SEED or text")
    return items


def main() -> None:
    items = build()
    counts: dict[str, int] = {}
    for it in items:
        counts[it["pattern"]] = counts.get(it["pattern"], 0) + 1
    payload = {
        "name": "neurotype-curated",
        "version": 1,
        "seed": SEED,
        "description": "Short messages typed carelessly (messy_text) and what the writer meant (ground_truth).",
        "pattern_counts": counts,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(items)} items to {OUT.relative_to(ROOT)}")
    for k, v in counts.items():
        print(f"  {k:16s} {v}")


if __name__ == "__main__":
    main()
