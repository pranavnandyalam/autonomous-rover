import random
import shutil
import sys
from pathlib import Path

OUTPUT = Path("/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/coco_person")

COCO_PERSON = 0
PERSON_CLASS = 1
MIN_PERSON_HEIGHT = 0.15
PERSON_IMAGES = 1000
BACKGROUND_IMAGES = 200
VALID_FRACTION = 0.15
SEED = 0


def read_people(label_path):
    people = []
    for line in label_path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 5 and int(parts[0]) == COCO_PERSON:
            people.append(parts[1:])
    return people


def sort_images(image_dir, label_dir):
    with_people, without_people = [], []
    for image_path in sorted(image_dir.glob("*.jpg")):
        label_path = label_dir / f"{image_path.stem}.txt"
        people = read_people(label_path) if label_path.exists() else []
        if any(float(h) >= MIN_PERSON_HEIGHT for _, _, _, h in people):
            with_people.append((image_path, people))
        elif not people:
            without_people.append((image_path, []))
    return with_people, without_people


def write_split(items, split):
    image_out = OUTPUT / split / "images"
    label_out = OUTPUT / split / "labels"
    image_out.mkdir(parents=True, exist_ok=True)
    label_out.mkdir(parents=True, exist_ok=True)
    for image_path, people in items:
        shutil.copy2(image_path, image_out / image_path.name)
        lines = [f"{PERSON_CLASS} {' '.join(box)}" for box in people]
        (label_out / f"{image_path.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))


def main(image_dir, label_dir):
    with_people, without_people = sort_images(Path(image_dir), Path(label_dir))
    print(f"Found {len(with_people)} images with a person >= {MIN_PERSON_HEIGHT:.0%} of frame height, "
          f"{len(without_people)} with no people")

    rng = random.Random(SEED)
    chosen = rng.sample(with_people, min(PERSON_IMAGES, len(with_people)))
    chosen += rng.sample(without_people, min(BACKGROUND_IMAGES, len(without_people)))
    rng.shuffle(chosen)

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    n_valid = int(len(chosen) * VALID_FRACTION)
    write_split(chosen[n_valid:], "train")
    write_split(chosen[:n_valid], "valid")

    for split in ("train", "valid"):
        labels = list((OUTPUT / split / "labels").glob("*.txt"))
        boxes = sum(len(p.read_text().splitlines()) for p in labels)
        print(f"{split}: {len(labels)} images, {boxes} person boxes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python build_person_dataset.py <coco val2017 images dir> <coco val2017 labels dir>")
    main(sys.argv[1], sys.argv[2])
