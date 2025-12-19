# KratorAI Gemini API Integration Guide

This guide provides the necessary information for the frontend developer to integrate the KratorAI Gemini API into the website.

## 🚀 Base URL & Documentation

The **Base URL** is the main address of your deployed service on Render. All specific endpoints are added to the end of this URL.

- **Base URL:** `https://kratorai-r.onrender.com` (Replace with your actual Render URL)
- **Interactive API Docs (Swagger):** `https://your-app-name.onrender.com/docs`

> [!TIP]
> **The most important link to give your frontend developer is the `/docs` link.** 
> It contains the full list of endpoints, interactive testing, and the exact data structures (schemas) they need to send and receive.

## 🚀 Unified Integration Endpoint

To simplify integration, we have provided a single endpoint that handles all AI features. This is the **only** URL the frontend needs to hit for most tasks.

- **Unified Endpoint:** `https://kratorai-r.onrender.com/process`
- **Method:** `POST`
- **Payload:** A JSON object containing an `action` key and the feature-specific data.

### How to use `/process`

The developer sends a JSON body with an `action` key. The API automatically routes the request to the correct feature.

| Action | Feature | Example Payload |
| :--- | :--- | :--- |
| `breed` | Design Breeding | `{ "action": "breed", "designs": [...], "style": "modern" }` |
| `refine` | Design Refining | `{ "action": "refine", "image_url": "...", "prompt": "make it blue" }` |
| `edit` | Design Editing | `{ "action": "edit", "image": "...", "mask": "...", "instruction": "..." }` |
| `agent` | AI Agent Chat | `{ "action": "agent", "message": "Hello", "session_id": "123" }` |
| `template` | Template Editing | `{ "action": "template", "template_id": "...", "modifications": {...} }` |

### Example Fetch Call (JavaScript)

```javascript
const response = await fetch('https://kratorai-r.onrender.com/process', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    action: "breed",
    designs: ["base64_image_1", "base64_image_2"],
    style: "minimalist"
  }),
});

const data = await response.json();
console.log(data);
```

## 🛠 Other Endpoints (Direct Access)

While `/process` is recommended, the developer can still hit specific endpoints directly if needed:

### 2. Design Refining (`/refine`)
**POST** `/refine` or `/refine/upload`
Generates variations of a design based on a prompt.
- **Request Body:** `RefineRequest` or `Multipart/form-data` for uploads.
- **Use Case:** Iterating on a specific design idea.

### 3. AI Agent Chat (`/agent/chat`)
**POST** `/agent/chat` or `/agent/chat/upload`
Conversational interface for design assistance.
- **Request Body:** `ChatRequest`
- **Use Case:** Interactive design editing and guidance.

### 4. Template Editing (`/template`)
**POST** `/template/edit`
Specific endpoints for editing design templates.

## 🔒 CORS Configuration

The API is currently configured to allow all origins (`*`).
> [!IMPORTANT]
> For production, please provide the frontend domain (e.g., `https://kratorai.com`) so we can restrict CORS for better security.

## ☁️ Appwrite Integration (BaaS)

Since you are using Appwrite, here is the recommended workflow:

1. **Storage:** When a user uploads an image, store it in **Appwrite Storage**.
2. **API Call:** Send the Appwrite file URL or the file itself to the Gemini API.
3. **Database:** Store the resulting image URL (returned by the Gemini API) in an **Appwrite Database** collection (e.g., `generated_designs`).
4. **Realtime:** Use Appwrite's Realtime features to notify the UI when a long-running generation is complete.

### Example Fetch Call (JavaScript)

```javascript
const response = await fetch('https://your-render-url.com/agent/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: "Refine this design to look more modern",
    session_id: "user-session-123"
  }),
});

const data = await response.json();
console.log(data);
```

## 📝 Notes
- The API uses **FastAPI** and is optimized for performance.
- Rate limiting is currently set to **60 requests per minute**.
- For large image uploads, ensure the `Content-Type` is set correctly to `multipart/form-data`.
