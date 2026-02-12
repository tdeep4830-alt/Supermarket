# 前端結構規範 (Frontend Blueprint) - React (Vite)

## 1. 技術棧 (Tech Stack)
- **Framework**: React 18+ (使用 Vite 作為構建工具)。
- **State Management**: **Zustand** (輕量、高性能，適合管理購物車與用戶狀態)。
- **Data Fetching**: **TanStack Query (React Query)** (處理 API 緩存、Loading 狀態及搶購時的即時數據刷新)。
- **Styling**: **Tailwind CSS** + **shadcn/ui** (組件庫)。
- **Validation**: **Zod** (確保 API 回傳數據與表單輸入符合 `data.md` 定義)。

## 2. 目錄組織 (Folder Structure)
遵循「功能模組化」與「職責分離」，與後端 App 結構對應：

```text
src/
├── api/                # Axios 實例與全局 API 定義
├── components/         # 公用 UI 組件 (Button, Input, Card)
├── features/           # 核心業務模組
│   ├── products/       # 商品列表、分類篩選
│   ├── cart/           # 購物車邏輯、側邊欄
│   ├── checkout/       # 結帳流程、優惠碼應用
│   └── auth/           # 用戶登入、積分顯示
├── hooks/              # 全局自定義 Hooks (如 useLocalStorage)
├── store/              # Zustand Stores (cartStore, userStore)
├── types/              # TypeScript Interfaces (需與 data.md 同步)
└── utils/              # 格式化工具 (如 priceFormatter)
```

3. 性能優化 (Vibe Coding Performance - Deep Dive)
為了確保在大量商品圖片和頻繁狀態更新下依然流暢，AI 必須遵循以下實作細節：

A. 智能圖片加載 (Smart Assets Management)：

Lazy Loading: 所有商品列表組件必須使用瀏覽器原生的 loading="lazy" 或 react-intersection-observer 實作延遲加載。

Blur-up 效果: 在圖片加載完成前，顯示佔位符（Skeleton Screen）或商品主色調的底色，防止頁面佈局抖動（CLS）。

B. 狀態更新頻率控制 (Throttling & Debouncing)：

購物車更新: 用戶連續點擊「+」增加數量時，前端應先透過 Zustand 更新 UI 數字，並對後端 API 請求進行 Debounce (500ms)，避免短時間內發送大量無效請求。

搜索輸入: 商品搜索框必須實作 Debounce，待用戶停止輸入 300ms 後才發起 API 請求。

C. 渲染優化 (Selective Rendering)：

Memoization: 對於複雜的商品卡片組件，必須使用 React.memo 封裝，防止因全局計時器（如搶購倒數）導致的無意義重複渲染。

Virtual List: 如果商品目錄超過 100 個品項，建議使用 react-window 實作虛擬列表。

4. 搶購交互邏輯 (Flash Sale UI Logic - Deep Dive)
這是超級市場專案的靈魂，AI 必須精準實作以下三個維度的邏輯：

A. 庫存同步與視覺反饋 (Stock Synchronization)：

React Query 同步: 搶購頁面需設定 staleTime: 2000 (2秒)，並開啟 refetchOnWindowFocus，確保用戶切換分頁回來後看到的是最新庫存。

動態庫存條: 庫存低於 10% 時，UI 需自動切換為紅色進度條並顯示「最後 X 件」，觸發用戶的緊迫感。

B. 樂觀鎖的前端處理 (Optimistic UI)：

下單狀態管理: 當用戶點擊「立即搶購」後，按鈕立即進入 loading 狀態並禁用，防止重複提交。

錯誤處理回滾: 若 API 回傳 409 Conflict (庫存版本衝突)，前端應立即顯示「有人快你一步，請重試」，並同步重整該商品的最新的 version 標記。

C. 支付閘道倒計時 (Order Lock Timer)：

鎖定期邏輯: 訂單建立後（PENDING），前端需啟動一個 15分鐘倒計時（與後端 Redis 鎖定時間一致）。

自動清理: 當倒計時結束，UI 需自動彈窗提示「訂單已過期」，並引導用戶返回購物車重新下單。