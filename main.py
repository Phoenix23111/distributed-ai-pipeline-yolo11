from fastapi import FastAPI, UploadFile, File
import redis
import uuid
import os
import cloudinary
import cloudinary.uploader
from celery import Celery
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

celery_redis_url = os.getenv("REDIS_URL")

# 2. Chop off everything after the "?" for the standard Redis client
standard_redis_url = celery_redis_url.split("?")[0]

redis_client = redis.Redis.from_url(standard_redis_url, decode_responses=True)
celery_app = Celery("ai_worker", broker=celery_redis_url, backend=celery_redis_url)

cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

@app.post("/api/v1/process")
async def process_image(file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    print(f"[{task_id}] Uploading file directly to Cloudinary...")
    
    upload_result = cloudinary.uploader.upload(file.file)
    cloud_url = upload_result["secure_url"]
    print(f"[{task_id}] Successfully uploaded! URL: {cloud_url}")
    
    redis_client.hset(f"task:{task_id}", mapping={
        "status": "queued",
        "image_url": cloud_url 
    })
    
    # 3. Yell at the Cloud Worker to start!
    celery_app.send_task("process_ai_task", args=[task_id, cloud_url])
    
    return {"task_id": task_id, "status": "queued"}
# local development
# @app.post("/api/v1/process")
# async def submit_image(file: UploadFile = File(...)):
#     """ Accepts an image file, saves it, and triggers the YOLO11 worker. """
#     task_id = str(uuid.uuid4())

#     # 1. Save the incoming file in /uploads folder
#     file_extension = file.filename.split(".")[-1]
#     input_path = f"uploads/{task_id}.{file_extension}"

#     with open(input_path, "wb") as buffer:
#         buffer.write(await file.read())

#     # 2. Package the task data
#     task_data = {
#         "task_id" : task_id,
#         "status" : "queued",
#         "input_path":input_path
#     }

#     # 3. Queue the task in Redis
#     redis_client.hset(f"task:{task_id}",mapping=task_data)
#     redis_client.lpush("ai_model_queue",task_id)

#     # 4. Trigger the background Celery worker
#     run_heavy_model.delay(task_id, input_path)

#     return {
#         "message": "Image received. Processing asynchronously.",
#         "task_id": task_id,
#         "check_status_url": f"/api/v1/status/{task_id}"
#     }


# @app.post("/api/v1/process")
# async def submit_heavy_task(payload: dict):
#     """
#     Receives data, instantly queues it in Redis, and returns a tracking ID.
#     This prevents the web server from freezing during heavy AI inference.
#     """
#     # 1. Generate a unique, secure tracking ID for this task
#     task_id = str(uuid.uuid4())
    
#     # 2. Package the data for the AI worker
#     task_data = {
#         "task_id": task_id,
#         "status": "queued",
#         "input": json.dumps(payload)
#     }
    
   
#     # 3. Push the task into Redis (The "Sticky Note")
#     redis_client.hset(f"task:{task_id}", mapping=task_data) 
#     redis_client.lpush("ai_model_queue", task_id)           
    
#     # NEW: Tell Celery to pick up the task!
#     run_heavy_model.delay(task_id, task_data["input"])       # Put the ID in the waiting line
    
#     # 4. Instantly reply to the user without waiting for the model
#     return {
#         "message": "Task successfully handed off to the broker.",
#         "task_id": task_id,
#         "check_status_url": f"/api/v1/status/{task_id}"
#     }

@app.get("/api/v1/status/{task_id}")
async def check_task_status(task_id: str):
    """ Allows the client to check if the background AI worker is done. """
    data = redis_client.hgetall(f"task:{task_id}")
    if not data:
        return {"error": "Invalid Task ID"}
    return data