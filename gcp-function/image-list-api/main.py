import functions_framework
from google.cloud import firestore
import json

db = firestore.Client(database="imagepipeline")

@functions_framework.http
def list_images(request):
    docs = db.collection("image-metadata").stream()
    items = [doc.to_dict() for doc in docs]
    return (json.dumps(items), 200, {"Content-Type": "application/json"})