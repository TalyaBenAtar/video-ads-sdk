# 📡 Video Ads Backend API

_A cloud-based backend service powering the Android Ads SDK_

This repository contains the **backend API** for the Ads SDK.  
It provides ad delivery, configuration management, authentication, and an administration portal used to control ad behavior without updating client applications.

The API is built with **Flask**, deployed on **Vercel**, and backed by **MongoDB**.

---

## 🚀 Overview

The API is responsible for:

- Storing and managing **ads** (image & video)
- Selecting ads dynamically per client application
- Enforcing **client-level configuration** (allowed types & categories)
- Handling **authentication & authorization**
- Serving a secure **web-based administration portal**

The Android SDK communicates directly with this API.

---

## 🌐 Deployment

- **Base URL:**  
https://vercel.com/talyas-projects-8ed6edb8/video-ads-sdk


- **Hosting:** Vercel  
- **Database:** MongoDB Atlas

---

## 🔐 Authentication

The API uses **JWT-based authentication**.

### Login
POST /auth/login


```json
{
  "username": "your-username",
  "password": "your-password"
}

{
  "token": "<jwt-token>"
}
```
The token must be sent in subsequent requests: Authorization: Bearer <token>

## Registration (Developer Accounts)
POST /auth/register
```
{
  "username": "developer-username",
  "password": "developer-password",
  "clientId": "developer-id"
}
```
Creates a developer account tied to a specific clientId (app).
The developer chooses their own id, and use it in the app when initiating the library.

## 📢 Ads Endpoints
List Ads
GET /ads?clientId=<clientId>

Create Ad
POST /ads
```
{
  "clientId": "developer-id",
  "id": "ad-id",
  "title": "ad-title",
  "type": "image/video",
  "imageUrl": "https://...",
  "clickUrl": "https://...",
  "categories": ["ad-catagory"],
  "enabled": true
}
```

Update Ad
PUT /ads/{adId}
Allows updating ad fields such as enabled, title, URLs, or categories.

Delete Ad
DELETE /ads/{adId}
Deletes an existing ad.

## 🎯 Ad Selection (Used by the SDK)
GET /ads/select?clientId=<clientId>&type=<image|video>
response:
```
{
  "ad": {
    "id": "ad-id",
    "type": "image/video",
    "imageUrl": "...",
    "clickUrl": "...",
    "categories": ["ad-catagory"]
  }
}
```
If no valid ad is found:
```
{ "ad": null }
```
This endpoint is public and optimized for SDK usage.


## ⚙️ Client Configuration
Each client app can control which ads are eligible.

Get Config
GET /config/{clientId}

Update Config
PUT /config/{clientId}
```
{
  "allowedTypes": ["image", "video"],
  "allowedCategories": ["ad-catagory"]
}
```
Configuration directly affects /ads/select.

## 🛠️ Administration Portal
A web-based portal is included for managing ads and configurations.
🔗 Portal URL
https://video-ads-sdk-git-main-talyas-projects-8ed6edb8.vercel.app/portal/login.html

### Features

- Secure login (admin & developer roles)
- Create, edit, enable, and delete ads
- Manage client configurations
- Immediate effect on SDK behavior (no app updates required)
- End users of client apps never access the portal.

## 🧪 Health Check
GET /health
```
{
  "status": "ok",
  "db": "connected"
}
```

## 🔧 Environment Variables
The API requires the following environment variables:
```
MONGODB_URI
ADMIN_USERNAME
ADMIN_PASSWORD
JWT_SECRET
```

## 📄 License
This project is released under the MIT License.

## 🧠 Related Projects
- Android Ads SDK:
https://github.com/TalyaBenAtar/MemoryGame
- Demo Application:
Memory Game (included in SDK repository)

## 📚 Documentation (GitHub Pages)

Full project documentation, including SDK usage, backend API, and the administration portal, is available here:

👉 https://talyabenatar.github.io/video-ads-sdk/

