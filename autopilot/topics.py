"""Auto-generate fresh video topics (no fixed video list).

Each topic is a small spec: a `kind` (drives format + thumbnail), the target
`playlist`, and a one-line `brief` the scriptwriter turns into a full title +
script. We rotate kinds for variety and avoid recently-used briefs via state.
"""
from __future__ import annotations

import random

# kind -> (playlist, thumbnail style, list of briefs)
KINDS = {
    "whatif": {
        "playlist": "What If…",
        "thumb": "bubbles",
        "briefs": [
            "What if you could hear what people really think of you?",
            "What if you could feel everything you made other people feel?",
            "What if you could see how lonely a stranger really is?",
            "What if everyone had a visible timer counting down their days?",
            "What if you could relive one ordinary day from your childhood?",
            "What if your phone showed the real reason you keep picking it up?",
            "What if you remembered every future you almost lived?",
            "What if you could read the last text someone wrote about you?",
            "What if kindness was visible, like a light around people?",
            "What if you woke up in the life you talked yourself out of?",
            "What if you could ask your future self one single question?",
            "What if every worry you ever had showed up as a person?",
            "What if you could see the exact moment a friendship started to fade?",
            "What if you only kept the memories you actually paid attention to?",
        ],
    },
    "howto": {
        "playlist": "3 AM Thoughts",
        "thumb": "bigface",
        "briefs": [
            "How to stop overthinking everything",
            "How to stop caring what people think",
            "How to stop procrastinating (the real reason you do)",
            "How to stop comparing yourself to other people",
            "How to stop being so hard on yourself",
            "How to actually be present instead of always somewhere else",
            "How to stop doomscrolling at night",
            "How to stop people-pleasing without feeling guilty",
            "How to enjoy things again when everything feels flat",
            "How to stop replaying embarrassing memories",
            "How to make a hard decision when you're stuck",
            "How to quiet your mind when you can't sleep",
        ],
    },
    "otheryou": {
        "playlist": "The Other You",
        "thumb": "split",
        "briefs": [
            "What if you met the person you could have been?",
            "Somewhere there's a version of you who never gave up",
            "The you that stayed vs the you that left — who's happier?",
            "You meet the you from ten years ago. What do you say?",
            "The version of you that took the leap is watching you not.",
            "Meet the you who finally forgave themselves.",
        ],
    },
    "reflection": {
        "playlist": "3 AM Thoughts",
        "thumb": "stars",
        "briefs": [
            "Everyone you walk past is living a life as deep as yours",
            "One day you'll do everything for the last time",
            "You only get about four thousand weeks",
            "You are the universe briefly experiencing itself",
            "You're not afraid of the dark — you're afraid of being alone in it",
            "The people who love you think of you more than you know",
            "Grief is just love with nowhere to go",
            "The small ordinary moments are the ones you'll miss most",
        ],
    },
}


def next_batch(n: int, used: list[str], rotation: list[str], seed: int | None = None):
    """Return up to `n` fresh topics, cycling kinds per `rotation` and avoiding
    briefs in `used`. Falls back to reusing briefs only if a kind is exhausted
    (the scriptwriter still varies the actual script)."""
    rng = random.Random(seed)
    used_set = set(used)
    topics = []
    rotation = rotation or list(KINDS)
    for i in range(n):
        kind = rotation[i % len(rotation)]
        spec = KINDS.get(kind) or next(iter(KINDS.values()))
        pool = [b for b in spec["briefs"] if b not in used_set] or list(spec["briefs"])
        brief = rng.choice(pool)
        used_set.add(brief)
        topics.append({
            "kind": kind,
            "playlist": spec["playlist"],
            "thumb": spec["thumb"],
            "brief": brief,
        })
    return topics
