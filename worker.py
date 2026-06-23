from celery import Celery
from ultralytics import YOLO
import redis
import time
import json

# Connect to the Redis container (acting as both the message broker and backend)
celery_app = Celery(
    "ai_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Connect a standard Redis client to update our task statuses
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
# Load the YOLO11-Nano model globally so it doesn't reload on every single image
print("Loading YOLO11 model into memory...")
model = YOLO("yolo11n.pt")

@celery_app.task(name="process_ai_task")
def run_heavy_model(task_id: str, input_path: str):
    """
    This is the actual background job. It pulls the task, processes it,
    and updates the database without the main web server ever waiting.
    """
    print(f"[{task_id}] Worker executing YOLO11 inference...")
    
    # 0. Update status in Redis to show we are working on it
    redis_client.hset(f"task:{task_id}", "status", "processing")
    
    # 1. Run inference on the image
    results = model(input_path)
    
    # 2. Save the annotated image (with bounding boxes) to the results folder
    output_path = f"results/{task_id}_output.jpg"
    results[0].save(output_path)

    # 3. Extract the actual text data (what objects were found)
    detected_objects = []
    for box in results[0].boxes:
        class_id = int(box.cls)
        class_name = model.names[class_id]
        confidence = float(box.conf)
        detected_objects.append(f"{class_name} ({confidence:.2f})")
    
    # 4. Save the final results back to Redis
    final_payload = {
        "output_image_path": output_path,
        "detections": detected_objects
    }
# 4. Save the final results back to Redis (Atomically!)
    redis_client.hset(f"task:{task_id}", mapping={
        "result": json.dumps(final_payload),
        "status": "completed"
    })
    
    print(f"[{task_id}] Processing complete! Image saved.")
    return final_payload