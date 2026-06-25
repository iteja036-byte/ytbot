def select_caption(captions, mood):
    filtered = []

    for c in captions:
        if mood == "sad" and c["emotion"] in ["sad-love", "heartbreak", "missing-you"]:
            filtered.append(c)

    filtered.sort(key=lambda x: x["intensity"], reverse=True)

    return filtered[0]


def viral_score(caption):
    emotion_boost = {
        "heartbreak": 2,
        "sad-love": 1.5,
        "missing-you": 1.2
    }

    return caption["intensity"] * emotion_boost.get(caption["emotion"], 1)


def select_tags(tags):
    return sorted(tags, key=lambda x: x["score"], reverse=True)[:2]


def brain_v2(data, mood):
    caption = select_caption(data["captions"], mood)

    tags = select_tags([
        {"name": "AnimeLove", "score": 0.9},
        {"name": "SadRomance", "score": 0.95},
        {"name": "ViralReel", "score": 0.7}
    ])

    return {
        "caption": caption["text"],
        "emotion": caption["emotion"],
        "viral_score": viral_score(caption),
        "tags": [t["name"] for t in tags]
    }
