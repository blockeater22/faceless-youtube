"""Knowledge resources for the heuristic analyzer (open & extensible).

These are the "priors" a story analyst brings: which words signal which genre,
setting, time, emotion, conflict, comedy, stakes. An LLM provider can ignore
these; the heuristic provider leans on them. All are plain data, extendable by
plugins/packs without code changes.
"""
from __future__ import annotations

# word -> emotion (aligned with the acting engine's emotion vocabulary)
EMOTION_WORDS = {
    "happy": "happy", "glad": "happy", "smile": "happy", "joy": "happy",
    "excited": "excited", "thrilled": "excited", "amazing": "excited",
    "wow": "excited", "nervous": "nervous", "anxious": "anxious",
    "worried": "nervous", "scared": "scared", "afraid": "scared",
    "terrified": "scared", "angry": "angry", "furious": "angry",
    "mad": "angry", "sad": "sad", "cry": "sad", "lonely": "sad",
    "confident": "confident", "proud": "proud", "determined": "determined",
    "confused": "confused", "curious": "curious", "shocked": "shocked",
    "surprised": "surprised", "embarrassed": "embarrassed",
    "hopeful": "hopeful", "relieved": "relieved", "frustrated": "frustrated",
    "suspicious": "suspicious", "calm": "neutral", "bored": "exhausted",
}

GENRE_CUES = {
    "comedy": ["funny", "joke", "silly", "awkward", "ridiculous", "oops", "prank"],
    "drama": ["cried", "loss", "betrayal", "heart", "tragedy", "alone", "regret"],
    "education": ["learn", "explain", "lesson", "how to", "definition", "step",
                  "understand", "concept", "tutorial"],
    "motivation": ["never give up", "dream", "believe", "overcome", "rise",
                   "inspire", "persevere", "goal"],
    "action": ["run", "chase", "fight", "explosion", "escape", "battle", "jump"],
    "fantasy": ["dragon", "magic", "wizard", "kingdom", "spell", "elf", "quest"],
    "sci-fi": ["robot", "spaceship", "alien", "future", "ai", "laser", "planet"],
    "romance": ["love", "kiss", "date", "crush", "heart", "wedding"],
    "business": ["interview", "office", "meeting", "client", "deadline", "boss",
                 "startup", "career"],
    "children": ["bunny", "puppy", "candy", "playground", "bedtime", "teddy"],
    "documentary": ["in fact", "studies show", "history", "according to", "data"],
}

TONE_CUES = {
    "lighthearted": ["fun", "silly", "playful", "laugh"],
    "serious": ["important", "grave", "serious", "must"],
    "tense": ["fear", "danger", "deadline", "threat", "panic"],
    "hopeful": ["hope", "dream", "believe", "someday", "better"],
    "gloomy": ["dark", "rain", "alone", "loss", "empty", "cold"],
    "inspirational": ["overcome", "rise", "achieve", "inspire", "courage"],
}

# location keyword -> (setting, environment, room_type, indoor)
SETTING_CUES = {
    "interview": ("corporate office", "office", "conference_room", True),
    "office": ("corporate office", "office", "workspace", True),
    "meeting": ("corporate office", "office", "conference_room", True),
    "reception": ("office lobby", "office", "reception", True),
    "bedroom": ("home", "home", "bedroom", True),
    "kitchen": ("home", "home", "kitchen", True),
    "living room": ("home", "home", "living_room", True),
    "home": ("home", "home", "living_room", True),
    "school": ("school", "school", "classroom", True),
    "classroom": ("school", "school", "classroom", True),
    "class": ("school", "school", "classroom", True),
    "street": ("city street", "street", "", False),
    "park": ("park", "park", "", False),
    "forest": ("forest", "outdoor", "", False),
    "restaurant": ("restaurant", "restaurant", "", True),
    "cafe": ("cafe", "restaurant", "", True),
    "shop": ("shop", "shop", "", True),
    "spaceship": ("spaceship", "studio", "", True),
}

TIME_CUES = {
    "morning": "morning", "dawn": "morning", "sunrise": "morning",
    "noon": "noon", "midday": "noon", "afternoon": "noon",
    "evening": "evening", "sunset": "evening", "dusk": "evening",
    "night": "night", "midnight": "night",
}

WEATHER_CUES = {
    "rain": "rain", "rainy": "rain", "raining": "rain", "storm": "storm",
    "snow": "snow", "snowy": "snow", "sunny": "clear", "fog": "fog",
    "foggy": "fog", "cloudy": "clear",
}

GOAL_CUES = ["want", "wants", "need", "needs", "must", "hope", "wish", "decide",
             "decides", "try", "tries", "plan", "pass", "win", "find", "escape",
             "save", "prove", "achieve", "ask", "get", "reach", "become"]

CONFLICT_CUES = ["but", "however", "struggle", "fear", "doubt", "fail", "failed",
                 "problem", "can't", "cannot", "refuse", "argue", "fight",
                 "lose", "lost", "afraid", "nervous", "worried", "stuck"]

COMEDY_CUES = ["awkward", "silly", "oops", "trip", "tripped", "slip", "joke",
               "funny", "ridiculous", "embarrassing", "clumsy", "accidentally"]

STAKES_CUES = ["everything", "or else", "last chance", "life", "death", "final",
               "deadline", "fired", "lose it all", "only chance", "forever"]

URGENCY_CUES = ["now", "hurry", "quick", "quickly", "immediately", "rushing",
                "late", "deadline", "running out", "hurried"]

ROLE_CUES = {
    "interviewer": ["interviewer", "recruiter"], "boss": ["boss", "manager"],
    "teacher": ["teacher", "professor"], "student": ["student", "pupil"],
    "hero": ["hero", "protagonist"], "villain": ["villain", "enemy"],
    "friend": ["friend", "buddy"], "stranger": ["stranger"],
    "parent": ["mother", "father", "mom", "dad", "parent"],
    "child": ["kid", "child", "boy", "girl"],
}
