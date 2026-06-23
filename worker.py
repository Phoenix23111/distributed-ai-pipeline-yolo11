import os
import requests
from celery import Celery
import redis
import cloudinary
import cloudinary.uploader
from ultralytics import YOLO
from dotenv import load_dotenv

# 1. Load the keys from the Colab .env file
load_dotenv()

# 2. Grab the full URL for Celery
celery_redis_url = os.getenv("REDIS_URL")

# 3. Chop off the SSL flag for the standard Redis client
standard_redis_url = celery_redis_url.split("?")[0]

# 4. Connect both clients using their preferred URLs!
celery_app = Celery("ai_worker", broker=celery_redis_url, backend=celery_redis_url)
redis_client = redis.Redis.from_url(standard_redis_url, decode_responses=True)

# 5. Connect to the Cloud Storage (Cloudinary)
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

# 6. Load the AI Muscle directly into the T4 GPU
print("Loading YOLO11 onto the Nvidia T4 GPU...")
model = YOLO("yolo11n.pt")

@celery_app.task(name="process_ai_task")
def run_heavy_model(task_id, image_url):
    print(f"[{task_id}] Colab Worker caught the task! Downloading image...")
    redis_client.hset(f"task:{task_id}", "status", "processing")

    # Step 1: Download the image from Cloudinary to the Google Server
    local_input_path = f"{task_id}_input.jpg"
    response = requests.get(image_url)
    with open(local_input_path, "wb") as f:
        f.write(response.content)

    # Step 2: Run YOLO (This will be lightning fast on the GPU)
    results = model(local_input_path)

    # Step 3: Save locally on Colab
    local_output_path = f"{task_id}_output.jpg"
    results[0].save(local_output_path)

    # Step 4: Upload the finished image back to Cloudinary
    print(f"[{task_id}] Uploading finished result back to Cloud...")
    upload_result = cloudinary.uploader.upload(local_output_path)
    final_cloud_url = upload_result["secure_url"]

    # Step 5: Update the Upstash sticky note with the final URL
    redis_client.hset(f"task:{task_id}", mapping={
        "output_path": final_cloud_url,
        "status": "completed"
    })

    print(f"[{task_id}] GPU Processing Complete!")
    return final_cloud_url