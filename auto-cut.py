import os

times = [
    1.43, 2.97, 4.47, 5.83, 7.4,
    8.73, 9.43, 11.93, 13.43, 14.73, 15.7
]

os.makedirs("clips", exist_ok=True)

for i in range(len(times) - 1):

    start = times[i]
    duration = times[i + 1] - start

    if duration < 0.8:
        continue

    cmd = (
        f'ffmpeg -y '
        f'-ss {start} '
        f'-i source_video.mp4 '
        f'-t {duration} '
        f'-vf "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280" '
        f'-an '
        f'clips/clip_{i:02d}.mp4'
    )

    os.system(cmd)

print("DONE")
