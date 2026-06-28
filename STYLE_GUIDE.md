# StickForge Visual Style Guide

The product identity is an **illustrated cartoon actor** — not a mathematical
stickman. Every rendering decision, asset, and animation must serve this.

> The viewer should think *"that character feels alive,"* not *"that is a stick
> figure."*

## Design philosophy

70% cartoon character · 20% stickman · 10% minimal flat design.
Friendly, approachable, expressive, simple, modern, readable, timeless.
**Soft rounded shapes; avoid sharp geometry.** Personality before motion.

## House style (what the `illustrated` renderer must produce)

| Element | Spec |
|---|---|
| Head | Big (~28–30% of height), white, **bold dark outline**, perfectly readable when tiny |
| Face | Expressive — eyes are not tiny dots; eyebrows are primary storytelling; many mouth shapes |
| Hair | A small distinctive style per character; should bounce slightly when animated |
| Body | Rounded shoulders, slight torso taper, soft silhouette — never a rectangle |
| Limbs | Thick rubber-hose with **rounded joints**; long and expressive; never rigidly straight |
| Hands | Simple cartoon hands (4 fingers), not bare circles |
| Feet | Simple cartoon shoes; support walk/run/jump |
| Line | Bold, clean, consistent width, rounded caps. **No shaky/sketch lines, no boil.** |
| Color | Flat, high-contrast, minimal gradients, small accents; must read in monochrome |
| Depth | Ground shadow under the actor |

Signature palette: white head/limbs, **yellow tee**, **black shorts**, black
shoes, bold near-black outline, small red/blue/green/purple accents.

## Acting & motion (the actor must perform)

- Body language reads before dialogue: lean in (curious), lean back (shock),
  shoulders drop (sad), chest out (confident), arms open (excited), hands to
  face (embarrassed), head tilt (thinking).
- Always alive: idle breathing, blinking, small head movement, hair bounce,
  hand follow-through, secondary motion, weight, ease in/out, overshoot.
- Motion/emotion FX vocabulary: speed lines, impact/burst, vibration, sweat,
  question/surprise, lightbulb, stars, hearts, anger. (`render/fx.py`)

## Quality bar (score every character/shot)

Rate each 1–10; **anything below 9 → keep redesigning**:

Appeal · Charm · Readability · Silhouette · Emotion · Animation readiness ·
Personality · Professional quality · Visual consistency · Brand identity.

At thumbnail size the viewer must instantly read emotion, action, direction,
pose, and mood. The silhouette must never be confusing.

## Absolute rule

Do **not** create mathematical stickmen. Create illustrated cartoon actors.
This philosophy guides every asset, animation, and future feature.
