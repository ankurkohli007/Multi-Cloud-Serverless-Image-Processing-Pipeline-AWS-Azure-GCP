import functions_framework
from google.cloud import firestore, vision

db = firestore.Client(database="imagepipeline")
vision_client = vision.ImageAnnotatorClient()

@functions_framework.cloud_event
def hello_gcs(cloud_event):
    data = cloud_event.data
    bucket = data["bucket"]
    name = data["name"]
    doc = {
        "imageId": name,
        "bucket": bucket,
        "size": data.get("size", "unknown"),
        "uploadTimestamp": data["timeCreated"],
    }
    try:
        image = vision.Image(source=vision.ImageSource(image_uri=f"gs://{bucket}/{name}"))
        labels = vision_client.label_detection(image=image).label_annotations
        doc["labels"] = [{"name": l.description, "confidence": round(l.score * 100, 1)} for l in labels[:10]]
        safe = vision_client.safe_search_detection(image=image).safe_search_annotation
        doc["safeSearch"] = {"adult": safe.adult.name, "violence": safe.violence.name, "racy": safe.racy.name}
        doc["isFlagged"] = any(v in ("LIKELY", "VERY_LIKELY") for v in doc["safeSearch"].values())
    except Exception as e:
        print(f"Vision analysis failed for {name}: {e}")
        doc["aiError"] = str(e)
    db.collection("image-metadata").document(name).set(doc)
    print(f"Saved enriched metadata for {name}")