# Multi-Cloud Serverless Image Processing Pipeline

An event-driven serverless pipeline built across **AWS**, **Azure**, and **GCP** — demonstrating cross-cloud competency in building identical architectures on different cloud platforms.

---

## Problem Statement

Build a pipeline where uploading an image to object storage automatically triggers processing and metadata storage — with **zero server management**. The same event-driven architecture must work identically across all three major cloud providers.

---

## Objective

Implement the same event-driven architecture across AWS, Azure, and GCP to demonstrate cross-cloud serverless competency. Each cloud implementation follows the same pattern:

1. User uploads an image to object storage
2. Storage event triggers a serverless function
3. Function logs/processes the upload
4. *(In progress)* Function writes metadata to a NoSQL database
5. *(Planned)* API layer serves metadata to frontend

---

## Architecture Overview

```
┌─────────────┐      ┌──────────────┐      ┌──────────────────┐      ┌──────────────┐      ┌───────────┐
│   User      │────▶│  Object      │────▶│  Event Trigger   │────▶│  Serverless  │────▶│  NoSQL    │
│  Uploads    │     │  Storage     │     │  (Push-based)    │     │  Function    │     │  Database  │
│  Image      │     │              │     │                  │     │  (Process)   │     │  (Step 3)  │
└─────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘     └───────────┘
                                                                       │
                                                                       ▼
                                                                ┌──────────────┐
                                                                │   API Layer  │
                                                                │  (Planned)   │
                                                                └──────────────┘
```

**Current Status:** Steps 1–2 complete (Storage + Event-Driven Compute)  
**In Progress:** Step 3 (NoSQL Database)  
**Planned:** Step 4 (API Layer)

---

## Cloud Service Comparison Table

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| **Storage** | S3 | Blob Storage | Cloud Storage |
| **Compute** | Lambda | Azure Functions | Cloud Functions (Cloud Run) |
| **Event Routing** | S3 Event Notification | Event Grid | Eventarc |
| **NoSQL Database** | DynamoDB | Cosmos DB | Firestore |
| **API Layer** | API Gateway + Lambda | API Management + Functions | Cloud Run / Cloud Endpoints |

---

## Lessons Learned / Debugging Notes

### 1. Resources Are Region-Scoped
Resources are region-scoped; mismatched regions between services cause **silent failures with no error message**. Always verify that storage, compute, and event routing services are deployed in the same region.

### 2. Azure Blob Triggers: Classic vs. Event Grid
- **Classic Blob triggers** poll storage on a schedule and can be unreliable on the Consumption plan.
- **Event Grid** is the modern push-based alternative but has **regional availability gaps** (hit this firsthand in **Italy North** — Event Grid wasn't available there at the time).

### 3. GCP Eventarc Requires Explicit IAM Grants
Eventarc runs on Pub/Sub internally and requires explicit IAM role grants (e.g., **Pub/Sub Publisher**) to service accounts **before** triggers can be created. Missing these grants results in cryptic permission errors during trigger creation.

---

## Setup Notes (Console-Based Deployment)

### AWS (Lambda + S3)
1. Create an **S3 bucket** in your target region
2. Create a **Lambda function** (Python 3.9+ runtime)
   - Upload `aws-lambda/handler.py` as the function code
   - Set handler to `handler.lambda_handler`
3. Configure **S3 Event Notification**:
   - Event type: `ObjectCreated:*`
   - Destination: Lambda function ARN
   - Grant S3 permission to invoke Lambda

### Azure (Functions + Blob Storage + Event Grid)
1. Create a **Storage Account** and **Blob Container**
2. Create a **Function App** (Consumption plan, Node.js 18+)
   - Deploy `azure-function/index.js`
   - Set entry point to the exported async function
3. Create an **Event Grid System Topic** for the storage account
4. Create an **Event Subscription**:
   - Event type: `Microsoft.Storage.BlobCreated`
   - Endpoint: Function App URL + function route
   - *Note: Verify Event Grid is available in your region*

### GCP (Cloud Functions + Cloud Storage + Eventarc)
1. Create a **Cloud Storage bucket** in your target region
2. Deploy the **Cloud Function** (2nd gen, Python 3.10+):
   ```bash
   gcloud functions deploy hello_gcs \
       --gen2 \
       --runtime=python310 \
       --region=us-central1 \
       --source=gcp-function \
       --entry-point=hello_gcs \
       --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
       --trigger-event-filters="bucket=YOUR_BUCKET_NAME"
   ```
3. **Critical:** Grant the Cloud Functions service account the `roles/pubsub.publisher` role:
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
       --role="roles/pubsub.publisher"
   ```

---

## Project Structure

```
.
├── aws-lambda/
│   └── handler.py           # AWS Lambda handler (Python)
├── azure-function/
│   └── index.js             # Azure Function handler (Node.js)
├── gcp-function/
│   ├── main.py              # GCP Cloud Function handler (Python)
│   └── requirements.txt     # Python dependencies
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

---

## Current Status

| Step | Description | Status |
|------|-------------|--------|
| 1 | Object Storage Setup | ✅ Complete |
| 2 | Event-Driven Compute (Storage → Function) | ✅ Complete |
| 3 | NoSQL Database Integration | 🚧 In Progress |
| 4 | API Layer for Metadata Access | 📋 Planned |

---

## Next Steps

- [ ] Add DynamoDB / Cosmos DB / Firestore integration to each function
- [ ] Implement metadata schema (file name, size, upload time, processing status)
- [ ] Build REST API layer to query metadata
- [ ] Add authentication/authorization to API
- [ ] Create infrastructure-as-code (Terraform/CDK/Bicep) for reproducible deployments

---

## License

MIT License — feel free to use this as a reference for your own multi-cloud projects.