# Multi-Cloud Serverless Image Processing Pipeline

An event-driven, serverless image processing pipeline built across **AWS**, **Azure**, and **Google Cloud Platform**. Upload an image to object storage and it automatically triggers a serverless function that performs AI-powered image analysis (label detection, moderation/safe search), stores enriched metadata in a NoSQL database, and exposes a read API for clients. Built to demonstrate real cross-cloud serverless competency with managed AI services.

---

## Status

| Stage | AWS | Azure | GCP |
|-------|-----|-------|-----|
| 1. Object Storage | ✅ Verified | ✅ Verified | ✅ Verified |
| 2. Event Trigger | ✅ Verified | ⚠️ Partial (blob trigger never invoked) | ✅ Verified |
| 3. NoSQL Database Write | ✅ Verified | ⚠️ Partial (configured, unverified — trigger never fired) | ✅ Verified |
| 4. Read API | ✅ Verified | ⚠️ Partial (HTTP function + Cosmos input binding returns 500, undiagnosed) | ✅ Verified |
| 5. AI Image Analysis | ✅ Verified | ⚠️ Partial (on-demand HTTP call only, not trigger-driven, results not stored) | ✅ Verified |

---

## Problem Statement & Objective

**Problem:** Uploading an image should automatically trigger processing, AI analysis, and metadata storage — with no servers to manage.

**Objective:** Build the same event-driven pipeline on AWS, Azure, and GCP to demonstrate real cross-cloud serverless and managed-AI competency.

---

## Architecture

```
User
  │
  ▼
Object Storage (S3 / Blob Storage / Cloud Storage)
  │
  ▼
Event Trigger (S3 Event Notifications / Event Grid + Blob Trigger / Eventarc on Pub/Sub)
  │
  ▼
Serverless Compute (Lambda / Azure Functions / Cloud Run Functions 2nd Gen)
  │
  ▼
Managed AI Vision (Rekognition / Azure AI Vision / Cloud Vision API)
  │
  ▼
NoSQL Database (DynamoDB / Cosmos DB for NoSQL / Firestore)
  │
  ▼
HTTP API (Lambda Function URL + API Gateway / HTTP Function / HTTP Cloud Run Function)
  │
  ▼
Client
```

---

## Repository Structure

```
.
├── aws-lambda/
│   ├── handler.py                 # S3-triggered Lambda: upload → AI analysis → DynamoDB
│   └── list_images_handler.py     # GET /images API: scan DynamoDB → JSON
├── azure-function/
│   ├── index.js                   # Blob-triggered function: upload → Cosmos DB output binding
│   ├── ImageListApi/
│   │   └── index.js               # HTTP function: Cosmos DB input binding → JSON
│   └── AnalyzeImage/
│       └── index.js               # On-demand HTTP: Azure AI Vision analysis
├── gcp-function/
│   ├── main.py                    # Eventarc-triggered: GCS finalize → Cloud Vision → Firestore
│   ├── requirements.txt
│   ├── image-list-api/
│   │   ├── main.py                # HTTP Cloud Run function: Firestore stream → JSON
│   │   └── requirements.txt
└── README.md
```

---

## Service Mapping

| Layer | AWS | Azure | GCP |
|-------|-----|-------|-----|
| **Object Storage** | S3 (private, eu-north-1) | Storage Account + Container "images" (Italy North) | Cloud Storage (private, US multi-region) |
| **Serverless Compute** | Lambda (Python 3.11) | Azure Functions (Node.js, Windows Consumption) | Cloud Run Functions 2nd Gen (Python) |
| **Event Routing** | S3 Event Notifications (all object-create) | Event Grid (unsupported in Italy North) → Classic Blob Trigger `images/{name}` | Eventarc trigger on `google.cloud.storage.object.v1.finalized` |
| **NoSQL Database** | DynamoDB `image-metadata` (PK: `imageId`, on-demand) | Cosmos DB for NoSQL (serverless) `ImagePipelineDB` / `ImageMetadata` (PK: `/imageId`) | Firestore Native mode, named DB `imagepipeline`, collection `image-metadata` |
| **HTTP API** | Lambda Function URL + API Gateway HTTP API (`GET /images` on `$default`) | HTTP-triggered Function `ImageListApi` (Cosmos input binding) | HTTP Cloud Run Function `image-list-api` (unauthenticated) |
| **AI Vision** | Rekognition (`detect_labels`, `detect_moderation_labels`) in eu-west-1 | Azure AI Vision (free tier) v3.2 `analyze` (Tags, Description, Adult) | Cloud Vision API `label_detection` + `safe_search_detection` |
| **Permission Model** | IAM execution role (S3 read, DynamoDB write, Rekognition read) | Function app settings + connection strings + keys (VISION_ENDPOINT, VISION_KEY) | Default compute service account with Editor role; Pub/Sub Publisher for Eventarc |

---

## Stage Walkthrough

### Stage 1 — Object Storage

**Concept:** Private buckets/containers to receive image uploads. No public access.

**What I built:**
- **AWS:** Private S3 bucket in `eu-north-1` (Stockholm).
- **Azure:** Storage account in Italy North with a blob container named `images`.
- **GCP:** Private GCS bucket in US multi-region.

**How the code evolved:** N/A — infrastructure-only stage.

**Problems & fixes:**
- Resources are region-scoped; mismatches fail silently (e.g., Rekognition unavailable in `eu-north-1`).
- Azure requires a storage account before creating a container.

---

### Stage 2 — Event-Driven Compute

**Concept:** An object upload triggers a serverless function automatically.

**What I built:**
- **AWS:** Lambda with S3 event notification (all object-create events). Execution role auto-created.
- **Azure:** Function App on Windows Consumption plan (Node.js — Python requires Linux, not offered in free-trial create flow). Two trigger variants:
  - Classic blob trigger on path `images/{name}`
  - Event Grid blob trigger (for comparison)
- **GCP:** Cloud Run Functions 2nd Gen with Eventarc trigger on the storage "object finalized" event.

**How the code evolved:** Function initially only logged the event (`fileName`, `size`).

**Problems & fixes:**
- **AWS:** S3 trigger binds to one exact bucket ARN — wrong bucket = silent no-op.
- **Azure:** Event Grid not supported in Italy North ("resource does not yet support events in this region"). Classic blob trigger showed 0 invocations (polling-based, unreliable on Consumption plan).
- **GCP:** Eventarc API had to be enabled. Trigger creation failed with `storage.buckets.get` permission denied until the Cloud Storage service agent was granted **Pub/Sub Publisher** (Eventarc runs on Pub/Sub).

---

### Stage 3 — NoSQL Database Write

**Concept:** The triggered function writes image metadata to a NoSQL database.

**What I built:**
- **AWS:** DynamoDB table `image-metadata` (partition key `imageId`, on-demand). Written via `boto3 put_item`. Role granted full DynamoDB access (learning scope; production should scope to `PutItem` on one table).
- **Azure:** Cosmos DB for NoSQL (serverless). Database `ImagePipelineDB`, container `ImageMetadata`, partition key `/imageId`. Written through an output binding (`outputDocument`). Documents require a lowercase `id` field.
- **GCP:** Firestore Native mode, named database `imagepipeline`. Collection `image-metadata` auto-created on first write.

**How the code evolved:** From logging only → writing base metadata (`imageId`, `bucket`, `size`, `uploadTimestamp`).

**Problems & fixes:**
- **GCP:** Firestore client defaults to database `"(default)"`. Must use `firestore.Client(database="imagepipeline")` — surfaced as `NotFound` at write time, looked like a permission error.
- **Azure:** Output binding "Collection Name" field defaulted to a placeholder; had to be set explicitly.

---

### Stage 4 — API Layer (Read Endpoint)

**Concept:** Expose a `GET /images` (or equivalent) endpoint that returns all stored metadata.

**What I built:**
- **AWS:** Second Lambda (`list_images_handler.py`) with DynamoDB read-only role. Exposed first via **Function URL**, then via **API Gateway HTTP API** route `GET /images` on the `$default` stage (routes are explicit method+path; bare invoke URL returns Not Found).
- **Azure:** HTTP-triggered function `ImageListApi` with a Cosmos DB input binding (`inputDocuments`, query `SELECT * FROM c`).
- **GCP:** HTTP Cloud Run function `image-list-api`, unauthenticated, entry point `list_images`.

**How the code evolved:** From scan/stream → JSON response with proper headers.

**Problems & fixes:**
- **AWS:** DynamoDB returns numbers as `Decimal`; `json.dumps` fails. Added custom `DecimalEncoder`.
- **GCP:** Entry point left as `hello_http` caused container start failure (PORT=8080 health check) — only a naming mismatch.
- **Azure:** Adding `WEBSITE_CONTENTSHARE` and `WEBSITE_CONTENTAZUREFILECONNECTIONSTRING` with new values made **all functions disappear** (code lives in an Azure Files share referenced by those settings). Removing the settings and restarting restored them.
- **Azure:** `ImageListApi` returns 500 with no exception surfaced by standard logs — undiagnosed.

---

### Stage 5 — AI Image Analysis

**Concept:** Enrich metadata with labels, moderation/safe-search, and a flagged indicator.

**What I built:**
- **AWS:** Rekognition `detect_labels` (MaxLabels=10, MinConfidence=70) + `detect_moderation_labels` (MinConfidence=60).
  - Rekognition unavailable in `eu-north-1` → called in `eu-west-1` (Ireland), keeping EU data residency.
  - S3 references cannot be used cross-region → image bytes sent directly (5 MB limit).
  - Lambda timeout raised 3s → 30s, memory 128 MB → 256 MB.
  - Role needs Rekognition read-only + S3 read (S3 trigger does **not** grant read access).
  - Keys are URL-encoded → `unquote_plus` required.
  - Confidence scores wrapped in `Decimal(str(...))` because DynamoDB rejects floats.
  - `try/except` so failed analysis still saves base metadata with `aiError` field.
- **GCP:** Cloud Vision API (enabled per project) with `label_detection` + `safe_search_detection`.
  - Reads straight from `gs://` URI — no byte transfer needed.
  - Default compute service account's Editor role was sufficient.
  - Added `google-cloud-vision` to requirements.
  - Moderation threshold: flag at `LIKELY` or `VERY_LIKELY`.
- **Azure:** Azure AI Vision resource (free tier) with endpoint and key stored as app settings `VISION_ENDPOINT` and `VISION_KEY`.
  - On-demand HTTP function `AnalyzeImage` using v3.2 `analyze` API (Tags, Description, Adult).
  - Private blobs need a SAS URL, which must be URL-encoded when passed as a query parameter.
  - Not integrated into the blob trigger pipeline; results not persisted.

**Output comparison:**
| Cloud | Labels | Moderation / Safe Search | Flagging |
|-------|--------|--------------------------|----------|
| AWS | Category + confidence % | Moderation labels (explicit categories) | Any moderation label → `isFlagged=true` |
| Azure | Tags + natural-language caption | Adult/racy/gore scores 0–1 | `isAdultContent` or `isRacyContent` → `isFlagged=true` |
| GCP | Description + confidence % (score × 100) | Likelihood levels: `VERY_UNLIKELY` … `VERY_LIKELY` | Any `LIKELY`/`VERY_LIKELY` → `isFlagged=true` |

---

## Portal-Configured Settings (No Secrets)

| Cloud | Setting |
|-------|---------|
| **AWS Lambda** | Timeout: 30s, Memory: 256 MB. Policies: `AmazonS3ReadOnlyAccess`, `AmazonDynamoDBFullAccess` (learning), `AmazonRekognitionReadOnlyAccess`. |
| **AWS API Gateway** | HTTP API, route `GET /images` on stage `$default`, integration = Lambda `list_images_handler`. |
| **Azure Blob Trigger** | Path: `images/{name}` (classic trigger). |
| **Azure Cosmos Output Binding** | Parameter: `outputDocument`, Database: `ImagePipelineDB`, Container: `ImageMetadata`, Partition Key: `/imageId`. |
| **Azure Cosmos Input Binding** | Parameter: `inputDocuments`, Database: `ImagePipelineDB`, Container: `ImageMetadata`, Query: `SELECT * FROM c`. |
| **Azure App Settings** | `VISION_ENDPOINT`, `VISION_KEY` (names only; values in portal). |
| **GCP Eventarc Trigger** | Event type: `google.cloud.storage.object.v1.finalized`, Service: Cloud Run Function `hello_gcs`, Bucket: target GCS bucket. |
| **GCP HTTP Function** | Unauthenticated, entry point: `list_images` (and `hello_gcs` for the trigger). |
| **GCP IAM** | Default compute service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`) granted **Editor** role (learning; production should scope to `datastore.documents.create`, `vision.images.annotate`, `pubsub.topics.publish`). |

---

## Known Limitations (Honest)

- **Azure blob trigger never fired reliably** — classic trigger is polling-based and unreliable on Consumption plan; Event Grid unsupported in Italy North.
- **Azure `ImageListApi` returns 500** — undiagnosed; no exception in standard logs.
- **Azure AI step is on-demand only** — not integrated into the upload pipeline; results not stored.
- **Public unauthenticated read endpoints** — no auth/throttling on any cloud.
- **Broad IAM roles used for learning** — full DynamoDB, Editor on GCP, etc.
- **`scan()` / `stream()` read entire tables** — no pagination, no indexes, no query optimization.

---

## What I Would Do Next

1. **Azure:** Move to Linux or Premium hosting plan for reliable blob triggers (Event Grid + Linux, or Premium plan with VNet).
2. **API layer:** Add API Management (Azure) / API Gateway authorizers + usage plans (AWS) / Cloud Endpoints (GCP) for auth and throttling.
3. **Data access:** Replace scans with queries and GSIs (DynamoDB), composite indexes (Firestore), or proper partition strategies (Cosmos).
4. **Security:** Least-privilege IAM roles; store secrets in Key Vault / Secrets Manager / Secret Manager.
5. **Moderation:** Configurable confidence thresholds; human-review queue for borderline cases.

---

*Built as a portfolio demonstration of cross-cloud serverless architecture and managed AI integration.*

## Stage 6: Generative AI Integration (additive)

Stage 6 code lives in `stage6-generative-ai/`. Earlier files are unchanged.

### What it adds
A generative model turns the vision step's labels into an alt-text caption and hashtags. Only text labels are sent, not the image (cheaper, avoids image-size and region limits; the prompt says *use ONLY the given labels*, which grounds the output and reduces invented details). The generative call has its own try/except, so a model failure never discards the vision results (`genAiError` field). Moderation decisions stay with the vision service, not the language model.

### Status table (Stage 6 only)

| Cloud | Status |
|-------|--------|
| AWS   | BLOCKED (code complete; see Known Issue) |
| Azure | Verified (on-demand HTTP function; caption returned in the response, not stored) |
| GCP   | Verified (automatic on upload; stored in Firestore) |

### Per-cloud notes
- **GCP**: Vertex AI Gemini via the `google-genai` SDK with `vertexai=True`. The API was enabled with `gcloud services enable aiplatform.googleapis.com` because Vertex AI was renamed and no longer matched in the API Library search. The model ID is copied from the console because IDs change. The client is created inside the function so a configuration error cannot crash container startup.
- **Azure**: A Foundry resource with a deployed small chat model, called by deployment name through the `/openai/v1/responses` route. App settings `AZ_OPENAI_ENDPOINT`, `AZ_OPENAI_KEY`, `AZ_OPENAI_DEPLOYMENT` hold the values (names only here). The code retries with a Bearer header on a 401. Lesson: endpoint, key and deployment must come from the same Foundry resource (the subscription had two), and a curl test of the key is the fastest way to separate a bad key from a bad function.

### Known Issue: Amazon Bedrock blocked on AWS
The Lambda calls Bedrock `converse` with the EU inference profile `eu.amazon.nova-lite-v1:0` from its own region. The call failed first with `AccessDeniedException` ("account is currently being verified") and later with `ValidationException` ("Operation not allowed"). The same error occurred in the Bedrock playground and for other models, and CloudShell also reported account verification in progress. The billing console showed a registered payment method and remaining credits. AWS Support replied that this is an account-level restriction they cannot change and suggested contacting an account manager. It is not yet determined whether it relates to account plan or service quotas. The code is retained and degrades gracefully: the record is still saved with the vision results plus a `genAiError` field. To retest once the restriction clears, upload a fresh image (existing records do not update).

### Why integrate AI cloud services and generative AI
AI cloud services (Rekognition, Cloud Vision, Azure AI Vision) are pre-trained APIs that turn unstructured data into structured data (labels, moderation flags, text), replacing manual review and tagging with no model training, pay-per-call. Generative models (Bedrock, Azure OpenAI, Vertex AI Gemini) write new content such as captions, summaries and answers. The cloud supplies what AI alone lacks: event triggers, scaling, identity and permissions, storage, APIs and monitoring. Good design runs the cheap predictable vision step first, grounds the generative step in its output, isolates each AI call so a failure never loses the base record, controls cost with small models and token caps, considers regions and inference profiles for data residency, and keeps safety decisions with the moderation service.
