#!/usr/bin/env python3
"""Generate 10 long-form (5-7 min) chaptered videos for Inklings.

Reuses scene templates from generate_stories.py and the chapter-card template
from generate_longform.py. Visuals rotate template every beat and narration
lines are kept short (~8-14 words) so each scene's TTS-driven duration lands
near 3-5s -- the engagement-pacing lever for long-form retention.

Run:    python scripts/generate_longform_batch.py
Render: for f in stories/lf_*.json; do python -m faceless build "$f" --formats 16:9; done
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_stories import BASE_STYLE, OUT, TEMPLATES, label  # noqa: E402

VOICE = {"backend": "kokoro", "voice": "am_liam", "polish": True, "gap": 0.22, "kokoro_speed": 0.78}


def t_chapter(p):
    props = [
        label("cnum", p.get("num", "1"), "accent", 0.20, [0.5, 0.37], t0=0.0),
        label("ctitle", p.get("title", ""), "ink", 0.062, [0.5, 0.56], t0=0.12),
    ]
    return ([], props)


TMPL = dict(TEMPLATES)
TMPL["chapter"] = t_chapter


def build(slug, title, hook, playlist, beats):
    scenes = []
    chapters = []
    t = 0.0
    for i, beat in enumerate(beats):
        tmpl, text = beat[0], beat[1]
        params = beat[2] if len(beat) > 2 else {}
        actors, props = TMPL[tmpl](params or {})
        min_dur = 3.2 if tmpl == "chapter" else 3.6
        scenes.append({"id": f"{i:02d}_{tmpl}", "narration": text, "min_dur": min_dur,
                       "actors": actors, "props": props})
        if tmpl == "chapter":
            chapters.append((t, params.get("num", ""), params.get("title", "")))
        t += min_dur  # rough estimate only, real timestamps come from spoken audio
    story = {"title": title, "handle": "@Inklings1", "hook": hook, "hook_dur": 1.8,
             "meta": {"playlist": playlist, "format": "long-form"},
             "style": BASE_STYLE, "voice": VOICE, "scenes": scenes}
    path = OUT / f"{slug}.json"
    path.write_text(json.dumps(story, indent=2))
    print(f"wrote {path}  ({len(scenes)} scenes, {len(chapters)} chapters)")
    return path


# --------------------------------------------------------------------------- #
# 10 long-form videos. Each: 7-beat intro, 6 chapters x (card + 8 beats),
# 4-beat outro -> ~65 beats/video, short lines -> visual change every ~3-5s.
# --------------------------------------------------------------------------- #
BATCH = []

# ============================================================ VIDEO 1 ===== #
BATCH.append((
    "lf_psychological_effects",
    "6 Psychological Effects Secretly Running Your Life",
    "Your brain is lying to you right now.",
    "Mind Traps",
    [
        ("solo", "Your brain makes thousands of decisions today without ever asking you.", {"pose": "think"}),
        ("point", "Most of them run on invisible scripts called psychological effects.", {"dir": "r"}),
        ("crowd", "Everyone around you is running on the exact same scripts.", {}),
        ("solo", "You've never noticed them, because they were never meant to be noticed.", {"pose": "stand"}),
        ("solo", "Here are six of them quietly steering your entire life.", {"poses": ["stand", "reach"]}),
        ("stars", "Once you see them, you can never fully unsee them.", {}),
        ("solo", "Let's start with the one that makes you over-think every room you enter.", {"pose": "look_up"}),

        ("chapter", "One. The Spotlight Effect.", {"num": "1", "title": "SPOTLIGHT EFFECT"}),
        ("solo", "You walk into a room sure that everyone notices your every move.", {"pose": "stand", "face": "surprised"}),
        ("crowd", "In reality, almost no one is paying attention to you at all.", {}),
        ("point", "Your brain imagines an audience that simply isn't watching.", {"dir": "l"}),
        ("label_above", "That stain on your shirt? Nobody clocked it. You did.", {"text": "!", "face": "sad"}),
        ("solo", "Psychologists call this the spotlight effect, and it never fully turns off.", {"pose": "think"}),
        ("two", "Everyone else is too busy starring in their own imagined spotlight.", {"poseA": "stand", "poseB": "think"}),
        ("solo", "So that embarrassing thing you did last week? Already forgotten.", {"pose": "stand", "face": "happy"}),
        ("celebrate", "You were never the main character of that memory. You were free.", {}),

        ("chapter", "Two. Mere-Exposure Effect.", {"num": "2", "title": "MERE-EXPOSURE EFFECT"}),
        ("solo", "You like things mostly because your brain has simply seen them before.", {"pose": "stand"}),
        ("walk", "The same song annoys you on day one, then hooks you by day five.", {"x0": 0.3, "x1": 0.7}),
        ("two", "That coworker you disliked at first? Familiarity quietly rewired your opinion.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "Advertisers know this. Repetition alone builds trust, with zero new evidence.", {"pose": "think"}),
        ("label_above", "Seen it once, neutral. Seen it ten times, somehow likable.", {"text": "x10", "face": "neutral"}),
        ("crowd", "It's why familiar faces feel safe, even strangers in a new city.", {}),
        ("solo", "Your comfort zone isn't truth. It's just repetition, dressed up as preference.", {"pose": "think"}),
        ("stars", "Question what you like. Ask if it earned that spot, or just repeated itself there.", {}),

        ("chapter", "Three. Loss Aversion.", {"num": "3", "title": "LOSS AVERSION"}),
        ("solo", "Losing twenty dollars hurts roughly twice as much as gaining it feels good.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Your brain treats losses as nearly twice as loud as gains.", {"text": "2x", "color": "accent"}),
        ("two", "It's why you stay in a job, a city, a relationship, out of fear.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Not because it's good. Because leaving feels like losing something, anything.", {"pose": "think", "face": "sad"}),
        ("point", "This is why sales scream 'limited time' instead of 'great deal.'", {"dir": "r"}),
        ("solo", "Fear of loss moves you faster than the promise of any gain.", {"pose": "stand"}),
        ("walk", "Notice when fear of losing something is the only reason you're staying.", {"x0": 0.4, "x1": 0.6, "face": "think"}),
        ("celebrate", "Sometimes the bravest move is simply naming the fear out loud.", {}),

        ("chapter", "Four. The Zeigarnik Effect.", {"num": "4", "title": "ZEIGARNIK EFFECT"}),
        ("solo", "Unfinished tasks live louder in your head than finished ones ever did.", {"pose": "think"}),
        ("label_above", "That one open tab in your mind, just sitting there.", {"text": "...", "face": "sad"}),
        ("solo", "It's called the Zeigarnik effect, and it's why cliffhangers work on you.", {"pose": "stand"}),
        ("two", "Your brain keeps an open loop running until you close it.", {"poseA": "stand", "poseB": "think"}),
        ("solo", "It's why that unsent text message keeps replaying at 2 a.m.", {"pose": "stand", "face": "sad"}),
        ("point", "Writers exploit this on purpose. Episodes never truly end.", {"dir": "r"}),
        ("solo", "But you can use it too. Write the loop down, and your mind lets go.", {"pose": "reach"}),
        ("stars", "An unfinished thought wants closure, not more time spent spinning.", {}),

        ("chapter", "Five. Social Proof.", {"num": "5", "title": "SOCIAL PROOF"}),
        ("crowd", "If everyone around you is doing something, you assume it must be right.", {}),
        ("solo", "It's a shortcut your brain built to save you time, not to find truth.", {"pose": "think"}),
        ("two", "It's why you trust a restaurant with a line out the door.", {"poseA": "stand", "poseB": "stand"}),
        ("label_above", "A crowd is not evidence. A crowd is just a crowd.", {"text": "?", "color": "accent"}),
        ("solo", "Entire trends, manias, and bad decisions spread through this one shortcut.", {"pose": "stand"}),
        ("point", "Ask yourself: do I believe this, or does everyone else?", {"dir": "l"}),
        ("solo", "The crowd can be loud and still be completely wrong.", {"pose": "think", "face": "sad"}),
        ("celebrate", "Your own quiet judgment is worth more than a thousand nodding heads.", {}),

        ("chapter", "Six. Sunk Cost Fallacy.", {"num": "6", "title": "SUNK COST FALLACY"}),
        ("solo", "You finish a bad movie because you already sat through an hour of it.", {"pose": "stand", "face": "sad"}),
        ("label_above", "The time you already spent is gone either way. Always.", {"text": "$", "face": "neutral"}),
        ("two", "It's why people stay in careers, degrees, and loves long past their expiry.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Your past investment has zero vote in what's actually good for you now.", {"pose": "think"}),
        ("point", "The only real question left is: would I start this today?", {"dir": "r"}),
        ("solo", "If the honest answer is no, the sunk cost was never the cost.", {"pose": "stand"}),
        ("walk", "Walking away from years invested can still be the smartest move you make.", {"x0": 0.35, "x1": 0.65, "face": "think"}),
        ("stars", "Your future doesn't owe your past a single extra minute.", {}),

        ("solo", "Six quiet scripts, running your decisions before you even notice.", {"pose": "stand"}),
        ("crowd", "Everyone around you is run by the same six, completely unaware.", {}),
        ("solo", "You can't delete them. But naming them takes back the wheel.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which one of these caught you off guard? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 2 ===== #
BATCH.append((
    "lf_harsh_truths",
    "6 Harsh Truths About Life Nobody Tells You",
    "Nobody is coming to save you.",
    "Hard Truths",
    [
        ("solo", "Nobody warns you about these six truths. So consider this the warning.", {"pose": "stand"}),
        ("crowd", "Everyone learns them eventually. Usually the hard, expensive way.", {}),
        ("solo", "You can learn them now, for free, in the next few minutes.", {"pose": "think"}),
        ("point", "Or you can learn them later, after they've already cost you something.", {"dir": "r"}),
        ("solo", "Either way, life is going to teach this lesson. Let's get ahead of it.", {"poses": ["stand", "reach"]}),
        ("stars", "None of these are comfortable. All of them are useful.", {}),
        ("solo", "Truth one starts with a sentence most people never say out loud.", {"pose": "look_up"}),

        ("chapter", "One. Nobody's Coming.", {"num": "1", "title": "NOBODY IS COMING"}),
        ("solo", "Nobody is coming to fix your finances, your body, or your habits.", {"pose": "stand", "face": "sad"}),
        ("two", "Friends can support you. Family can love you. Neither can do it for you.", {"poseA": "stand", "poseB": "stand"}),
        ("label_above", "Waiting for rescue is the slowest way to grow up.", {"text": "?", "face": "neutral"}),
        ("solo", "The version of you that solves this only exists if you build him.", {"pose": "think"}),
        ("point", "This isn't a sad truth. It's the most empowering one here.", {"dir": "l"}),
        ("solo", "If no one's coming, then nobody can take credit either. It's yours.", {"pose": "stand", "face": "happy"}),
        ("walk", "The day you stop waiting is the day you actually start moving.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "And momentum, once it starts, carries far more than motivation ever did.", {}),

        ("chapter", "Two. Most Won't Change.", {"num": "2", "title": "MOST PEOPLE WON'T CHANGE"}),
        ("solo", "Most people you know today will be the same person in ten years.", {"pose": "stand"}),
        ("two", "Not because they can't change. Because change is uncomfortable, and comfort wins.", {"poseA": "shrug", "poseB": "stand"}),
        ("label_above", "Hoping someone changes is not a plan. It's a delay.", {"text": "...", "face": "sad"}),
        ("solo", "Stop waiting for people to become a version they show no signs of becoming.", {"pose": "think", "face": "sad"}),
        ("point", "Believe the pattern in front of you, not the promise in their mouth.", {"dir": "r"}),
        ("solo", "Some people do change. But it's rare, and it's never on your timeline.", {"pose": "stand"}),
        ("two", "Love people as they are now. Plan your life around that, not a maybe.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
        ("stars", "It will save you years of waiting for a person who never arrives.", {}),

        ("chapter", "Three. You'll Be Forgotten Fast.", {"num": "3", "title": "YOU'LL BE FORGOTTEN FAST"}),
        ("solo", "Most people forget an embarrassing thing you did within about a week.", {"pose": "stand", "face": "surprised"}),
        ("crowd", "Everyone is the main character of their own story, not a critic of yours.", {}),
        ("label_above", "Your worst day lives rent-free in your head alone.", {"text": "!", "face": "sad"}),
        ("solo", "This should feel terrifying. It's actually the most freeing truth on this list.", {"pose": "think"}),
        ("point", "If they'll forget it anyway, why are you still performing for them?", {"dir": "l"}),
        ("solo", "Take the risk. Say the weird thing. Wear the bold color.", {"pose": "reach", "face": "happy"}),
        ("walk", "The audience you're afraid of is too busy starring in their own life.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "You have far more room to be yourself than you've ever used.", {}),

        ("chapter", "Four. Comfort Is the Enemy.", {"num": "4", "title": "COMFORT IS THE ENEMY"}),
        ("solo", "Comfort feels like safety, but it quietly erodes everything you could become.", {"pose": "stand"}),
        ("two", "The gym is uncomfortable. The hard conversation is uncomfortable. Growth always is.", {"poseA": "stand", "poseB": "shrug"}),
        ("label_above", "If it's easy, it's probably not changing you much.", {"text": "=", "face": "neutral"}),
        ("solo", "Your comfort zone was sized for the person you used to be.", {"pose": "think"}),
        ("point", "Outgrowing it is supposed to feel tight before it feels right.", {"dir": "r"}),
        ("solo", "Discomfort isn't a sign you're doing it wrong. It's a sign you're doing it.", {"pose": "stand"}),
        ("walk", "Step toward the thing that makes your chest tighten just slightly.", {"x0": 0.3, "x1": 0.7, "face": "think"}),
        ("stars", "On the other side of that tightness is the life you actually want.", {}),

        ("chapter", "Five. Time Doesn't Heal.", {"num": "5", "title": "TIME DOESN'T HEAL, HABITS DO"}),
        ("solo", "Time alone doesn't heal anything. It just adds distance to the pain.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Healing is something you do, not something that happens to you.", {"text": "+", "face": "neutral"}),
        ("two", "Two people, same heartbreak, same year. One heals. One just ages around it.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "The difference is what they did with the days in between.", {"pose": "think"}),
        ("point", "Therapy, movement, honesty, journaling. Small daily habits do the actual healing.", {"dir": "r"}),
        ("solo", "Time just gives the habits room to work. It was never the cure itself.", {"pose": "stand"}),
        ("walk", "Build one small healing habit today, instead of waiting for time to do it.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "A year from now, the habit will have done what waiting never could.", {}),

        ("chapter", "Six. You're Replaceable at Work.", {"num": "6", "title": "REPLACEABLE AT WORK, NOT HOME"}),
        ("solo", "At work, you are replaceable. A new hire can learn your job in months.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Title, desk, login. All of it transfers to someone else.", {"text": "->", "face": "neutral"}),
        ("two", "At home, you are not replaceable. No one else is your kid's parent.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
        ("solo", "No one else is your partner's person, or your friend's person, but you.", {"pose": "think"}),
        ("point", "Stop spending your irreplaceable hours on a role that could be filled by anyone.", {"dir": "l"}),
        ("solo", "Work hard. Just don't confuse which role actually needs the best of you.", {"pose": "stand"}),
        ("walk", "Walk out on time tonight, for the people who can't be replaced.", {"x0": 0.4, "x1": 0.6, "face": "happy"}),
        ("stars", "Your job will survive without you. Your family's memories of you won't.", {}),

        ("solo", "Six harsh truths. None of them comfortable. All of them useful.", {"pose": "stand"}),
        ("crowd", "Everyone learns these eventually. Now you get a head start.", {}),
        ("solo", "Knowing them changes nothing by itself. Acting on one of them changes everything.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which truth landed hardest for you? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 3 ===== #
BATCH.append((
    "lf_feel_behind",
    "6 Reasons You Feel So Behind in Life",
    "You are not actually behind.",
    "Hard Truths",
    [
        ("solo", "You feel behind. Like everyone else got the instructions and you didn't.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Almost everyone secretly feels this exact same way, all at once.", {}),
        ("solo", "That feeling is real. But it's also built on a broken measuring stick.", {"pose": "think"}),
        ("point", "Here are six reasons it feels this way, and why most of them lie.", {"dir": "r"}),
        ("solo", "By the end, the race you think you're losing might not even exist.", {"poses": ["stand", "reach"]}),
        ("stars", "Let's take the broken measuring stick apart, one piece at a time.", {}),
        ("solo", "Reason one is sitting in your pocket, buzzing at you right now.", {"pose": "look_up"}),

        ("chapter", "One. The Highlight Reel.", {"num": "1", "title": "THE HIGHLIGHT REEL"}),
        ("solo", "Everyone online posts the wedding, the promotion, the vacation. Never the rest.", {"pose": "stand"}),
        ("label_above", "You're comparing your full footage to their best ten seconds.", {"text": "?", "face": "sad"}),
        ("two", "Behind every glowing post is laundry, doubt, and bills, just like yours.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Nobody posts the argument, the rejection email, or the 3 a.m. panic.", {"pose": "think", "face": "sad"}),
        ("point", "You can't lose a race against a reel that was never the whole story.", {"dir": "l"}),
        ("solo", "Their highlight reel was never a fair opponent for your entire life.", {"pose": "stand"}),
        ("walk", "Step back from the feed and measure your week by your own week.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "The race you thought you were losing was never actually a race.", {}),

        ("chapter", "Two. The Comparison Trap.", {"num": "2", "title": "THE COMPARISON TRAP"}),
        ("solo", "Comparison always picks the one person doing better, never the thousand who aren't.", {"pose": "stand"}),
        ("label_above", "Your brain filters for threats. It was never built for fairness.", {"text": "!", "face": "neutral"}),
        ("two", "You compare your messy middle to someone else's edited beginning, every time.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "It's a rigged game with no finish line and no fair referee.", {"pose": "think", "face": "sad"}),
        ("point", "The only honest comparison left is you, today, against you, yesterday.", {"dir": "r"}),
        ("solo", "That comparison you can actually win, slowly, on your own terms.", {"pose": "stand", "face": "happy"}),
        ("walk", "Trade the scoreboard with strangers for a private one with your past self.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "That's the only leaderboard that was ever actually yours to climb.", {}),

        ("chapter", "Three. Nobody Shows the Struggle Years.", {"num": "3", "title": "NOBODY SHOWS THE STRUGGLE YEARS"}),
        ("solo", "Every success story skips the five quiet years before anyone was watching.", {"pose": "stand"}),
        ("crowd", "You only meet people at the finish line, never at mile one.", {}),
        ("label_above", "The 'overnight success' usually took about a decade, hidden.", {"text": "10yr", "face": "neutral"}),
        ("solo", "You're comparing your year one to someone else's year ten, unaware.", {"pose": "think", "face": "sad"}),
        ("point", "The struggle years aren't a sign you're behind. They're a sign you're in it.", {"dir": "l"}),
        ("solo", "Everyone impressive walked through this exact unglamorous stretch you're standing in.", {"pose": "stand"}),
        ("walk", "Keep walking through the part nobody filmed. That's where it's actually built.", {"x0": 0.35, "x1": 0.65, "face": "think"}),
        ("celebrate", "One day your struggle years become someone else's invisible chapter too.", {}),

        ("chapter", "Four. Wrong Timeline.", {"num": "4", "title": "YOU'RE MEASURING THE WRONG TIMELINE"}),
        ("solo", "You're using society's checklist: degree by twenty-two, house by thirty.", {"pose": "stand"}),
        ("label_above", "That checklist was never written for your specific life.", {"text": "x", "color": "accent"}),
        ("two", "Some people peak at twenty-five. Others are just getting warmed up at fifty.", {"poseA": "celebrate", "poseB": "stand", "colorB": "muted"}),
        ("solo", "There is no universal deadline for becoming who you're meant to be.", {"pose": "think"}),
        ("point", "Your timeline only has to make sense for the life you're actually living.", {"dir": "r"}),
        ("solo", "Borrowed deadlines from other people's lives will always feel like falling behind.", {"pose": "stand", "face": "sad"}),
        ("walk", "Write your own timeline today, and measure yourself against that one instead.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "There is no late. There's only a path nobody else has walked yet.", {}),

        ("chapter", "Five. Burnout Looks Like Laziness.", {"num": "5", "title": "BURNOUT DISGUISED AS LAZINESS"}),
        ("solo", "Sometimes you're not behind. You're just running on an empty tank.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Exhaustion doesn't announce itself. It just looks like not trying.", {"text": "0%", "color": "accent"}),
        ("two", "You call it laziness. Your body is quietly screaming for rest.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "Pushing harder on an empty tank doesn't move you. It just stalls you longer.", {"pose": "think"}),
        ("point", "Rest isn't falling behind. Rest is how you stay in the race at all.", {"dir": "l"}),
        ("solo", "The version of you who rests today out-paces the one who burns out tomorrow.", {"pose": "stand", "face": "happy"}),
        ("walk", "Take the nap, the day off, the slow morning. It's not weakness.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "A refueled you moves faster than an exhausted you ever could.", {}),

        ("chapter", "Six. No Definition of Ahead.", {"num": "6", "title": "YOU HAVEN'T DEFINED 'AHEAD'"}),
        ("solo", "You can't win a race you've never actually defined the finish line for.", {"pose": "stand"}),
        ("label_above", "Ahead of who? At what? By whose scoreboard, exactly?", {"text": "?", "face": "neutral"}),
        ("two", "Ahead at thirty for you might just mean peace, not a promotion.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "Without your own definition, you'll always borrow someone else's, and lose by it.", {"pose": "think", "face": "sad"}),
        ("point", "Write down what 'ahead' actually means to you, specifically, this year.", {"dir": "r"}),
        ("solo", "Then measure yourself only against that one sentence, nothing else.", {"pose": "stand"}),
        ("walk", "Walk toward your own definition, even if it looks like standing still to others.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Behind only exists on a map you never agreed to follow.", {}),

        ("solo", "Six reasons the feeling is real, and six reasons the race isn't.", {"pose": "stand"}),
        ("crowd", "Almost everyone you envy is quietly comparing themselves to someone else too.", {}),
        ("solo", "You're not behind. You're just on a timeline nobody else can see.", {"pose": "reach", "face": "happy"}),
        ("cta", "What does 'ahead' actually mean to you? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 4 ===== #
BATCH.append((
    "lf_loneliness_epidemic",
    "6 Silent Signs of the Loneliness Epidemic",
    "You can be surrounded and still be alone.",
    "Mind Traps",
    [
        ("solo", "You can have a packed calendar and still feel completely alone.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Loneliness today doesn't look empty. It looks busy, and disconnected.", {}),
        ("solo", "It's quieter than it used to be, and that makes it more dangerous.", {"pose": "think"}),
        ("point", "Here are six silent signs hiding inside an ordinary, crowded week.", {"dir": "r"}),
        ("solo", "You might recognize more of these than you'd like to admit.", {"poses": ["stand", "reach"]}),
        ("stars", "None of this is your fault. All of it is worth noticing.", {}),
        ("solo", "Sign one starts the moment you walk into a packed room.", {"pose": "look_up"}),

        ("chapter", "One. Alone in a Crowd.", {"num": "1", "title": "SURROUNDED BUT STILL ALONE"}),
        ("crowd", "You're at a party, surrounded by people, scrolling your phone in the corner.", {}),
        ("solo", "You can name everyone here. None of them really know you.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Quantity of people was never the same thing as connection.", {"text": "?", "face": "neutral"}),
        ("two", "You have a hundred contacts and nobody to call at midnight.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("point", "A crowded room can still be the loneliest place you stand in.", {"dir": "l"}),
        ("solo", "Being around people was never the cure. Being known by them is.", {"pose": "think"}),
        ("walk", "Pick one person in that crowd and actually ask them something real.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "One real conversation beats a hundred polite ones, every time.", {}),

        ("chapter", "Two. Texting Replaced Visiting.", {"num": "2", "title": "TEXTING REPLACED VISITING"}),
        ("solo", "We replaced visits with calls, then calls with texts, then texts with likes.", {"pose": "stand"}),
        ("label_above", "Each upgrade felt easier. Each one connected us a little less.", {"text": "<3", "color": "muted"}),
        ("two", "A heart emoji takes one second. A real visit takes effort, and presence.", {"poseA": "wave", "poseB": "stand"}),
        ("solo", "We mistook constant contact for closeness. They were never the same thing.", {"pose": "think", "face": "sad"}),
        ("point", "Convenience quietly traded depth for speed, and nobody voted on it.", {"dir": "r"}),
        ("solo", "Call someone today instead of texting them. Let it feel inconvenient.", {"pose": "stand"}),
        ("walk", "Walk over instead of typing. Effort is what makes people feel chosen.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "The friendships that last are the ones still worth the effort.", {}),

        ("chapter", "Three. Rehearsed Conversations.", {"num": "3", "title": "REHEARSING CONVERSATIONS"}),
        ("solo", "You rehearse a conversation in your head with someone you'll never actually call.", {"pose": "think", "face": "sad"}),
        ("label_above", "An entire imaginary friendship, playing out in total silence.", {"text": "...", "face": "neutral"}),
        ("two", "You know exactly what they'd say. You've just never tested it out loud.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "This is your mind trying to meet a need your life isn't currently meeting.", {"pose": "think"}),
        ("point", "The rehearsal feels safe. The actual call feels terrifying. Make the call anyway.", {"dir": "l"}),
        ("solo", "Real conversations are messier than the ones in your head. They're also real.", {"pose": "stand"}),
        ("walk", "Send the message you've been rehearsing instead of replaying it again.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "The version in your head can never hug you back. The real one can.", {}),

        ("chapter", "Four. Small Talk Is All That's Left.", {"num": "4", "title": "ONLY SMALL TALK LEFT"}),
        ("solo", "How are you, good and you, fine. The entire conversation, every single day.", {"pose": "stand"}),
        ("two", "Nobody asks what's actually going on underneath the polite weather report.", {"poseA": "shrug", "poseB": "stand"}),
        ("label_above", "Small talk is safe. It's also where real connection goes to die.", {"text": "...", "face": "sad"}),
        ("solo", "You can know someone for years and still know almost nothing real.", {"pose": "think", "face": "sad"}),
        ("point", "Ask one question deeper than the weather, and watch what happens.", {"dir": "r"}),
        ("solo", "Most people are starving for someone to ask them something that matters.", {"pose": "stand"}),
        ("walk", "Be the one who asks the real question first. Someone has to.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Depth doesn't happen by accident. Somebody has to go first.", {}),

        ("chapter", "Five. Missing People You're 'Friends' With.", {"num": "5", "title": "MISSING THE PEOPLE STILL HERE"}),
        ("solo", "You miss a friend you technically still talk to, almost every single week.", {"pose": "stand", "face": "sad"}),
        ("label_above", "The friendship still exists. The closeness quietly moved out.", {"text": "?", "color": "accent"}),
        ("two", "You're 'friends' on every app, and strangers in every conversation that matters.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Online friendship can quietly replace the kind that actually shows up.", {"pose": "think"}),
        ("point", "Notice who you're missing despite being technically connected to them.", {"dir": "l"}),
        ("solo", "That ache is information. It's telling you exactly who to call this week.", {"pose": "stand"}),
        ("walk", "Reach out to the friend you miss, even though the app says you're close.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "A real reunion beats a permanent 'friend' status every single time.", {}),

        ("chapter", "Six. Nobody Notices the Disappearing.", {"num": "6", "title": "NOBODY NOTICES YOU'RE GONE"}),
        ("solo", "You could go quiet for two weeks, and almost nobody would check in.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Silence used to trigger a phone call. Now it barely registers.", {"text": "0", "face": "neutral"}),
        ("two", "Everyone assumes someone else is checking on you. So nobody does.", {"poseA": "shrug", "poseB": "shrug"}),
        ("solo", "This isn't proof you're unlovable. It's proof everyone is just as overloaded.", {"pose": "think"}),
        ("point", "Be the person who checks in first, even badly, even awkwardly.", {"dir": "r"}),
        ("solo", "One text, 'thinking of you,' breaks the silence loop for someone today.", {"pose": "stand", "face": "happy"}),
        ("walk", "Send it to the person who's been quiet. Don't assume someone else will.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "The epidemic ends one unprompted message at a time. Start with one.", {}),

        ("solo", "Six silent signs, hiding in plain sight, inside a normal busy week.", {"pose": "stand"}),
        ("crowd", "Almost everyone around you is fighting this same quiet battle right now.", {}),
        ("solo", "You're not as alone in feeling alone as you think you are.", {"pose": "reach", "face": "happy"}),
        ("cta", "Text someone right now, before you finish reading this comment.", {}),
    ],
))

# ============================================================ VIDEO 5 ===== #
BATCH.append((
    "lf_mindset_shifts",
    "6 Mindset Shifts That Will Change How You See Everything",
    "Six sentences that rewrite how you see everything.",
    "Mindset Shifts",
    [
        ("solo", "Your whole life runs through a handful of sentences in your head.", {"pose": "think"}),
        ("point", "Change six sentences, and you quietly change how you see everything.", {"dir": "r"}),
        ("crowd", "Most people never even hear the sentences running their own mind.", {}),
        ("solo", "These six shifts won't change your circumstances. They'll change your lens.", {"pose": "stand"}),
        ("solo", "And the lens decides whether the same exact day feels heavy or light.", {"poses": ["stand", "reach"]}),
        ("stars", "Let's rewrite the sentences, one mindset shift at a time.", {}),
        ("solo", "Shift one starts with the most common sentence of them all.", {"pose": "look_up"}),

        ("chapter", "One. Victim to Author.", {"num": "1", "title": "FROM VICTIM TO AUTHOR"}),
        ("solo", "'This happened to me' feels true, and quietly hands away your power.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Victim asks: why me. Author asks: what now.", {"text": "->", "face": "neutral"}),
        ("two", "You didn't choose every chapter. You still get to write the next one.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "This isn't about blaming yourself. It's about reclaiming the pen.", {"pose": "think"}),
        ("point", "Ask 'what now' instead of 'why me,' and watch the story change direction.", {"dir": "l"}),
        ("solo", "Authors don't get easier plots. They just keep writing anyway.", {"pose": "stand"}),
        ("walk", "Pick up the pen on whatever happened to you today, and write the next line.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("celebrate", "You stopped being a character and became the one holding the pen.", {}),

        ("chapter", "Two. Perfect to Done.", {"num": "2", "title": "FROM PERFECT TO DONE"}),
        ("solo", "Perfect waits for the right time, the right mood, the right version of you.", {"pose": "think"}),
        ("label_above", "Perfect is patient. It will happily wait forever with you.", {"text": "0%", "color": "muted"}),
        ("two", "Done ships the rough draft, the awkward first attempt, today, not someday.", {"poseA": "reach", "poseB": "stand"}),
        ("solo", "Done can be improved. Perfect, sitting unfinished, can't be improved at all.", {"pose": "stand"}),
        ("point", "Ask 'is it done' instead of 'is it perfect,' and you'll finally finish things.", {"dir": "r"}),
        ("solo", "Every masterpiece you admire started as someone's embarrassing rough draft.", {"pose": "think"}),
        ("walk", "Ship the rough version today. Polish is a privilege of things that exist.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "Done and imperfect beats perfect and imaginary, every single time.", {}),

        ("chapter", "Three. Compare to Inspire.", {"num": "3", "title": "FROM COMPARE TO INSPIRE"}),
        ("solo", "Compare looks at someone ahead of you and feels smaller for it.", {"pose": "stand", "face": "sad"}),
        ("two", "Inspire looks at the exact same person and feels possibility instead.", {"poseA": "stand", "poseB": "celebrate", "faceB": "happy"}),
        ("label_above", "Same person. Same achievement. Completely different lens on it.", {"text": "=", "face": "neutral"}),
        ("solo", "The shift isn't about them. It's the question you ask about yourself.", {"pose": "think"}),
        ("point", "Ask 'what can I learn here' instead of 'why not me.'", {"dir": "l"}),
        ("solo", "Inspiration is comparison with the bitterness quietly filtered out.", {"pose": "stand"}),
        ("walk", "Next time envy shows up, ask it one question: what's it actually pointing at?", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "Envy, pointed in the right direction, becomes a map instead of a wound.", {}),

        ("chapter", "Four. Reaction to Response.", {"num": "4", "title": "FROM REACTION TO RESPONSE"}),
        ("solo", "Reaction is instant, automatic, and usually said with your worst voice.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Between the trigger and your words, there's a tiny gap.", {"text": "...", "face": "neutral"}),
        ("two", "Response lives in that gap, and chooses the words on purpose instead.", {"poseA": "think", "poseB": "stand"}),
        ("solo", "You can't always control what happens. You can control the half-second after.", {"pose": "think"}),
        ("point", "Breathe once before you speak, and watch which version of you shows up.", {"dir": "r"}),
        ("solo", "That tiny pause is the entire difference between regret and respect.", {"pose": "stand"}),
        ("walk", "Practice the pause today, on the smallest annoyance you can find.", {"x0": 0.35, "x1": 0.65}),
        ("stars", "The gap between trigger and response is where your character actually lives.", {}),

        ("chapter", "Five. Scarcity to Enough.", {"num": "5", "title": "FROM SCARCITY TO ENOUGH"}),
        ("solo", "Scarcity counts what's missing before it ever counts what's already here.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Enough doesn't mean nothing's missing. It means today still counts.", {"text": "+", "face": "neutral"}),
        ("two", "Scarcity chases more, forever. Enough enjoys what's here, then chases more too.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "The shift isn't lowering your ambition. It's raising your gratitude alongside it.", {"pose": "think"}),
        ("point", "Ask 'what do I already have' before you ask 'what do I still need.'", {"dir": "l"}),
        ("solo", "Both questions can live in the same sentence, in the same breath.", {"pose": "stand"}),
        ("walk", "Name one thing that's enough right now, even while you build toward more.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("celebrate", "Enough isn't the finish line. It's just permission to enjoy the run.", {}),

        ("chapter", "Six. Someday to Today.", {"num": "6", "title": "FROM SOMEDAY TO TODAY"}),
        ("solo", "Someday is a day that never actually appears on any calendar.", {"pose": "stand"}),
        ("label_above", "Someday has never once shown up on a Tuesday. Not once.", {"text": "?", "color": "accent"}),
        ("two", "Today is the only day that has ever existed for anyone, ever.", {"poseA": "stand", "poseB": "reach"}),
        ("solo", "Every 'someday' plan quietly waiting is a today plan you're avoiding.", {"pose": "think", "face": "sad"}),
        ("point", "Ask what tiny piece of 'someday' you could start in the next hour.", {"dir": "r"}),
        ("solo", "You don't need the whole plan today. You just need the first inch of it.", {"pose": "stand"}),
        ("walk", "Take that one inch right now, before today turns into another someday.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Someday was always just today, wearing a disguise to feel less urgent.", {}),

        ("solo", "Six sentences. Same life, same circumstances, completely different lens.", {"pose": "stand"}),
        ("crowd", "Everyone has access to these same six shifts, starting right now.", {}),
        ("solo", "Pick one shift and run it through tomorrow morning before anything else.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which shift do you need most this week? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 6 ===== #
BATCH.append((
    "lf_smart_procrastinate",
    "Why Smart People Procrastinate More Than Anyone Else",
    "Smart people procrastinate the most. Here's why.",
    "Mind Traps",
    [
        ("solo", "The smartest people you know are often the biggest procrastinators around.", {"pose": "stand", "face": "surprised"}),
        ("crowd", "It's not laziness. It's something far stranger going on underneath.", {}),
        ("solo", "Intelligence doesn't prevent procrastination. In some ways, it quietly fuels it.", {"pose": "think"}),
        ("point", "Here are six reasons smart people stall on the things that matter most.", {"dir": "r"}),
        ("solo", "You might recognize yourself in more than one of these.", {"poses": ["stand", "reach"]}),
        ("stars", "None of this means you're broken. It means you're predictable.", {}),
        ("solo", "Reason one is a trap disguised as a virtue.", {"pose": "look_up"}),

        ("chapter", "One. Perfectionism in Disguise.", {"num": "1", "title": "PERFECTIONISM DISGUISED AS LAZY"}),
        ("solo", "If it can't be done perfectly, some part of you decides not to start.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Not starting feels safer than starting and falling short.", {"text": "0%", "color": "muted"}),
        ("two", "From the outside it looks like laziness. Inside, it's fear wearing a disguise.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "Smart people have higher standards, which makes the gap feel scarier.", {"pose": "think"}),
        ("point", "Lower the bar to 'just start badly,' and the fear loses its grip.", {"dir": "l"}),
        ("solo", "A messy first attempt is infinitely more valuable than a flawless idea.", {"pose": "stand"}),
        ("walk", "Open the document and write one bad sentence. That's the whole trick.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "The bad sentence becomes a good one. The blank page never does.", {}),

        ("chapter", "Two. Afraid of Their Own Limits.", {"num": "2", "title": "AFRAID TO FIND THEIR LIMIT"}),
        ("solo", "If you never really try, you never find out where your ceiling is.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Untested potential feels infinite. Tested potential has an actual number.", {"text": "?", "face": "neutral"}),
        ("two", "Some smart people protect the comforting idea of 'I could, if I wanted.'", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Procrastination keeps that fantasy alive a little longer, untested.", {"pose": "think"}),
        ("point", "The fear isn't failing. It's discovering the real ceiling, finally, for sure.", {"dir": "r"}),
        ("solo", "But a real ceiling you can push against beats an imaginary one you can't.", {"pose": "stand"}),
        ("walk", "Test the limit on something small today. The fear shrinks once it's real.", {"x0": 0.3, "x1": 0.7, "face": "think"}),
        ("stars", "A known limit is something you can train. An imagined one just haunts you.", {}),

        ("chapter", "Three. Too Many Options.", {"num": "3", "title": "TOO MANY OPTIONS, NO FILTER"}),
        ("solo", "Smart minds generate options fast, often faster than they can choose between them.", {"pose": "think"}),
        ("label_above", "Five great paths and no decision is worse than one okay path.", {"text": "5", "color": "accent"}),
        ("two", "Every option looks equally appealing, which quietly cancels all of them out.", {"poseA": "shrug", "poseB": "shrug"}),
        ("solo", "Analysis feels productive. It often just delays the only thing that counts.", {"pose": "stand", "face": "sad"}),
        ("point", "Pick the option that's good enough, and move, instead of the perfect one.", {"dir": "l"}),
        ("solo", "Momentum reveals more than analysis ever will. Movement teaches you faster.", {"pose": "stand"}),
        ("walk", "Choose any reasonable option in the next sixty seconds and start walking.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "A decent plan in motion beats a perfect plan still sitting on paper.", {}),

        ("chapter", "Four. Overestimating Future Motivation.", {"num": "4", "title": "OVERESTIMATING FUTURE MOTIVATION"}),
        ("solo", "Future you, in your imagination, is always more disciplined than today's you.", {"pose": "stand"}),
        ("label_above", "Tomorrow's motivation is a fantasy you've never actually met.", {"text": "?", "face": "neutral"}),
        ("two", "Smart people trust their planning brain over their actual track record.", {"poseA": "think", "poseB": "stand"}),
        ("solo", "But future you will feel exactly as tired and distracted as today's you.", {"pose": "stand", "face": "sad"}),
        ("point", "Plan for today's energy level, not an imaginary upgraded version of yourself.", {"dir": "r"}),
        ("solo", "If it matters, do the smallest version of it now, while you remember why.", {"pose": "stand"}),
        ("walk", "Do five minutes today instead of betting on sixty minutes tomorrow.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Today's small effort always beats tomorrow's imaginary large one.", {}),

        ("chapter", "Five. Bored by Anything Beneath Them.", {"num": "5", "title": "BORED BENEATH THEM"}),
        ("solo", "Smart people get bored fast with tasks that don't challenge them enough.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Boredom feels like a verdict. It's usually just a mismatch.", {"text": "x", "color": "muted"}),
        ("two", "The boring step is still required, even if it isn't intellectually exciting.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "Skipping the boring foundation is how brilliant ideas quietly collapse later.", {"pose": "think"}),
        ("point", "Make the boring task a game: a timer, a reward, a small challenge.", {"dir": "l"}),
        ("solo", "You don't need to love the step. You just need to survive it once.", {"pose": "stand"}),
        ("walk", "Set a ten-minute timer and just survive the boring part today.", {"x0": 0.35, "x1": 0.65}),
        ("celebrate", "On the other side of boring is usually the part you actually wanted.", {}),

        ("chapter", "Six. Thinking Instead of Doing.", {"num": "6", "title": "MISTAKING THINKING FOR DOING"}),
        ("solo", "Smart people can spend hours thinking about a task and call it progress.", {"pose": "think"}),
        ("label_above", "Thinking feels productive. It often produces exactly nothing.", {"text": "0", "face": "neutral"}),
        ("two", "A brilliant plan in your head has the same real-world value as no plan.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Ideas don't compound. Actions do. That's the entire, unglamorous secret.", {"pose": "stand"}),
        ("point", "Trade one hour of thinking for ten minutes of clumsy, real action.", {"dir": "r"}),
        ("solo", "The action will teach you more than the thinking ever could alone.", {"pose": "stand", "face": "happy"}),
        ("walk", "Stop planning this video idea, and go do one small version of it now.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "Six traps, all built on intelligence working against itself.", {}),

        ("solo", "Being smart was never the problem. Believing the stalling is the issue.", {"pose": "stand"}),
        ("crowd", "Everyone smart enough to relate to this is smart enough to fix it too.", {}),
        ("solo", "Pick the smallest task you've been avoiding, and start it badly, right now.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which one of these six is your exact flavor of stalling? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 7 ===== #
BATCH.append((
    "lf_mental_health_habits",
    "6 Habits That Are Secretly Destroying Your Mental Health",
    "This ordinary habit is quietly wrecking you.",
    "Mind Traps",
    [
        ("solo", "Some of your most normal daily habits are quietly wrecking your mind.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Nobody warns you, because everyone around you is doing them too.", {}),
        ("solo", "None of these look dangerous. That's exactly why they work so well.", {"pose": "think"}),
        ("point", "Here are six of the quietest mental health killers in modern life.", {"dir": "r"}),
        ("solo", "You're probably doing at least two of these right now, today.", {"poses": ["stand", "reach"]}),
        ("stars", "Awareness alone won't fix them. But it's where fixing them starts.", {}),
        ("solo", "Habit one happens in the last hour before you fall asleep.", {"pose": "look_up"}),

        ("chapter", "One. Doomscrolling Before Bed.", {"num": "1", "title": "DOOMSCROLLING BEFORE BED"}),
        ("solo", "You tell yourself five more minutes. Forty minutes later, you're still scrolling.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Blue light and bad news, right before you try to sleep.", {"text": "!", "color": "accent"}),
        ("two", "Your brain absorbs the world's worst headlines, then tries to power down.", {"poseA": "think", "poseB": "stand"}),
        ("solo", "It rarely works. You fall asleep anxious and wake up groggy.", {"pose": "stand", "face": "sad"}),
        ("point", "Charge your phone outside the bedroom for one week. Just try it.", {"dir": "l"}),
        ("solo", "Your last thought of the day shouldn't be a stranger's worst moment.", {"pose": "think"}),
        ("walk", "Replace the last ten minutes of scrolling with literally anything else tonight.", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "Tomorrow's mood starts with tonight's last ten minutes. Choose them carefully.", {}),

        ("chapter", "Two. Comparing Life to a Feed.", {"num": "2", "title": "COMPARING LIFE TO A FEED"}),
        ("solo", "You measure your actual life against everyone else's carefully edited highlight reel.", {"pose": "stand"}),
        ("label_above", "An edited reel was never a fair opponent for real life.", {"text": "?", "face": "sad"}),
        ("two", "Their best ten seconds against your full, messy twenty-four hours.", {"poseA": "celebrate", "poseB": "stand", "colorB": "muted"}),
        ("solo", "This comparison was rigged before you even opened the app.", {"pose": "think", "face": "sad"}),
        ("point", "Mute accounts that make you feel small. Your feed is yours to curate.", {"dir": "r"}),
        ("solo", "You wouldn't invite a person who makes you feel small into your home.", {"pose": "stand"}),
        ("walk", "Don't let them live rent-free in your pocket either. Clean the feed.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "A curated feed protects the same mind a curated home protects.", {}),

        ("chapter", "Three. Saying Yes When You Mean No.", {"num": "3", "title": "SAYING YES WHEN YOU MEAN NO"}),
        ("solo", "You agree to plans, favors, and projects you have zero actual energy for.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Every fake yes quietly borrows energy from somewhere else in you.", {"text": "-", "color": "accent"}),
        ("two", "You avoid one small awkward moment now, and pay for it for days.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "People-pleasing isn't kindness. It's a loan against your own well-being.", {"pose": "think"}),
        ("point", "Practice one honest 'I can't this time,' and notice you survive it.", {"dir": "l"}),
        ("solo", "The relationships that can't survive your honest no were never that solid.", {"pose": "stand"}),
        ("walk", "Say the real no this week, even if your voice shakes a little.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "Your energy is a budget. Spend it on what you actually meant to.", {}),

        ("chapter", "Four. Skipping Meals to Stay Productive.", {"num": "4", "title": "SKIPPING MEALS FOR 'PRODUCTIVITY'"}),
        ("solo", "You skip lunch to push through one more task, and call it discipline.", {"pose": "stand"}),
        ("label_above", "A starved brain doesn't focus harder. It just focuses worse.", {"text": "0", "face": "neutral"}),
        ("two", "Low blood sugar shows up disguised as irritability, fog, and doom.", {"poseA": "shrug", "poseB": "stand", "colorB": "muted"}),
        ("solo", "You're not lazy at 3 p.m. You're just running on fumes.", {"pose": "think", "face": "sad"}),
        ("point", "Eat the actual meal. The task will still be there in twenty minutes.", {"dir": "r"}),
        ("solo", "A fed brain solves in twenty minutes what a starved one fights for an hour.", {"pose": "stand"}),
        ("walk", "Step away and eat something real before your next task today.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Productivity built on skipped meals is just borrowed energy with interest.", {}),

        ("chapter", "Five. Bottling Up Instead of Talking.", {"num": "5", "title": "BOTTLING UP INSTEAD OF TALKING"}),
        ("solo", "You decide it's not a big deal, and swallow it down, again.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Unspoken feelings don't disappear. They just go underground.", {"text": "...", "face": "sad"}),
        ("two", "Eventually they leak out sideways, on the person who least deserves it.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Bottling it up feels like strength. It's usually just delayed weakness.", {"pose": "think"}),
        ("point", "Say the small true thing to someone, before it becomes a big one.", {"dir": "l"}),
        ("solo", "A feeling spoken out loud loses about half its weight immediately.", {"pose": "stand", "face": "happy"}),
        ("walk", "Tell one person one true thing today, even if it feels small.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "The bottle was never as strong as the words you were afraid to say.", {}),

        ("chapter", "Six. Treating Rest as Laziness.", {"num": "6", "title": "TREATING REST LIKE LAZINESS"}),
        ("solo", "You feel guilty resting unless you've earned it with enough exhaustion first.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Rest isn't a reward for burnout. It's prevention for it.", {"text": "+", "face": "neutral"}),
        ("two", "Productivity culture sold you the idea that stillness equals weakness.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "But machines that never rest break down. You're not built differently.", {"pose": "think"}),
        ("point", "Schedule rest like a meeting you can't cancel on yourself.", {"dir": "r"}),
        ("solo", "Rested you gets more done in fewer hours than exhausted you ever will.", {"pose": "stand", "face": "happy"}),
        ("walk", "Take the rest today, without earning it first. It's allowed.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "Rest isn't the opposite of ambition. It's what makes ambition sustainable.", {}),

        ("solo", "Six quiet habits, all wearing the disguise of completely normal life.", {"pose": "stand"}),
        ("crowd", "Almost everyone watching this is guilty of at least three of them.", {}),
        ("solo", "Pick the one habit you'll change this week, and just change that one.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which habit hit closest to home? Be honest in the comments.", {}),
    ],
))

# ============================================================ VIDEO 8 ===== #
BATCH.append((
    "lf_rock_bottom_lessons",
    "6 Lessons Hitting Rock Bottom Teaches You That Success Never Will",
    "Rock bottom taught me things success never could.",
    "Hard Truths",
    [
        ("solo", "Rock bottom is brutal. It's also the most honest teacher you'll ever have.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Success can be faked, performed, photographed. Rock bottom can't.", {}),
        ("solo", "That's exactly why it teaches lessons no achievement ever quite reaches.", {"pose": "think"}),
        ("point", "Here are six things hitting bottom taught me that winning never did.", {"dir": "r"}),
        ("solo", "If you're down there right now, this one's especially for you.", {"poses": ["stand", "reach"]}),
        ("stars", "None of this means rock bottom is good. It means it's honest.", {}),
        ("solo", "Lesson one shows up the moment the applause stops.", {"pose": "look_up"}),

        ("chapter", "One. Who Actually Stays.", {"num": "1", "title": "WHO ACTUALLY STAYS"}),
        ("solo", "Success fills a room with people. Rock bottom empties it instantly.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Most of the crowd was there for what you had, not who you are.", {}),
        ("label_above", "The room gets smaller. The people left get realer.", {"text": "-", "color": "muted"}),
        ("two", "One or two people stay anyway, with nothing to gain from staying.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
        ("point", "Those are the only names worth keeping after everything else clears out.", {"dir": "l"}),
        ("solo", "You finally learn your real net worth, measured in people, not money.", {"pose": "stand"}),
        ("walk", "Walk toward the ones who stayed. They already proved everything.", {"x0": 0.4, "x1": 0.6, "face": "happy"}),
        ("celebrate", "A smaller circle of real people beats a packed room of fans.", {}),

        ("chapter", "Two. How Little You Need.", {"num": "2", "title": "HOW LITTLE YOU TRULY NEED"}),
        ("solo", "Rock bottom strips away everything that wasn't actually necessary to survive.", {"pose": "stand"}),
        ("label_above", "What's left, when almost everything is gone, is the real list.", {"text": "1", "face": "neutral"}),
        ("two", "Food, shelter, one person who believes in you. The list is shorter than you thought.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "Success never forces you to find that list. Rock bottom hands it to you.", {"pose": "think"}),
        ("point", "Once you know your floor, the fear of falling shrinks dramatically.", {"dir": "r"}),
        ("solo", "You stop white-knuckling things you now know you could live without.", {"pose": "stand", "face": "happy"}),
        ("walk", "Carry the short list forward, even once you're climbing back up.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "Knowing your floor is the strangest kind of freedom there is.", {}),

        ("chapter", "Three. Your Real Pain Tolerance.", {"num": "3", "title": "YOUR REAL TOLERANCE FOR PAIN"}),
        ("solo", "You always assumed a certain hardship would break you completely.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Then it happened. And somehow, you were still standing.", {"text": "!", "face": "surprised"}),
        ("two", "Success never tests this number. It just lets you guess at it.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Rock bottom gives you the actual number, measured, not imagined.", {"pose": "think"}),
        ("point", "Whatever you survived becomes the new floor of what you fear.", {"dir": "l"}),
        ("solo", "You can't unknow that you're tougher than you gave yourself credit for.", {"pose": "stand"}),
        ("walk", "Carry that proof with you the next time fear tries to stop you.", {"x0": 0.35, "x1": 0.65, "face": "happy"}),
        ("celebrate", "You're not as fragile as the version of you who hadn't been tested yet.", {}),

        ("chapter", "Four. What You Were Avoiding.", {"num": "4", "title": "WHAT YOU WERE AVOIDING"}),
        ("solo", "Rock bottom usually arrives carrying a problem you'd been avoiding for years.", {"pose": "stand", "face": "sad"}),
        ("label_above", "The bill always comes due. Rock bottom is just the due date.", {"text": "$", "color": "accent"}),
        ("two", "Success let you outrun the issue. Bottom finally makes you face it.", {"poseA": "stand", "poseB": "think"}),
        ("solo", "It's not a punishment. It's the conversation you kept postponing.", {"pose": "think"}),
        ("point", "Name the exact thing you were avoiding, out loud, to one person.", {"dir": "r"}),
        ("solo", "Facing it down here is brutal. Avoiding it forever would have been worse.", {"pose": "stand"}),
        ("walk", "Walk toward the thing you've been avoiding, now that there's nowhere left to run.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "What broke you open is often exactly what needed addressing.", {}),

        ("chapter", "Five. How to Rebuild From Nothing.", {"num": "5", "title": "HOW TO REBUILD FROM NOTHING"}),
        ("solo", "From nothing, every tiny win counts again, the way it did at the very start.", {"pose": "stand", "face": "happy"}),
        ("label_above", "Getting out of bed becomes a real, countable victory again.", {"text": "+1", "color": "accent"}),
        ("two", "Success skips this. It hands you momentum you never had to build twice.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "Rebuilding teaches you the actual mechanics of how anything gets built at all.", {"pose": "think"}),
        ("point", "One small brick a day. That's the entire secret, repeated patiently.", {"dir": "l"}),
        ("solo", "You stop needing a miracle. You just need tomorrow's one brick.", {"pose": "stand"}),
        ("walk", "Lay one brick today. Don't worry yet about the whole building.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("celebrate", "Rebuilders end up sturdier than people who never had to rebuild at all.", {}),

        ("chapter", "Six. What You're Actually Capable Of.", {"num": "6", "title": "WHAT YOU'RE ACTUALLY CAPABLE OF"}),
        ("solo", "Before the fall, your capability was just a guess, untested and comfortable.", {"pose": "stand"}),
        ("label_above", "After the fall, it's a fact, earned the hard way.", {"text": "✓", "color": "accent"}),
        ("two", "Success lets you wonder if you're strong. Rock bottom proves it.", {"poseA": "stand", "poseB": "celebrate", "faceB": "happy"}),
        ("solo", "You now know things about your own strength that comfort could never teach.", {"pose": "think"}),
        ("point", "Whatever comes next, you already know you can survive worse than this.", {"dir": "r"}),
        ("solo", "That knowledge doesn't leave once you've climbed back to solid ground.", {"pose": "stand"}),
        ("walk", "Walk forward carrying proof, not just hope, of what you can handle.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Rock bottom was brutal. It also handed you something success never could.", {}),

        ("solo", "Six lessons, all paid for the hard way, none of them refundable.", {"pose": "stand"}),
        ("crowd", "Everyone who's been down there carries a version of this same proof.", {}),
        ("solo", "If you're down there now, you're not failing. You're being taught.", {"pose": "reach", "face": "happy"}),
        ("cta", "What did your own rock bottom teach you? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 9 ===== #
BATCH.append((
    "lf_comparing_yourself",
    "The Real Reason You Can't Stop Comparing Yourself to Others",
    "Your brain was built to compare. Here's why.",
    "Mind Traps",
    [
        ("solo", "You promise yourself you'll stop comparing. Then you open the app anyway.", {"pose": "stand", "face": "sad"}),
        ("crowd", "Almost every single person scrolling right now is doing the exact same thing.", {}),
        ("solo", "It's not a willpower problem. It's a setting your brain was built with.", {"pose": "think"}),
        ("point", "Here's the real reason comparison won't let go of you, in six parts.", {"dir": "r"}),
        ("solo", "By the end, you'll understand the urge instead of just fighting it blind.", {"poses": ["stand", "reach"]}),
        ("stars", "Understanding it doesn't erase it. It does make it far less scary.", {}),
        ("solo", "Part one goes back further than any app, any feed, any screen.", {"pose": "look_up"}),

        ("chapter", "One. A Survival Instinct.", {"num": "1", "title": "COMPARISON IS A SURVIVAL INSTINCT"}),
        ("solo", "For most of human history, knowing your rank in the tribe kept you alive.", {"pose": "stand"}),
        ("crowd", "Status meant food, safety, a mate, a place by the fire.", {}),
        ("label_above", "Your brain still runs that ancient ranking software today.", {"text": "#", "face": "neutral"}),
        ("solo", "It just has no idea the tribe is now eight billion strangers online.", {"pose": "think", "face": "sad"}),
        ("point", "The instinct isn't broken. It's just running on the wrong battlefield now.", {"dir": "l"}),
        ("solo", "Knowing it's ancient hardware makes it feel less like a personal flaw.", {"pose": "stand"}),
        ("walk", "Notice the ranking instinct fire today, and just name it for what it is.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "You're not broken. You're a stone-age brain in a modern feed.", {}),

        ("chapter", "Two. A Brain Built for a Village.", {"num": "2", "title": "BUILT FOR A VILLAGE, NOT A FEED"}),
        ("solo", "Your brain evolved to compare you to maybe a hundred and fifty people.", {"pose": "stand"}),
        ("label_above", "Today it compares you to millions, every single scroll.", {"text": "150", "color": "muted"}),
        ("two", "In the village, you were probably above average at something, visibly.", {"poseA": "celebrate", "poseB": "stand"}),
        ("solo", "Online, there's always someone richer, fitter, funnier, one swipe away.", {"pose": "stand", "face": "sad"}),
        ("point", "The math was never designed to survive a pool this large.", {"dir": "r"}),
        ("solo", "Shrinking your feed is shrinking the comparison pool back to something survivable.", {"pose": "think"}),
        ("walk", "Trim your feed down to a village-sized pool of people who actually matter.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "A smaller, kinder village beats an infinite, brutal feed.", {}),

        ("chapter", "Three. Highlight Reel vs Behind the Scenes.", {"num": "3", "title": "HIGHLIGHT REEL VS BEHIND THE SCENES"}),
        ("solo", "You compare your full footage to everyone else's ten best edited seconds.", {"pose": "stand"}),
        ("label_above", "Behind every glowing photo is a person just like you.", {"text": "?", "face": "sad"}),
        ("two", "Doubt, debt, arguments, none of it makes the post. All of it is real.", {"poseA": "stand", "poseB": "stand", "colorB": "muted"}),
        ("solo", "This isn't a fair fight. It was rigged before you opened the app.", {"pose": "think"}),
        ("point", "Remind yourself: this is their highlight reel, not their whole life.", {"dir": "l"}),
        ("solo", "You'd never compare your blooper reel to someone's award speech either.", {"pose": "stand"}),
        ("walk", "Catch the comparison mid-scroll and name what you're actually comparing.", {"x0": 0.4, "x1": 0.6}),
        ("celebrate", "Naming the unfair fight is often enough to quietly end it.", {}),

        ("chapter", "Four. Status Anxiety Is Ancient.", {"num": "4", "title": "STATUS ANXIETY IS ANCIENT"}),
        ("solo", "Philosophers were writing about status anxiety long before any screen existed.", {"pose": "think"}),
        ("label_above", "This isn't a modern glitch. It's an old, old human ache.", {"text": "~", "face": "neutral"}),
        ("two", "Kings worried about other kings. Villagers worried about other villagers.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "Technology didn't invent the wound. It just handed it a megaphone.", {"pose": "stand", "face": "sad"}),
        ("point", "Knowing it's ancient means you're not uniquely weak for feeling it.", {"dir": "r"}),
        ("solo", "Every generation has fought this fight, with whatever tools they had.", {"pose": "stand"}),
        ("walk", "Pick up the tools this generation has: boundaries, breaks, honest self-talk.", {"x0": 0.3, "x1": 0.7}),
        ("stars", "You're not failing a modern test. You're fighting a very old battle, well.", {}),

        ("chapter", "Five. No Finish Line.", {"num": "5", "title": "COMPARISON HAS NO FINISH LINE"}),
        ("solo", "Even people who 'win' the comparison game find someone new to compare to.", {"pose": "stand", "face": "sad"}),
        ("label_above", "There is no rank where comparison finally stops on its own.", {"text": "∞", "color": "accent"}),
        ("two", "Billionaires compare yachts. New parents compare milestones. It never ends.", {"poseA": "stand", "poseB": "stand"}),
        ("solo", "Winning the game doesn't end the game. It just moves the goalpost.", {"pose": "think"}),
        ("point", "The only real exit is stepping off the track, not running faster on it.", {"dir": "l"}),
        ("solo", "You can quit a race that was never going to declare a winner.", {"pose": "stand"}),
        ("walk", "Step off the track today, even just for one quiet afternoon.", {"x0": 0.4, "x1": 0.6, "face": "happy"}),
        ("celebrate", "Off the track, there's no rank. There's just your actual life.", {}),

        ("chapter", "Six. Turning Comparison Into Fuel.", {"num": "6", "title": "TURNING COMPARISON INTO FUEL"}),
        ("solo", "You can't delete the instinct. You can redirect where it points.", {"pose": "stand"}),
        ("label_above", "Same spark, pointed at action instead of self-attack.", {"text": "->", "face": "neutral"}),
        ("two", "Instead of 'why not me,' try 'what would it take to get there.'", {"poseA": "think", "poseB": "reach"}),
        ("solo", "That tiny rewording turns envy into the closest thing to a roadmap.", {"pose": "stand", "face": "happy"}),
        ("point", "The next time comparison stings, ask it what it's actually pointing toward.", {"dir": "r"}),
        ("solo", "It usually knows exactly what you want, before you've admitted it.", {"pose": "think"}),
        ("walk", "Take one small step toward what your envy was quietly pointing at.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "The same instinct that wounds you can also point you home.", {}),

        ("solo", "Six reasons, all tracing back to one old, misfiring instinct.", {"pose": "stand"}),
        ("crowd", "Everyone scrolling right now is fighting this exact same ancient pull.", {}),
        ("solo", "You can't switch it off. You can choose what you do with it.", {"pose": "reach", "face": "happy"}),
        ("cta", "What is your comparison instinct actually pointing you toward? Tell me below.", {}),
    ],
))

# ============================================================ VIDEO 10 ==== #
BATCH.append((
    "lf_emotional_maturity",
    "6 Signs You're More Emotionally Mature Than You Realize",
    "You might be more grown than you give yourself credit for.",
    "Mindset Shifts",
    [
        ("solo", "Emotional maturity rarely feels like a trophy. It usually feels like nothing.", {"pose": "stand"}),
        ("crowd", "Most mature people quietly assume everyone else has it figured out too.", {}),
        ("solo", "You might be doing the hard, invisible work without ever naming it.", {"pose": "think"}),
        ("point", "Here are six quiet signs you're more grown than you give yourself credit for.", {"dir": "r"}),
        ("solo", "Some of these might describe you on your hardest days, not your best ones.", {"poses": ["stand", "reach"]}),
        ("stars", "Maturity was never about feeling calm. It's about what you do anyway.", {}),
        ("solo", "Sign one shows up the moment you've made a mistake.", {"pose": "look_up"}),

        ("chapter", "One. Apologize Without Excuses.", {"num": "1", "title": "APOLOGIZE WITHOUT EXCUSES"}),
        ("solo", "You say 'I was wrong,' full stop, instead of 'I was wrong, but.'", {"pose": "stand"}),
        ("label_above", "No 'but.' No explanation tacked on to soften the blow.", {"text": "✓", "color": "accent"}),
        ("two", "It costs your ego something. You pay it anyway, because the bond matters more.", {"poseA": "stand", "poseB": "wave", "faceB": "happy"}),
        ("solo", "Most people apologize for the reaction, not the actual thing they did.", {"pose": "think", "face": "sad"}),
        ("point", "A clean apology, no defense attached, is rarer than people think.", {"dir": "l"}),
        ("solo", "If you can do this, you're already ahead of most adults you know.", {"pose": "stand", "face": "happy"}),
        ("walk", "Practice it this week: one clean apology, with zero attached 'but.'", {"x0": 0.3, "x1": 0.7}),
        ("celebrate", "That clean apology is doing more repair than you realize.", {}),

        ("chapter", "Two. Sit With Discomfort.", {"num": "2", "title": "YOU CAN SIT WITH DISCOMFORT"}),
        ("solo", "You can feel anxious, awkward, or sad, and not immediately reach for an escape.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Not numbing it. Not fixing it instantly. Just sitting with it.", {"text": "...", "face": "neutral"}),
        ("two", "Most people scroll, snack, or argue their way out of an uncomfortable feeling.", {"poseA": "shrug", "poseB": "stand"}),
        ("solo", "Sitting with it, instead of fleeing it, is a quiet, unglamorous skill.", {"pose": "think"}),
        ("point", "Discomfort tolerated, even briefly, builds a strength avoidance never could.", {"dir": "r"}),
        ("solo", "You don't need to enjoy the feeling. You just need to not run from it.", {"pose": "stand"}),
        ("walk", "Next uncomfortable moment, stay in it ten extra seconds before reacting.", {"x0": 0.4, "x1": 0.6}),
        ("stars", "Ten extra seconds of staying is where real maturity quietly lives.", {}),

        ("chapter", "Three. Don't Need to Win Every Argument.", {"num": "3", "title": "DON'T NEED TO WIN EVERY ARGUMENT"}),
        ("solo", "You can let a small disagreement go, even when you're technically right.", {"pose": "stand"}),
        ("label_above", "Being right and being kind aren't always the same move.", {"text": "=", "face": "neutral"}),
        ("two", "You ask, is this worth the relationship, before you ask, am I right.", {"poseA": "think", "poseB": "stand"}),
        ("solo", "Most people can't resist the last word. You can, and you do.", {"pose": "stand", "face": "happy"}),
        ("point", "Winning a small argument can quietly lose a much bigger thing.", {"dir": "l"}),
        ("solo", "Choosing the relationship over the point is a trade only mature people make.", {"pose": "stand"}),
        ("walk", "Let one small thing go this week, on purpose, without resentment.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("celebrate", "The relationship you protected is worth more than the point you dropped.", {}),

        ("chapter", "Four. Set Boundaries Without Guilt.", {"num": "4", "title": "BOUNDARIES WITHOUT GUILT"}),
        ("solo", "You say no, and you don't spend the next hour apologizing for it.", {"pose": "stand"}),
        ("label_above", "A boundary stated once, without a paragraph of excuses.", {"text": "STOP", "color": "accent"}),
        ("two", "Less mature versions of you would over-explain, then quietly resent saying yes.", {"poseA": "shrug", "poseB": "stand", "colorB": "muted"}),
        ("solo", "A boundary isn't an attack. It's information about what you can actually carry.", {"pose": "think"}),
        ("point", "People who respect you will respect the boundary too, eventually.", {"dir": "r"}),
        ("solo", "The ones who don't were testing the boundary's existence, not its wording.", {"pose": "stand"}),
        ("walk", "State one boundary plainly this week, and let the guilt pass through.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "A boundary without guilt is one of the clearest signs of growth there is.", {}),

        ("chapter", "Five. Let Go of What You Can't Control.", {"num": "5", "title": "LETTING GO OF THE UNCONTROLLABLE"}),
        ("solo", "You catch yourself spiraling over something you have zero power to change.", {"pose": "stand", "face": "sad"}),
        ("label_above", "Then, instead of spiraling further, you actually let it go.", {"text": "->", "face": "neutral"}),
        ("two", "Less mature you would replay it for hours, hunting for a different outcome.", {"poseA": "think", "poseB": "stand", "colorB": "muted"}),
        ("solo", "This version of you asks one question: can I actually change this right now.", {"pose": "think"}),
        ("point", "If the answer is no, you redirect the energy somewhere it can help.", {"dir": "l"}),
        ("solo", "That redirection, repeated daily, is most of what people call wisdom.", {"pose": "stand"}),
        ("walk", "Name one uncontrollable thing today, and physically walk away from holding it.", {"x0": 0.4, "x1": 0.6, "face": "happy"}),
        ("celebrate", "Letting go of the unchangeable frees up energy for the changeable.", {}),

        ("chapter", "Six. Celebrate Others Without Comparing.", {"num": "6", "title": "CELEBRATE OTHERS WITHOUT COMPARING"}),
        ("solo", "A friend shares good news, and your first feeling is genuine joy, not envy.", {"pose": "stand", "face": "happy"}),
        ("label_above", "No quiet math running underneath about your own scoreboard.", {"text": "+1", "color": "accent"}),
        ("two", "Less mature you would smile outwardly while comparing inwardly, instantly.", {"poseA": "shrug", "poseB": "celebrate", "faceB": "happy"}),
        ("solo", "This version of you can be happy for them without it costing you anything.", {"pose": "stand"}),
        ("point", "That's not naivety. That's a scarcity instinct you've already outgrown.", {"dir": "r"}),
        ("solo", "Someone else's win was never subtracted from your own. It never is.", {"pose": "think", "face": "happy"}),
        ("walk", "Celebrate someone today, loudly, with zero quiet comparison attached.", {"x0": 0.3, "x1": 0.7, "face": "happy"}),
        ("stars", "Joy that doesn't compete with anyone else's is rare, and it's yours.", {}),

        ("solo", "Six signs, all quiet, all easy to miss in yourself.", {"pose": "stand"}),
        ("crowd", "Almost everyone doing these things assumes it's nothing special. It is.", {}),
        ("solo", "You're probably more grown than the voice in your head gives you credit for.", {"pose": "reach", "face": "happy"}),
        ("cta", "Which of these six already sounds like you? Tell me below.", {}),
    ],
))

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    total = 0
    for slug, title, hook, playlist, beats in BATCH:
        build(slug, title, hook, playlist, beats)
        total += len(beats)
    print(f"\n{len(BATCH)} videos written, {total} total scenes.")
