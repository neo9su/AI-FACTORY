# Platform API Setup Guide

This guide covers how to obtain API credentials for each publishing platform used in Phase 5C.

## 抖音 (Douyin) Open Platform

1. Visit https://developer.open-douyin.com/ and log in with your Douyin creator account
2. Create a new app under "我的应用"
3. Enable these scopes: `video.create`, `video.list`, `user_info`
4. Copy `client_key` → set as `DOUYIN_CLIENT_KEY` in your `.env`
5. Copy `client_secret` → set as `DOUYIN_CLIENT_SECRET` in your `.env`
6. Complete user OAuth (Authorization Code flow) to obtain a user token
7. Exchange the code for `open_id` → set as `DOUYIN_OPEN_ID` in your `.env`

**API base:** `https://open.douyin.com`  
**Token URL:** `https://open.douyin.com/oauth/client_token/`  
**Post URL:** `https://open.douyin.com/api/douyin/v1/video/create/`

---

## 小红书 (Xiaohongshu) Creator Open API

1. Apply for creator API access at https://ark.xiaohongshu.com/
2. Wait for approval (can take 1-3 business days)
3. After approval, get `app_id` → set as `XHS_APP_ID`
4. Get `app_secret` → set as `XHS_APP_SECRET`
5. Complete OAuth2 authorization to obtain `access_token`
6. Set `XHS_ACCESS_TOKEN` in your environment

**Tip:** You can also set `XHS_ACCESS_TOKEN` directly if you already have it from the dashboard.

**API base:** `https://ark.xiaohongshu.com`  
**Note create URL:** `https://ark.xiaohongshu.com/api/sns/v1/note/create`

---

## TikTok for Developers

1. Register at https://developers.tiktok.com/ and create an app
2. Enable **Content Posting API** (under Products)
3. Request `video.publish` and `video.upload` scopes
4. Complete OAuth 2.0 Authorization Code flow with your TikTok creator account
5. Exchange the auth code for an `access_token`
6. Set `TIKTOK_ACCESS_TOKEN` in your environment

**API base:** `https://open.tiktokapis.com/v2`  
**Video post:** `https://open.tiktokapis.com/v2/post/publish/video/init/`  
**Photo post:** `https://open.tiktokapis.com/v2/post/publish/content/init/`

---

## Testing without credentials

The platform clients **gracefully degrade** when credentials are absent:
- `is_configured()` returns `False`
- `upload()` returns `PlatformUploadResult(success=False, error="... not set")`
- The publish job status becomes `upload_failed` (bundle.json still available for manual posting)
- You can retry once credentials are configured via the **🔄 重试上传** button in the UI

This means the system always works — content is packaged into `bundle.json` regardless of whether platform credentials are set.

---

## Environment Variables Summary

| Variable | Platform | Required |
|----------|----------|----------|
| `DOUYIN_CLIENT_KEY` | 抖音 | Yes |
| `DOUYIN_CLIENT_SECRET` | 抖音 | Yes |
| `DOUYIN_OPEN_ID` | 抖音 | Yes (author's open_id) |
| `XHS_APP_ID` | 小红书 | Optional if XHS_ACCESS_TOKEN set |
| `XHS_APP_SECRET` | 小红书 | Optional if XHS_ACCESS_TOKEN set |
| `XHS_ACCESS_TOKEN` | 小红书 | Yes (or use app_id + secret) |
| `TIKTOK_CLIENT_KEY` | TikTok | Optional |
| `TIKTOK_CLIENT_SECRET` | TikTok | Optional |
| `TIKTOK_ACCESS_TOKEN` | TikTok | Yes |
