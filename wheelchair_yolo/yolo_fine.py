import torch
from ultralytics import YOLO

model = YOLO("/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/yolo26n.pt")

print("Starting Detection Training...")
results = model.train(
    data="/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/wheelchair.v1i.yolo26/data.yaml",
    device="mps",
    epochs=50,
    patience=50,
    batch=32,
    imgsz=256,
    project=""
)