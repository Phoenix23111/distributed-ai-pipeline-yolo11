import streamlit as st
import requests
import time

# 1.  Set the Title of the app

st.title("YOLO11 Asynchronus Object Detection")
st.write("Upload an Image below to send it to the celery worker.")

# 2. Create the file Uploader widget
# restrict it to jpg and png
uploaded_file = st.file_uploader("Choose an Image...", type=["jpg","png","jpeg"])

# 3 .  Add a simple check to see if the user actuallly uploaded something
if uploaded_file is not None:
    st.success("File Successfully loaded into the browser!")

    # Create a button to trigger the process
    if st.button("Run Object Detection"):

        # Show  a Loading spinner so the user knows something is happening
        with st.spinner("Processing The Image"):
            # package the file for the api 
            files = {"file":(uploaded_file.name,uploaded_file.getvalue(),uploaded_file.type)}
            print(uploaded_file.getvalue())

            try:
                response = requests.post("https://distributed-ai-pipeline-yolo11.onrender.com/api/v1/process",files=files)

                # check if Api caught it successfully
                if response.status_code == 200:
                    data = response.json()
                    st.info(f"Gateway accepted the file! Task ID: {data['task_id']}")
                    # The polling loop
                    status = "processing"
                    while status != "completed":
                        # Ask the API 
                        status_response = requests.get(f"https://distributed-ai-pipeline-yolo11.onrender.com/api/v1/status/{data['task_id']}")
                        status_data = status_response.json()
                        # Check What API says
                        status = status_data.get("status")
                        # wait 2 seconds before asking again
                        time.sleep(2)
                    
                    st.success("YOLO11 Processing Complete!")
                    # Grab the output path from the sticky note and display it!
                    final_image_path = status_data.get("output_path")
                    st.image(final_image_path, caption = "Object Detection Results")

                    
                else:
                    st.error("Gateway rejected the file.")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to FastAPI. Is your server running?")