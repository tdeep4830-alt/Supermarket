# 身份驗證與權限規範 (Auth & Permission Blueprint)

## 1. 技術實現 (Implementation)
- **機制**: 基於 Session 的有狀態驗證（相比 JWT 更安全，支援伺服器端登出）。
- **後端庫**: Django 內建 Session + `django.contrib.auth`。
- **存儲**:
    - Session ID: 存於 HttpOnly Cookie (防止 XSS 攻擊)。
    - Session Data: 存於 Redis (Ref: infra.md §2B)。
- **CSRF 保護**: Double Submit Cookie 模式。

## 2. 用戶模型 (User Model)

### A. Custom User Model
繼承 `AbstractUser`，擴展以下欄位：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `phone` | CharField(20) | 手機號碼，可選，唯一 |
| `is_verified` | BooleanField | 手機/郵箱已驗證 |
| `avatar_url` | URLField | 頭像 URL |
| `membership_tier` | CharField | 會員等級: REGULAR, GOLD, PLATINUM |

### B. 注意事項
- 必須在第一次 migration 前設定 `AUTH_USER_MODEL`。
- 使用 UUID 作為主鍵 (Ref: data.md §4)。

## 3. 數據安全 (Security)
- **Password**: 必須使用 Django 內建的 PBKDF2 算法加密，嚴禁存儲明文。
- **PII 保護**: 在日誌 (Logging) 中嚴禁記錄用戶密碼、Token 或手機號碼等敏感資訊。
- **CSRF Token**:
    - 前端必須從 Cookie 讀取 `csrftoken` 並放入 `X-CSRFToken` Header。
    - 所有 POST/PUT/PATCH/DELETE 請求必須帶上 CSRF Token。
- **Session Cookie**:
    - `SESSION_COOKIE_HTTPONLY = True` (防止 JS 讀取)
    - `SESSION_COOKIE_SAMESITE = 'Lax'` (防止 CSRF)
    - `SESSION_COOKIE_SECURE = True` (生產環境 HTTPS)

## 4. 權限層級 (Permission Levels)
- **AllowAny**: 商品列表、分類、登入/註冊。
- **IsAuthenticated**: 下單、查詢個人訂單、領取優惠券、修改個人資料。
- **IsAdmin**: 庫存管理、優惠券創建、監控數據查看。

## 5. API 端點 (Endpoints)

| Method | Endpoint | Permission | 說明 |
|--------|----------|------------|------|
| POST | `/api/auth/register/` | AllowAny | 用戶註冊 |
| POST | `/api/auth/login/` | AllowAny | 用戶登入 |
| POST | `/api/auth/logout/` | IsAuthenticated | 用戶登出 |
| GET | `/api/auth/me/` | IsAuthenticated | 取得當前用戶資訊 |
| PUT | `/api/auth/me/` | IsAuthenticated | 更新當前用戶資訊 |

## 6. 異常處理 (Exception)
- **401 Unauthorized**: Session 過期或無效，前端需觸發自動導向登入頁。
- **403 Forbidden**: 權限不足（例如用戶嘗試讀取他人訂單）。
- **CSRF 驗證失敗**: 返回 403，前端需重新取得 CSRF Token。

## 7. 前端整合 (Frontend Integration)
```typescript
// API Client 配置
const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true, // 必須開啟，傳送 Cookie
});

// CSRF Token 攔截器
apiClient.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method)) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});
```
