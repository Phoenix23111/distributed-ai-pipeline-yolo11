
# Distributed AI Vision Pipeline: YOLO11

A fully decoupled, cloud-native computer vision pipeline demonstrating enterprise-grade architectural patterns. This project processes real-time object detection using YOLO11, leveraging a distributed microservices architecture to offload heavy GPU computation from the main web server.

## System Architecture

Unlike standard monolithic AI applications that block the main thread during inference, this system utilizes an asynchronous, message-driven architecture.

```mermaid
graph TD
    A[Streamlit UI] -->|1. Uploads Image| B(FastAPI Gateway)
    B -->|2. Offloads File| C[(Cloudinary Object Storage)]
    B -->|3. Publishes Task| D{{Upstash Redis Queue}}
    B -.->|6. Long-Polling Status| A
    E[Google Colab Worker] -->|4. Consumes Task| D
    E -->|5. YOLO11 Inference | E
    E -->|7. Uploads Result| C
    E -->|8. Updates Status| D
    D -.->|9. Returns Result URL| B
