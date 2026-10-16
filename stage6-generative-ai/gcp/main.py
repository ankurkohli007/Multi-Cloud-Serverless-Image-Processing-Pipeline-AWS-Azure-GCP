import json
import google.auth
import functions_framework
from google import genai
from google.cloud import firestore, vision

db = firestore.Client(database="imagepipeline")
vision_client = vision.ImageAnnotatorClient()

GEN_MODEL = "gemini-3.8-flash"

def generate_caption(label_names, flagged):
    _, project = google.auth.default()
    client = genai.Client(vertexai=True, project=project, location="us-central1")
    prompt = (
        "You write alt-text for an image catalog. You cannot see the image. "
        "Use ONLY these detected labels: " + ", ".join(label_names) + ". "
        f"Moderation flagged: {flagged}. "
        'Reply with JSON only: {"caption": "<one sentence>", "hashtags": ["#a", "#b", "#c"]}'
    )
    text = client.models.generate_content(model=GEN_MODEL, contents=prompt).text
    try:
        return json.loads(text[text.index('{'): text.rindex('}') + 1])
    except ValueError:
        return {"caption": text.strip(), "hashtags": []}

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

        if doc["labels"]:
            try:
                gen = generate_caption([l["name"] for l in doc["labels"]], doc["isFlagged"])
                doc["aiCaption"] = gen.get("caption")
                doc["aiHashtags"] = gen.get("hashtags", [])
            except Exception as e:
                print(f"GenAI step failed for {name}: {e}")
                doc["genAiError"] = str(e)
    except Exception as e:
        print(f"Vision analysis failed for {name}: {e}")
        doc["aiError"] = str(e)
    db.collection("image-metadata").document(name).set(doc)
    print(f"Saved enriched metadata for {name}")