# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app, storage, firestore
import google.cloud.firestore
import tensorflow as tf
import numpy as np
from PIL import Image
import time
from io import BytesIO

initialize_app()

def process_image(uri: str):
    model = tf.saved_model.load("efficientdet_model")

    image = Image.open(uri)
    image = np.array(image.resize(512, 512))

    input_tensor = tf.convert_to_tensor(image, dtype=tf.uint8)
    input_tensor = tf.expand_dims(input_tensor, 0)

    detections = model(input_tensor)

    categories = []

    print(detections)

    for i in range(int (detections["num_detections"])):
        box = detections["detection_boxes"][i].numpy()
        class_id = detections["detection_classes"][i].numpy()
        score = detections["detection_score"][i].numpy()
        category = detections["detection_boxes"][i]["class"]
        if score > 0.5: 
            categories.append({
                "class_id": int(class_id),
                "box": box,
                "score": score,
                "category": category
            })
    print(categories)
    return categories

def save_processed_image(categories, uri, uid, db_id):
    original_image = Image.open(uri)
    crop_images = []

    for idx, category in enumerate(categories):
        ymin, xmin, ymax, xmax = category["box"]
        width, height = original_image.size

        # Crop and save each detected category
        cropped_image = original_image.crop((
            int(xmin * width),
            int(ymin * height),
            int(xmax * width),
            int(ymax * height)
        ))

        unique_filename = f"{uid}_{db_id}_{time.time()*1000}.png"
        storage_client = storage.bucket("inspo-mobile-app.firebasestorage.app")
        blob = storage_client.blob(f"cropped_images/{unique_filename}")
        buffer = BytesIO()
        cropped_image.save(buffer, format="PNG")
        buffer.seek(0)
        blob.upload_from_file(buffer, content_type="image/png")
        cropped_image_url = f"gs://{storage_client.name}/cropped_images/{unique_filename}"
        crop_images.append({"uri": cropped_image_url, "category": category["category"]})

    return crop_images

@https_fn.on_request()
def categorize_image(req: https_fn.Request) -> https_fn.Response:
    try:
        data = req.get_json()
        if not data:
            return https_fn.Response("Missing JSON body", status=400)
        uid = data.get("uid")
        db_id = data.get("db_id")
        uri = data.get("uri")
        crop_values = data.get("crop_values")
        if not crop_values:
            print("Hellop")
            cateogories = process_image(uri)
            save_processed_image(cateogories, uri, uid, db_id)
            collection_name = f"message"
            # firestore_client: firestore.Client = firestore.Client()
            # _, doc_ref = firestore_client.collection(collection_name).add({"cropped_images": process_images})
            return https_fn.Response(f"Message with ID added.")

        return https_fn.Response("Hello world!!")
    except Exception as e:
        return f"Error {e}"