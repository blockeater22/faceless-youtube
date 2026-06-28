"""Script parsing + emotion inference (the 'director' reading the page).

Script format (plain text, one beat per line):

    # comments and blank lines are ignored
    (a quiet street at night)          -> stage/action, no subtitle
    happy: Finally, the weekend!       -> explicit emotion
    What is that...?                   -> emotion inferred (curious/thinking)
    No way!                            -> inferred (shocked)

Explicit ``emotion:`` prefixes always win; otherwise emotion is inferred from
keywords and punctuation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..acting.emotion import EMOTIONS

# keyword -> emotion (first match wins, scanned in this order)
_LEXICON: list[tuple[tuple[str, ...], str]] = [
    (("oh no", "no way", "what?!", "gasp", "whoa", "?!"), "shocked"),
    (("wow", "amazing", "awesome", "yes!", "incredible", "can't wait"), "excited"),
    (("why", "how come", "huh", "confused", "what's going on"), "confused"),
    (("hmm", "let me think", "i wonder", "maybe", "perhaps"), "thinking"),
    (("look", "what's that", "who's there", "hello?", "wonder"), "curious"),
    (("sorry", "sad", "miss", "alone", "lonely", "lost", "cry"), "sad"),
    (("angry", "stop", "how dare", "grr", "hate", "enough"), "angry"),
    (("nervous", "worried", "um", "scared", "afraid", "uh"), "nervous"),
    (("i can", "easy", "watch this", "of course", "no problem"), "confident"),
    (("must", "will", "let's", "ready", "i'll do it", "come on"), "determined"),
    (("phew", "finally", "made it", "thank", "relief"), "relieved"),
    (("hope", "wish", "someday", "please"), "hopeful"),
    (("suspicious", "really", "hmm...", "i don't trust"), "suspicious"),
    (("happy", "glad", "great", "love", "yay", "wonderful"), "happy"),
]


@dataclass
class ScriptLine:
    text: str
    emotion: str
    kind: str = "dialogue"           # dialogue | action
    think: bool = False              # pause/look before this line


def infer_emotion(text: str) -> str:
    low = text.lower()
    for keys, emo in _LEXICON:
        if any(k in low for k in keys):
            return emo
    if low.endswith("?"):
        return "curious"
    if low.endswith("...") or "..." in low:
        return "thinking"
    if low.endswith("!"):
        return "excited"
    return "happy"


# emotions that warrant a "think/notice before reacting" lead-in
_REACTIONS = {"shocked", "confused", "suspicious", "curious"}


def parse_script(text: str) -> list[ScriptLine]:
    lines: list[ScriptLine] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        # action / stage direction
        if (s.startswith("(") and s.endswith(")")) or \
           (s.startswith("[") and s.endswith("]")) or s.startswith("*"):
            body = s.strip("()[]* ").strip()
            emo = infer_emotion(body)
            lines.append(ScriptLine(body, emo, kind="action"))
            continue
        # explicit "emotion: text"
        m = re.match(r"^([a-zA-Z]+)\s*:\s*(.+)$", s)
        if m and m.group(1).lower() in EMOTIONS:
            emo, body = m.group(1).lower(), m.group(2).strip()
        else:
            body, emo = s, infer_emotion(s)
        lines.append(ScriptLine(body, emo, kind="dialogue",
                                think=emo in _REACTIONS))
    return lines
