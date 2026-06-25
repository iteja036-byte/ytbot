import json

with open('brain.json') as f:
    brain = json.load(f)

with open('clips.json') as f:
    clips = json.load(f)

wanted = brain['tags']

best = []

for clip in clips:

    score = len(
        set(wanted) &
        set(clip['tags'])
    )

    best.append((score,clip['file']))

best.sort(reverse=True)

selected = [x[1] for x in best[:2]]

with open('selected.json','w') as f:

    json.dump(selected,f)

print(selected)
