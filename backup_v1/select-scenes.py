import os
import random
from PIL import Image

folder = "clips"

imgs = sorted([x for x in os.listdir(folder) if x.endswith(".jpg")])

selected = []

for img in imgs:
    path = os.path.join(folder, img)

    try:
        im = Image.open(path)

        w,h = im.size

        # reject dark/useless frames
        stat = im.resize((1,1)).getpixel((0,0))

        bright = sum(stat)/3

        if bright < 40:
            continue

        # keep only good cinematic frames
        if random.random() > 0.08:
            continue

        selected.append(img)

    except:
        pass

selected = selected[:12]

print("\nBEST SCENES:\n")

for i,x in enumerate(selected):
    print(i,"=>",x)

with open("chosen.txt","w") as f:
    for x in selected:
        f.write(x+"\n")

print("\nDONE")
