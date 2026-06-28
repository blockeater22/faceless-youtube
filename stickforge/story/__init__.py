"""The Story Engine — turn a written script into a performed, subtitled scene.

    script (text)  ->  parsed lines (emotion + intent)  ->  acting beats
                   ->  performance clip + timed subtitles  ->  Scene

It closes the loop the Acting Engine opened: a writer types lines, the director
infers emotion and inserts "think before you react" beats, and the result is a
silent-readable performance with subtitles. No manual keyframing.
"""
from .script import ScriptLine, parse_script, infer_emotion
from .engine import storyboard
from .dialogue import parse_dialogue, stage_dialogue

__all__ = ["ScriptLine", "parse_script", "infer_emotion", "storyboard",
           "parse_dialogue", "stage_dialogue"]
