# 基礎設施規範 (Infrastructure Blueprint) - Online Supermarket

## 1. 運行環境 (Runtime Environment)
- **Containerization**: 統一使用 Docker 進行開發與部署。
- **PaaS Provider**: Render (Web Service + Managed PostgreSQL + Managed Redis)。
- **Python Runtime**: `python:3.12-slim` (基於 Debian 的輕量鏡像)。

## 2. Docker 架構規範
### A. Dockerfile 策略
- **Multi-stage Build**: 使用多階段構建以優化鏡像大小。
- **User Permission**: 禁止使用 root 運行，需建立 `django-user`。
- **Static Files**: 使用 `whitenoise` 處理 Django 靜態文件，並在 Docker 構建階段執行 `collectstatic`。

### B. Docker Compose (Local Dev)
- **Services**: `web` (Django), `db` (Postgres:16), `redis` (Redis:7-alpine)。
- **Network**: 內部網絡互相通訊，僅 `web` 對外開放 8000 端口。

## 3. 環境變數協議 (Environment Variables)
所有敏感資訊嚴禁寫入代碼，必須透過 `.env` 或 Render 儀表板注入：

| 變數名稱 | 範例/用途 | 必填 |
| :--- | :--- | :--- |
| `DEBUG` | `False` (Production) | 是 |
| `SECRET_KEY` | Django 安全金鑰 | 是 |
| `DATABASE_URL` | `postgres://user:password@host:port/db` | 是 |
| `REDIS_URL` | `redis://default:password@host:port` | 是 |
| `ALLOWED_HOSTS` | `your-app.onrender.com,localhost` | 是 |
| `USE_CACHE` | `True` (啟用 Redis 緩存) | 否 |

## 4. CI/CD 與部署流程 (Render Specific)
- **Deploy Trigger**: GitHub `main` 分支推送自動觸發。
- **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- **Start Command**: `gunicorn supermarket.wsgi:application --bind 0.0.0.0:$PORT`
- **Pre-deploy Tool**: 在啟動 App 前，必須自動執行 `python manage.py migrate`。

## 5. 高併發與維護 (Scalability & Maintenance)
- **Connection Pooling**: 使用 `dj-database-url` 配合 Render 的數據庫連接池。
- **Health Checks**: 
  - Path: `/health/`
  - 邏輯: 需檢查 DB 與 Redis 是否連線正常。
- **Logging**: 日誌輸出至 `stdout`，由 Render Log Streams 統一收集。
- **Persistent Storage**: 商品圖片存儲於外部服務 (Cloudinary / S3)，Docker 容器內部不保留狀態。

## 6. 災難恢復 (Disaster Recovery)
- **DB Backup**: 依賴 Render 的自動備份機制。
- **Cache Policy**: Redis 僅作為緩存與暫時性數據（如購物車、搶購計數），若 Redis 重啟，系統應能從 DB 恢復核心數據。

## 7. 自動化測試規範 (Automated Testing & CI/CD)
- **Unit Testing Framework**: 統一使用 `pytest` 配合 `pytest-django`。
- **Coverage**: 核心業務邏輯（尤其是庫存扣減、優惠碼計算）的測試覆蓋率必須達到 100%。
- **CI/CD Integration (Automated Testing)**:
    - **Pre-deployment Check**: 在 Render 的部署流程中，或 GitHub Actions 的 CI 流程中，必須執行 `pytest`。
    - **Blocking**: 任何一個測試失敗，必須中斷部署流程，禁止代碼上線。
- **Mocking**: 涉及到外部 API（如支付接口）或 Redis 緩存時，必須使用 `unittest.mock` 進行模擬，確保測試環境的獨立性。

## 8. 可觀測性規範 (Observability & Monitoring)
為了監控高併發下的系統健康狀況，必須實施以下措施：

### A. 結構化日誌 (Structured Logging)
- 統一輸出為 **JSON 格式** 至 `stdout`。
- 每個請求必須帶有唯一 `request_id`（Trace ID），方便跨文件追蹤單次請求的完整路徑。

### B. 性能監控 (APM)
- **Tool**: 建議集成 **Sentry** (Render 易於接駁) 進行錯誤追蹤與性能監控。
- **Profiling**: 針對資料庫查詢（SQL Queries）進行監控，若單次查詢超過 500ms 必須紀錄 `WARNING` 日誌。

### C. 指標監控 (Metrics)
- 需提供 `/metrics` 接口（若使用 Prometheus 監控）或通過日誌統計：
    - **Business Metrics**: 每秒下單數、搶購失敗率、庫存更新延遲。
    - **System Metrics**: 數據庫連接池使用率、Redis 命中率。

### D. 健康檢查進階 (Advanced Health Checks)
- `/health/` 接口除了檢查連線，還需檢查當前任務隊列（如有）是否有嚴重的積壓（Backlog）。

## 9. GitHub 整合與安全規範 (GitHub & Security)

### A. 自動化 Git 操作指令
- **Git Flow**: 每次 Service 開發完成並通過本地 `pytest` 後，必須提示用戶執行：
    - `git add .`
    - `git commit -m "feat: [App Name] implement [Service Name] logic"`
    - `git push origin [branch-name]`
- **Atomic Commits**: 每個 Service 應作為一個獨立的 Commit，確保歷史紀錄清晰。

### B. GitHub Security (安全性)
- **Secrets Management**: 
    - 嚴禁將 `.env` 或任何私鑰提交至 GitHub。
    - 必須配置 `.gitignore` 排除所有敏感文件。
    - 在 GitHub Repository Settings 中使用 **Actions Secrets** 來儲存 `RENDER_API_KEY` 或 `DATABASE_URL`。
- **Branch Protection**: 建議開啟 `main` 分支保護，要求部署前必須通過 Status Checks（即 Automated Testing）。
- **Security Scanning**: 
    - 必須在 CI 流程中加入 **Secret Scanning** (例如使用 GitHub 原生功能或 `gitleaks`)。
    - 加入 `dependabot` 以自動監控 Python 套件的安全漏洞。
    - JWT Secret: 必須由環境變數 JWT_SECRET_KEY 提供，不得提交至 Git。
    - CORS 設定: 必須嚴格限制 CORS_ALLOWED_ORIGINS，僅允許前端域名訪問。