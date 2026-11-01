"""The prompt texts of the Documentary nodes, editable in the Documentary
Prompts node. Each box is plain text:

  - a line starting with '#' is a comment, blank lines are ignored;
  - a line starting with [tags] is used only when all its tags apply
    ('!tag': when it doesn't), e.g. "[story !lens] Never mention a photo.";
  - {name} is replaced with a value (each box lists its own); other braces
    stay as they are.

The kept lines are joined with spaces. An empty box means the built-in text
(DEFAULTS), so clearing a box brings back the latest default.

Tags: story (a free mood), format (a reel format with a job per photo), lens
(the writer sees the camera settings: "behind the lens", "photographer's
craft"), camera (the plan decides on which slides the camera details show),
youtube / instagram (the target).
"""
import re

# The boxes, in the order a film uses them.
FIELDS = ("photo_analysis", "moods", "auto_mood", "reel_formats", "writing_rules", "story_plan", "per_photo",
          "social_post")

HEADERS = {
    "photo_analysis":
        "# 1. PHOTO ANALYSIS - Story, step 1: the vision model, once per photo.\n"
        "# What it reports about each photo (subject, what it does, setting, framing). The writer knows only\n"
        "# what this returns. Your background, the photo's note and the JSON answer format are added after it.\n",
    "moods":
        "# 2. MOODS - Story: the tone of the narration.\n"
        "# One line per mood: <name>: how the narration should sound. Story's 'mood' picks one; a name that\n"
        "# isn't in Story's dropdown can still be picked by 'auto'. (Voice and music per mood are set in code.)\n"
        "# '[lens]' after the name: the narration may talk about the camera and the shot, and the writer sees\n"
        "# the camera settings (writing rules' [lens] lines).\n",
    "auto_mood":
        "# 3. AUTO MOOD - Story, only with mood 'auto (from photos)'.\n"
        "# How the writer chooses a mood (not a reel format) for these photos. Added after what the vision model\n"
        "# saw and the moods to choose from.\n",
    "reel_formats":
        "# 4. REEL FORMATS - Story: moods with a fixed job per photo, in order (made for reels).\n"
        "# A block per format; its mood also needs a line in 2. MOODS:\n"
        "#   <mood name> | <least>-<most> words [| camera] [| ask: <word>, ...] [| ask line: <text>]\n"
        "#   - <job of photo 1>\n"
        "#   - ...\n"
        "# camera: the writer sees the camera settings. ask: the last narration must say one of these words,\n"
        "# else it is rewritten and finally gets the ask line. For another number of photos, the first and last\n"
        "# jobs stay and the middle ones are spread. {n}: the number of photos.\n",
    "writing_rules":
        "# 5. WRITING RULES - Story: in every request to the writer (plan and each photo).\n"
        "# The do's and don'ts of all narration: what not to describe, facts only from the reference, names.\n"
        "# Tags: [story] free moods, [format] reel formats, [lens] the writer sees the camera settings.\n",
    "story_plan":
        "# 6. STORY PLAN - Story, step 2: one request before any narration is written.\n"
        "# The writer plans the whole film: title, premise, a beat per photo, the opening line, the thumbnail\n"
        "# text (hook), the closing 'follow' line; for reel formats also the camera moves and the cover photo;\n"
        "# and on which slides the camera details fit. The JSON answer format is added after it.\n"
        "# Tags: story, format, camera. Values: {n} photos, {moves} the camera moves, {outro_words}.\n",
    "per_photo":
        "# 7. PER-PHOTO NARRATION - Story, step 3: one request per photo.\n"
        "# Extra instructions for each photo's narration, added after the plan, what the vision model saw and\n"
        "# the word limit. Tags: story, format, lens.\n",
    "social_post":
        "# 8. SOCIAL POST - the Social Post node: caption, YouTube title, hashtags, tags, key phrases.\n"
        "# Tags: [youtube], [instagram]. Values: {ask} (subscribe / follow), {hashtags} (3 / 5).\n",
}

LOOK = """\
Look at this photograph like a careful observer. Identify the main subject as precisely as you can: an animal or plant by its common species name (if unsure between close species, name the likeliest), a place or landmark by name if you recognise it, people by what they are doing (never guess who they are).
Say what it is doing right now, and what it holds in its beak, mouth, hands or claws, if anything.
Describe the ground or setting it is in (for example grass, water, rock, sky, street, room), and list other living things in the scene.
Say where the main subject sits in the frame, how much of it it fills and which way it faces (for example 'small, in the left third, facing right', 'fills the frame, centred, facing the camera'). Facts only, no style.
"""

RULES = """\
[story] The viewer sees each picture while the narration plays, so never describe what is visible (colours, poses, perches, grass, sky). Use what is in the pictures only as the starting point, and give the viewer what they can't see: the story, the stakes, feelings, meaning, jokes, true facts.
[format] The viewer sees each picture while the narration plays: point at what is visible only where the moment's job asks for it (the light, feathers, posture, colour, the background), and say what it adds rather than list it.
[lens] Talk about taking the shot, but never say 'photo', 'image', 'picture', 'frame' or 'slide'.
[story !lens] Never mention a photo, image, picture, camera, frame, shot, slide or background.
[format !lens] Never say 'photo', 'image', 'picture' or 'slide'.
Speak to the viewer, in short sentences that are easy to say aloud.
Real-world facts (numbers, habits, abilities, records) may only come from the 'reference' text given for a moment; never invent or embellish one, and if there is no reference, use no facts.
Don't label facts ('fun fact'). Use common names, never scientific names.
When a moment has a 'name' (given by the person who took the photos, always correct), call its subject by that name at least once in that moment's narration, early on (e.g. 'the pintail', 'a northern wheatear'); never call it just 'the bird', 'the duck' or 'it' without the name. Without a 'name', use the most specific name in 'subject'.
"""

PLAN = """\
[format] Plan the narration as one story in this tone that does those jobs: a title, a one-sentence premise, and the beats (each moment's job as given).
[format] Also 'motions': for each moment, in order, the camera move over the picture that suits where the subject sits in it ('framing'), one of {moves}: zoom in when it is small in a wide scene, zoom out when it fills the picture, pan towards the side it faces or moves to, so the move ends on it; not the same move every time.
[format] Also 'cover': the number (1 to {n}) of the strongest moment for the cover: the sharpest, most striking subject, eye contact or a peak pose.
[format] Also a 'hook': a thumbnail text overlay of 3 to 4 words for that cover, punchy and in this tone (no quotes, no hashtags),
[story] Plan the narration as one story in this tone: a title, a one-sentence premise, and exactly {n} beats, one per moment in order, each saying what that moment's narration does for the story (not what the picture shows).
[story] Also an 'opening': the very first line the viewer hears, at most 12 words, that stops someone scrolling past: a question, a surprise or a bold promise of what's coming, in this tone, and true (no invented facts).
[story] Also a 'hook': a thumbnail headline of 2 to 5 words that makes people want to watch (no quotes, no hashtags),
and an 'outro': one short closing line to be spoken at the very end, under {outro_words} words, in the same tone, that asks the viewer to follow for more stories like this; it must say 'follow' (in the story's language), and no names, handles or hashtags.
[camera] Some moments have 'camera': the settings the photo was taken with. They can be shown as a small line of text on that moment's slide (never spoken). Say for each moment, in order, whether showing them fits this story and tone ('show_details': true or false; false when a moment has no 'camera'): yes in a documentary, a nature film or a photographer's memoir, where the craft is part of the story (then on most moments that have them), no where it would break the spell (a bedtime story, a joke, a noir mystery).
"""

MOMENT = """\
Vary how sentences start, and never use the phrase 'right now'.
"""

MOOD_PICKER = """\
Pick the one tone that suits these photos best: what they show (wildlife, landscapes, people, a city, action, quiet moments), their feeling, and what would make the most watchable story; not always the first one.
"""

POST = """\
Write the post as separate parts:
[youtube] 'title': the YouTube title, at most 70 characters, curious and specific, with the main key phrase early.
'hook': a scroll-stopping first line of at most 10 words.
'body': two or three short paragraphs, 50 to 90 words in all, separated by blank lines, in the video's tone, that tease the story without retelling it, with true details only from the narration, two or three fitting emojis, and two or three of the key phrases worked in naturally.
'question': one short question to the viewer, to get comments.
'cta': one short line inviting the viewer to {ask} for more stories like this. No hashtags in any of these.
'hashtags': exactly {hashtags}, a mix of specific (the subjects, the place) and popular ones for this kind of video, no spaces, without the # sign.
[youtube] 'tags': 12 YouTube tags, from specific to broad, each 1 to 4 words.
'keyphrases': 8 search key phrases of 2 to 5 words that people would type to find this video.
'alt_text': one sentence describing the video for people who can't see it.
"""


def moods_text(moods, lens=()):
    return HEADERS["moods"] + "".join(f"{name}{' [lens]' if name in lens else ''}: {style}\n"
                                      for name, style in moods.items() if style)


def formats_text(formats):
    blocks = []
    for name, f in formats.items():
        head = [name, f"{f['words'][0]}-{f['words'][1]} words"]
        if f.get("camera"):
            head.append("camera")
        if f.get("ask"):
            head.append("ask: " + ", ".join(f["ask"]))
        if f.get("ask_line"):
            head.append("ask line: " + f["ask_line"])
        blocks.append(" | ".join(head) + "\n" + "".join(f"- {job}\n" for job in f["jobs"]))
    return HEADERS["reel_formats"] + "\n".join(blocks)


def defaults(moods, formats, lens=()):
    """The boxes' texts, as the Prompts node shows them. lens: the moods marked [lens]."""
    return {"photo_analysis": HEADERS["photo_analysis"] + LOOK, "moods": moods_text(moods, lens),
            "auto_mood": HEADERS["auto_mood"] + MOOD_PICKER, "reel_formats": formats_text(formats),
            "writing_rules": HEADERS["writing_rules"] + RULES, "story_plan": HEADERS["story_plan"] + PLAN,
            "per_photo": HEADERS["per_photo"] + MOMENT, "social_post": HEADERS["social_post"] + POST}


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def parse_moods(text):
    """{name: style}, and the names marked [lens]."""
    moods, lens = {}, set()
    for line in _lines(text):
        name, sep, style = line.partition(":")
        name = name.strip()
        if name.endswith("[lens]"):
            name = name[:-len("[lens]")].strip()
            lens.add(name)
        if not sep or not name or not style.strip():
            raise ValueError(f"Documentary Prompts, moods: expected '<name>: <style>', got {line[:80]!r}")
        moods[name] = style.strip()
    return moods, lens


def parse_formats(text):
    formats, current = {}, None
    for line in _lines(text):
        if line.startswith("-"):
            if current is None:
                raise ValueError(f"Documentary Prompts, reel_formats: a job before any format: {line[:80]!r}")
            current["jobs"].append(line[1:].strip())
            continue
        parts = [p.strip() for p in line.split("|")]
        current = {"words": (8, 12), "jobs": []}
        for part in parts[1:]:
            words = re.fullmatch(r"(\d+)\s*-\s*(\d+)\s*words?", part)
            key, sep, value = part.partition(":")
            if words:
                current["words"] = (int(words[1]), int(words[2]))
            elif part == "camera":
                current["camera"] = True
            elif sep and key.strip() == "ask":
                current["ask"] = tuple(w.strip().lower() for w in value.split(",") if w.strip())
            elif sep and key.strip() == "ask line":
                current["ask_line"] = value.strip()
            else:
                raise ValueError(f"Documentary Prompts, reel_formats: unknown {part!r} in {line[:80]!r}")
        formats[parts[0]] = current
    for name, f in formats.items():
        if len(f["jobs"]) < 2:
            raise ValueError(f"Documentary Prompts, reel_formats: {name!r} needs at least 2 jobs (first and last)")
        if f.get("ask") and not f.get("ask_line"):
            f["ask_line"] = ""
    return formats


def parse(texts, moods, formats, lens=()):
    """{field: text} (empty or missing: the default) -> the prompts the nodes
    use: "moods" {name: style}, "lens_moods" (marked [lens]), "formats"
    {name: shot list}, the other fields as text."""
    default = defaults(moods, formats, lens)
    texts = {k: (texts.get(k) or "").strip() or default[k] for k in FIELDS}
    out = {k: texts[k] for k in FIELDS}
    out["moods"], out["lens_moods"] = parse_moods(texts["moods"])
    out["formats"] = parse_formats(texts["reel_formats"])
    missing = [name for name in out["formats"] if name not in out["moods"]]
    if missing:
        raise ValueError(f"Documentary Prompts: reel format(s) {', '.join(missing)} have no line in moods")
    return out


def render(text, tags=(), **values):
    """The box's text for this film: the lines whose tags apply, joined, with
    {name} replaced by values."""
    tags, kept = set(tags), []
    for line in _lines(text):
        m = re.match(r"\[([^\]]*)\]\s*", line)
        if m:
            want = m[1].replace(",", " ").split()
            if not all((w[1:] not in tags) if w.startswith("!") else (w in tags) for w in want):
                continue
            line = line[m.end():]
        kept.append(line)
    out = " ".join(kept)
    for key, value in values.items():
        out = out.replace("{" + key + "}", str(value))
    return out + " " if out else ""
