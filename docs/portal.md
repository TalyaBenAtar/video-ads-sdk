---
layout: default
title: Ads SDK Docs
---


[Home](index.md) | [SDK](sdk.md) | [API](api.md) | [Portal](portal.md)

---


\# 🛠️ Administration Portal



The \*\*Administration Portal\*\* is a secure web-based interface used to manage ads and client configuration for the Ads SDK system.



It allows backend data to be updated dynamically, without requiring changes or redeployment of client applications.



---



\## 🎯 Purpose



The portal exists to separate \*\*ad management\*\* from \*\*app development\*\*.



Using the portal, authorized users can:

\- Control which ads are available

\- Enable or disable ads instantly

\- Configure ad behavior per client application



All changes take effect immediately for apps using the SDK.



---



\## 🔐 Access



\### 🔗 Portal URL

https://video-ads-sdk-git-main-talyas-projects-8ed6edb8.vercel.app/portal/login.html





Access requires authentication.



Two roles are supported:

\- \*\*Admin\*\* – full access to all clients and ads

\- \*\*Developer\*\* – access limited to their own clientId



End users of host applications never access the portal.



---



\## ✨ Features



\- Secure login using JWT authentication

\- Create, edit, enable, and delete ads

\- Support for \*\*image and video ads\*\*

\- Assign categories to ads

\- Manage per-client configuration:

&nbsp; - Allowed ad types (image / video)

&nbsp; - Allowed categories

\- Immediate effect on SDK behavior (no app updates required)



---



\## 🔄 Typical Usage Flow



1\. Log in to the portal

2\. Select or enter a \*\*clientId\*\* (application ID)

3\. Create or edit an ad:

&nbsp;  - Choose ad type (image or video)

&nbsp;  - Provide media URL

&nbsp;  - Assign categories

4\. Enable the ad

5\. The Android app receives the updated ad automatically via the SDK



---



\## 🧠 Relationship to the SDK



The Android Ads SDK communicates only with the backend API.  

The portal is an \*\*administrative tool\*\* layered on top of the same API.



This separation ensures:

\- Clean SDK integration

\- Secure ad management

\- No coupling between app code and ad data



---



\## 🔗 Related


\- \[Android SDK Documentation](sdk.md)

\- \[Backend API Documentation](api.md)



---

## 📸 Portal Screenshots

### 🔐 Login & Account Creation
![Portal Login](screenshots/admin_portal_screenshot.png)

---

### 🧩 Main Dashboard
![Portal Dashboard](screenshots/admin-portal-open-screenshot.png)

---

### ✏️ Edit Existing Ad
![Edit Ad Modal](screenshots/portal-edit-screenshot.png)

---

### ➕ Create New Ad
![Create Ad Modal](screenshots/portal-create-screenshot.png)

