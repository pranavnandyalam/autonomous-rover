from pathlib import Path
from ultralytics import YOLO

DATASET = Path("/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/wheelchair.v1i.yolo26")
MODEL_PATH = "/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/yolo26n.pt"
SPLITS = ["train", "valid", "test"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

COCO_PERSON = 0
PERSON_CLASS = 1
CONFIDENCE = 0.4


def load_model():
    model = YOLO(MODEL_PATH)
    if model.names.get(COCO_PERSON) != "person":
        raise ValueError(f"{MODEL_PATH} is not a COCO model (class 0 is {model.names.get(COCO_PERSON)!r})")
    return model


def existing_lines(label_path):
    if not label_path.exists():
        return []
    lines = [line.strip() for line in label_path.read_text().splitlines() if line.strip()]
    return [line for line in lines if line.split()[0] != str(PERSON_CLASS)]


def person_lines(model, image_path):
    result = model(str(image_path), classes=[COCO_PERSON], conf=CONFIDENCE, device="mps", verbose=False)[0]
    return [f"{PERSON_CLASS} {x:.6f} {y:.6f} {w:.6f} {h:.6f}" for x, y, w, h in result.boxes.xywhn.tolist()]


def label_split(model, split):
    image_dir = DATASET / split / "images"
    label_dir = DATASET / split / "labels"
    label_dir.mkdir(exist_ok=True)

    images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    people_found = 0
    for image_path in images:
        label_path = label_dir / f"{image_path.stem}.txt"
        people = person_lines(model, image_path)
        label_path.write_text("\n".join(existing_lines(label_path) + people) + "\n")
        people_found += len(people)

    print(f"{split}: {len(images)} images, {people_found} people labeled")


def clear_caches():
    for cache in DATASET.glob("*/labels.cache"):
        cache.unlink()
        print(f"Deleted {cache}")


if __name__ == "__main__":
    model = load_model()
    for split in SPLITS:
        label_split(model, split)
    clear_caches()
