"""The look of a film (Documentary Look node): fonts, accent colour, intro,
subtitles, colour grade, finish, follow card and thumbnail layout.

Each part is "auto (from mood)" (one of the mood's choices in MOOD_LOOKS),
"random" (any choice) or a fixed choice. The choices are drawn from the
story's seed, so Ken Burns Video and Thumbnail, which both resolve the look,
get the same one. Without a Look node: CLASSIC, the look from before.
"""
import colorsys
import os
import random

import numpy as np
import torch

AUTO, RANDOM = "auto (from mood)", "random"

# (title font, text font): the title, label and thumbnail use the first,
# subtitles and the follow text the second. Fonts in font_dirs(): this pack's
# fonts/ folder first (open licences, LICENSE-*.txt there); DejaVu comes with the system.
FONT_SETS = {
    "classic": ("DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf"),
    "cinematic": ("BebasNeue-Regular.ttf", "Poppins-SemiBold.ttf"),
    "impact": ("Anton-Regular.ttf", "Poppins-Bold.ttf"),
    "elegant": ("DMSerifDisplay-Regular.ttf", "PT_Serif-Web-Bold.ttf"),
    "modern": ("Poppins-Bold.ttf", "Poppins-SemiBold.ttf"),
    "handwritten": ("PermanentMarker-Regular.ttf", "Kalam-Bold.ttf"),
    "typewriter": ("SpecialElite-Regular.ttf", "CourierPrime-Bold.ttf"),
    "playful": ("LuckiestGuy-Regular.ttf", "Poppins-Bold.ttf"),
}
ACCENTS = {"from photos": None, "gold": (255, 200, 61), "white": (245, 245, 240), "coral": (255, 111, 97),
           "teal": (64, 200, 190), "sky": (110, 180, 255)}
PARTS = {
    "font": list(FONT_SETS),
    "accent": list(ACCENTS),
    "intro": ["collage", "hero", "filmstrip", "mosaic"],
    "subtitles": ["outline", "boxed", "karaoke", "minimal"],
    "grade": ["none", "warm", "cool", "faded film", "black & white", "vivid"],
    "finish": ["none", "vignette", "film grain", "letterbox"],
    "follow_card": ["classic", "minimal"],
    "thumbnail": ["classic", "bold", "split", "framed"],
}
CLASSIC = {"font": "classic", "accent": "gold", "intro": "collage", "subtitles": "outline", "grade": "none",
           "finish": "none", "follow_card": "classic", "thumbnail": "classic"}

# Per mood, what auto picks from (missing parts: any choice).
_WILD = {"accent": ["from photos"], "follow_card": ["classic", "minimal"]}
MOOD_LOOKS = {
    "documentary (Nat Geo)": {"font": ["elegant", "modern"], "intro": ["hero", "collage", "filmstrip"],
                              "subtitles": ["outline", "boxed"], "grade": ["warm", "none", "vivid"],
                              "finish": ["vignette", "none"], "thumbnail": ["bold", "framed", "classic"]},
    "funny": {"accent": ["from photos", "coral"], "font": ["playful", "modern"], "intro": ["collage", "mosaic"], "subtitles": ["karaoke", "boxed"],
              "grade": ["vivid", "none"], "finish": ["none"], "thumbnail": ["bold", "split"]},
    "poetic": {"accent": ["from photos", "white"], "font": ["elegant", "handwritten"], "intro": ["hero", "mosaic"], "subtitles": ["minimal"],
               "grade": ["faded film", "cool", "warm"], "finish": ["vignette", "film grain"],
               "follow_card": ["minimal"], "thumbnail": ["framed", "classic"]},
    "bedtime story": {"font": ["handwritten", "playful"], "intro": ["collage", "mosaic"],
                      "subtitles": ["boxed", "minimal"], "grade": ["warm"], "finish": ["vignette"],
                      "thumbnail": ["framed", "classic"]},
    "epic trailer": {"accent": ["from photos", "white"], "font": ["cinematic", "impact"], "intro": ["hero"], "subtitles": ["outline", "minimal"],
                     "grade": ["cool", "vivid"], "finish": ["letterbox"], "follow_card": ["minimal"],
                     "thumbnail": ["bold"]},
    "nostalgic memoir": {"font": ["typewriter", "handwritten", "elegant"], "intro": ["filmstrip", "collage"],
                         "subtitles": ["minimal", "boxed"], "grade": ["faded film", "warm"],
                         "finish": ["film grain", "vignette"], "thumbnail": ["framed", "classic"]},
    "sports commentary": {"accent": ["from photos", "coral"], "font": ["impact", "cinematic"], "intro": ["mosaic", "hero"], "subtitles": ["karaoke"],
                          "grade": ["vivid"], "finish": ["none"], "thumbnail": ["bold", "split"]},
    "mystery / noir": {"accent": ["white"], "font": ["typewriter", "cinematic"], "intro": ["hero"], "subtitles": ["minimal", "outline"],
                       "grade": ["black & white"], "finish": ["film grain", "letterbox"], "follow_card": ["minimal"],
                       "thumbnail": ["bold", "framed"]},
    "behind the lens": {"font": ["modern", "typewriter"], "intro": ["filmstrip", "collage"],
                        "subtitles": ["boxed", "minimal"], "grade": ["none", "faded film"],
                        "finish": ["none", "vignette"], "thumbnail": ["classic", "framed", "split"]},
    "inner dialogue": {"accent": ["from photos", "coral", "sky"], "font": ["playful", "handwritten", "modern"], "intro": ["collage", "mosaic"],
                       "subtitles": ["karaoke", "boxed"], "grade": ["vivid", "none"], "finish": ["none"],
                       "thumbnail": ["bold", "split"]},
    "travel field notes": {"font": ["typewriter", "handwritten"], "intro": ["filmstrip", "hero"],
                           "subtitles": ["minimal", "boxed"], "grade": ["faded film", "cool", "warm"],
                           "finish": ["film grain", "vignette"], "thumbnail": ["framed", "classic"]},
    "zen & mindful": {"accent": ["from photos", "teal"], "font": ["elegant", "modern"], "intro": ["hero", "mosaic"], "subtitles": ["minimal"],
                      "grade": ["faded film", "warm", "none"], "finish": ["vignette"], "follow_card": ["minimal"],
                      "thumbnail": ["framed", "classic"]},
    "david vs goliath": {"font": ["cinematic", "impact"], "intro": ["hero", "mosaic"],
                         "subtitles": ["outline", "karaoke"], "grade": ["cool", "vivid"],
                         "finish": ["letterbox", "vignette"], "thumbnail": ["bold", "split"]},
    "gossip column": {"accent": ["coral", "from photos"], "font": ["playful", "impact", "modern"], "intro": ["mosaic", "collage"],
                      "subtitles": ["karaoke", "boxed"], "grade": ["vivid"], "finish": ["none"],
                      "thumbnail": ["bold", "split"]},
    "survival log": {"accent": ["from photos", "white"], "font": ["typewriter", "cinematic"], "intro": ["hero", "filmstrip"],
                     "subtitles": ["minimal", "outline"], "grade": ["cool", "faded film", "black & white"],
                     "finish": ["film grain", "vignette"], "thumbnail": ["bold", "framed"]},
    "mini-documentary": {"font": ["elegant", "modern"], "intro": ["hero", "filmstrip"], "subtitles": ["minimal"],
                         "grade": ["warm", "none", "faded film"], "finish": ["vignette"],
                         "follow_card": ["minimal"], "thumbnail": ["framed", "bold"]},
    "photographer's craft": {"font": ["modern", "typewriter"], "intro": ["filmstrip", "mosaic"],
                             "subtitles": ["boxed", "minimal"], "grade": ["none", "vivid"],
                             "finish": ["none", "vignette"], "thumbnail": ["split", "classic", "framed"]},
    "species spotlight": {"accent": ["from photos", "teal", "coral"], "font": ["modern", "impact", "playful"], "intro": ["mosaic", "collage"],
                          "subtitles": ["karaoke", "boxed"], "grade": ["vivid"], "finish": ["none"],
                          "thumbnail": ["split", "bold"]},
}


def resolve(settings, mood, seed, reel):
    """The concrete look: settings {part: AUTO / RANDOM / a choice} (None: CLASSIC)."""
    if not settings:
        out = dict(CLASSIC)
    else:
        rng = random.Random(f"look-{seed}-{mood}")
        table = {**_WILD, **MOOD_LOOKS.get(mood or "", {})}
        out = {}
        for part, choices in PARTS.items():
            # Draw for every part, so a fixed choice doesn't change the others.
            auto, any_ = rng.choice(table.get(part) or choices), rng.choice(choices)
            want = settings.get(part, AUTO)
            out[part] = auto if want == AUTO else any_ if want == RANDOM else want
        if settings.get("accent_hex"):
            out["accent"] = settings["accent_hex"]
    if reel and out["finish"] == "letterbox":
        out["finish"] = "vignette"  # no bars in a 9:16 reel
    return out


def accent_rgb(look, images, cover=0):
    """The accent colour: a named one, '#rrggbb', or from the photos (the cover's most vivid colour)."""
    value = look["accent"]
    if isinstance(value, str) and value.startswith("#") and len(value) == 7:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    if ACCENTS.get(value):
        return ACCENTS[value]
    for image in [images[cover]] + [im for i, im in enumerate(images) if i != cover]:
        rgb = _vivid(image)
        if rgb:
            return rgb
    return ACCENTS["gold"]


def _vivid(image):
    """The vivid colour of the photo's sharp part (in wildlife photos the subject, not the soft
    background or sky), as a light colour that reads on dark; None for a grey photo."""
    x = image[0].float().cpu().permute(2, 0, 1)[None]
    h, w = x.shape[2:]
    scale = 160 / max(h, w)
    x = torch.nn.functional.interpolate(x, size=(max(round(h * scale), 3), max(round(w * scale), 3)), mode="area")
    lap = torch.tensor([[[[0, 1, 0], [1, -4, 1], [0, 1, 0]]]], dtype=torch.float32)
    sharp = torch.nn.functional.conv2d(x.mean(1, keepdim=True), lap, padding=1).abs()
    sharp = torch.nn.functional.avg_pool2d(sharp, 9, stride=1, padding=4)[0, 0]
    sharp = (sharp / (sharp.max() + 1e-6)).flatten().numpy()
    px = x[0].permute(1, 2, 0).reshape(-1, 3).numpy()
    mx, mn = px.max(1), px.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    keep = (sat > 0.35) & (mx > 0.3)
    if keep.sum() < len(px) * 0.005:
        return None
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[keep]])
    weight = hsv[:, 1] * hsv[:, 2] * (0.05 + sharp[keep] ** 2)
    bins = (hsv[:, 0] * 24).astype(int) % 24
    # The colour that is on average the sharpest and most vivid, not the most common: the
    # subject's colour is small next to the sky or the foliage behind it. Specks don't count.
    count = np.bincount(bins, minlength=24)
    score = np.bincount(bins, weights=weight, minlength=24) / np.maximum(count, 1)
    score[count < max(5, 0.002 * len(px))] = 0
    best = score.argmax()
    sel = bins == best
    hue = float(np.average(hsv[sel, 0], weights=weight[sel]))
    s = float(np.average(hsv[sel, 1], weights=weight[sel]))
    r, g, b = colorsys.hsv_to_rgb(hue, min(max(s, 0.55), 0.8), 1.0)
    # Light enough to read on a dark background: blues and purples lifted towards white.
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 0.6:
        k = (0.6 - lum) / (1 - lum)
        r, g, b = (c + (1 - c) * k for c in (r, g, b))
    return round(r * 255), round(g * 255), round(b * 255)


def grade(image, kind):
    """A colour grade on an IMAGE ([1,H,W,3], 0..1)."""
    if kind in (None, "none"):
        return image
    x = image.float()
    grey = (x * torch.tensor([0.299, 0.587, 0.114], device=x.device)).sum(-1, keepdim=True)
    if kind == "warm":
        x = x * torch.tensor([1.06, 1.0, 0.9], device=x.device) + 0.01
    elif kind == "cool":
        x = x * torch.tensor([0.92, 0.99, 1.07], device=x.device)
    elif kind == "faded film":
        x = grey + (x - grey) * 0.78
        x = x * 0.86 + 0.07
        x = x * torch.tensor([1.03, 1.0, 0.95], device=x.device)
    elif kind == "black & white":
        x = ((grey - 0.5) * 1.18 + 0.5).expand_as(x)
    elif kind == "vivid":
        x = grey + (x - grey) * 1.28
        x = (x - 0.5) * 1.07 + 0.5
    return x.clamp(0, 1)


def fonts(look):
    """(title font, text font, headline font, small font) file names."""
    title, text = FONT_SETS.get(look["font"], FONT_SETS["classic"])
    if look["font"] == "classic":
        return title, text, "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"
    return title, text, title, "Poppins-Medium.ttf"


def font_dirs(models_dir):
    """This pack's fonts, then any added to models/fonts on the volume, then the system's DejaVu."""
    return [os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"), os.path.join(models_dir, "fonts"),
            "/usr/share/fonts/truetype/dejavu"]
