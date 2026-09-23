import functions_framework
from google.cloud import firestore

db = firestore.Client(database="imagepipeline")

@functions_framework.cloud_event
def hello_gcs(cloud_event):
    data = cloud_event.data

    bucket = data["bucket"]
    name = data["name"]
    size = data.get("size", "unknown")
    time_created = data["timeCreated"]

    print(f"New file uploaded: {name} in bucket {bucket}, size: {size} bytes")

    # Write metadata into Firestore
    doc_ref = db.collection("image-metadata").document(name)
    doc_ref.set({
        "imageId": name,
        "bucket": bucket,
        "size": size,
        "uploadTimestamp": time_created
    })

    print(f"Saved metadata for {name} to Firestore")