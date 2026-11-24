from ultralytics import YOLO

model = YOLO("/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/yolo26n.pt")

print("Starting Detection Training (wheelchair + person)...")
results = model.train(
    data="/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/data_combined.yaml",
    device="mps",
    epochs=50,
    patience=15,
    batch=32,
    imgsz=320,
    project="/Users/prn/Documents/Code/ENGR100/runs/detect",
    name="wheelchair_person",
)
