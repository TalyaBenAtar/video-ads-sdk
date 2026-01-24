[Home](index.md) | [SDK](sdk.md) | [API](api.md) | [Portal](portal.md)

---


\# 📡 Backend API



The \*\*Video Ads Backend API\*\* powers the Android Ads SDK.  

It provides ad delivery, configuration management, authentication, and an administration portal for managing ad content dynamically.



The API is built with \*\*Flask\*\*, deployed on \*\*Vercel\*\*, and backed by \*\*MongoDB Atlas\*\*.



---



\## 🌐 Deployment



\- \*\*Base URL\*\*

https://vercel.com/talyas-projects-8ed6edb8/video-ads-sdk





\- \*\*Hosting:\*\* Vercel  

\- \*\*Database:\*\* MongoDB Atlas



---



\## 🔐 Authentication



The API uses \*\*JWT-based authentication\*\*.



\### Login

POST /auth/login





```json

{

&nbsp; "username": "your-username",

&nbsp; "password": "your-password"

}



{

&nbsp; "token": "<jwt-token>"

}

```

The token must be sent in subsequent requests: Authorization: Bearer <token>



\## Registration (Developer Accounts)

POST /auth/register

```

{

&nbsp; "username": "developer-username",

&nbsp; "password": "developer-password",

&nbsp; "clientId": "developer-id"

}

```

Creates a developer account tied to a specific clientId (app).

The developer chooses their own id, and use it in the app when initiating the library.



\## 📢 Ads Endpoints

List Ads

GET /ads?clientId=<clientId>



Create Ad

POST /ads

```

{

&nbsp; "clientId": "developer-id",

&nbsp; "id": "ad-id",

&nbsp; "title": "ad-title",

&nbsp; "type": "image/video",

&nbsp; "imageUrl": "https://...",

&nbsp; "clickUrl": "https://...",

&nbsp; "categories": \["ad-catagory"],

&nbsp; "enabled": true

}

```



Update Ad

PUT /ads/{adId}

Allows updating ad fields such as enabled, title, URLs, or categories.



Delete Ad

DELETE /ads/{adId}

Deletes an existing ad.



\## 🎯 Ad Selection (Used by the SDK)

GET /ads/select?clientId=<clientId>\&type=<image|video>

response:

```

{

&nbsp; "ad": {

&nbsp;   "id": "ad-id",

&nbsp;   "type": "image/video",

&nbsp;   "imageUrl": "...",

&nbsp;   "clickUrl": "...",

&nbsp;   "categories": \["ad-catagory"]

&nbsp; }

}

```

If no valid ad is found:

```

{ "ad": null }

```

This endpoint is public and optimized for SDK usage.





\## ⚙️ Client Configuration

Each client app can control which ads are eligible.



Get Config

GET /config/{clientId}



Update Config

PUT /config/{clientId}

```

{

&nbsp; "allowedTypes": \["image", "video"],

&nbsp; "allowedCategories": \["ad-catagory"]

}

```

Configuration directly affects /ads/select.



\## 🛠️ Administration Portal

A web-based portal is included for managing ads and configurations.

🔗 Portal URL

https://video-ads-sdk-git-main-talyas-projects-8ed6edb8.vercel.app/portal/login.html



\### Features



\- Secure login (admin \& developer roles)

\- Create, edit, enable, and delete ads

\- Manage client configurations

\- Immediate effect on SDK behavior (no app updates required)

\- End users of client apps never access the portal.



\## 🧪 Health Check

GET /health

```

{

&nbsp; "status": "ok",

&nbsp; "db": "connected"

}

```



\## 🔧 Environment Variables

The API requires the following environment variables:

```

MONGODB\_URI

ADMIN\_USERNAME

ADMIN\_PASSWORD

JWT\_SECRET

```



\## 📄 License

This project is released under the MIT License.

