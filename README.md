# VVIP（Tele-Marketing 土地開發情資系統）

## 專案目的與用途

VVIP 是一套以 Django 開發的 **土地開發情資查詢與帳戶管理系統**，主要服務電銷／土地開發從業人員。系統提供：

- **土地開發搜尋**：依地建號、地段、實價登錄等條件查詢土地與建物情資。
- **多租戶帳戶管理**：以公司為單位管理子網域、開放地區與成員權限。
- **會員與權限管理**：區分老闆、主管、專員等角色，並可管理密碼、帳號清單與新增／編輯帳號。
- **API 與整合**：提供 REST API（含 Swagger/ReDoc）供公司與使用者等維運與整合使用。

適用情境：需依地區與條件查詢土地／建物資料、管理多公司多帳號、並依權限使用查詢與下載（如總歸戶、PDF）的團隊。

---

## 主要功能概覽

| 模組 | 說明 |
|------|------|
| **土地開發** | 地建號查詢、地段／區域篩選、實價資料、計畫名稱／暱稱、總歸戶、PDF 下載、地建號等級設定等。 |
| **帳號管理** | 帳號管理登入、公司帳號列表、新增／編輯帳號、取得 Logo。 |
| **會員管理** | 會員密碼、帳號清單、新增／編輯會員帳號。 |
| **Users API** | 公司與使用者之 CRUD API（需登入／Token）。 |
| **API 文件** | Swagger UI、ReDoc（登入後可於 `/api/schema/swagger-ui/` 使用）。 |

---

## 操作介紹

### 入口與登入

- **首頁**：`/` → 登入頁（帳號、密碼、記住我）。
- **土地開發主頁**：登入後可進入 `/v_search/land_dev/` 進行土地開發查詢。
- **帳號管理登入**：`/v_search/account_manage_login/`。
- **帳號管理**：`/v_search/account_manage/`（公司帳號列表、編輯、新增）。
- **會員相關**：密碼頁、帳號清單、新增／編輯會員等（`/v_search/member_pw/`、`member_aclist/`、`member_newac/`、`member_editac/`）。

### 土地開發查詢流程（概念）

1. 登入後進入「土地開發」。
2. 選擇縣市、區、地段等條件，必要時選擇計畫名稱／暱稱。
3. 送出查詢後可檢視地建號、實價等結果；可進行總歸戶、設定地建號等級、下載 PDF 等。

### API 與文件

- **Schema**：`/api/schema/`
- **Swagger UI**（需登入）：`/api/schema/swagger-ui/`
- **ReDoc**：`/api/schema/redoc/`
- **Users API**：`/users/` 底下各端點（公司／使用者列表、新增、查詢、修改等）。

---

## 技術架構

- **後端**：Django 4.x、Django REST Framework、django-allauth、drf-spectacular
- **資料庫**：預設 SQLite；可透過 `local_settings.py` 改為 MySQL/MariaDB，並使用 `DATABASE_ROUTERS` 分庫（如 `t_search` 指向 `diablo_test`）
- **快取**：django-redis（需 Redis）
- **其他**：Celery、uWSGI、Nginx 等可選（部署用）

---

## 環境需求與安裝（Mac）

- **Python**：建議 **3.8～3.12**（專案使用 Django 4.0，不支援 Python 3.13+；若使用 3.14 會出現 `No module named 'cgi'` 等錯誤）。
- 可透過 `pyenv install 3.10` 或 `brew install python@3.10` 安裝指定版本，並用該直譯器建立虛擬環境。

### 依賴套件（建議使用 Homebrew）

```bash
# 安裝 Homebrew（若尚未安裝）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝常用套件
brew install python@3.8
brew install libpython
brew install mysql    # 若使用 MySQL
brew install gdal    # 若需要 GIS 相關
```

### 切換 Python 版本（可選）

```bash
ls -l /usr/local/bin/python*
ln -s -f /usr/local/bin/python3.8 /usr/local/bin/python
```

### 安裝專案依賴

```bash
# 從專案目錄執行（或依團隊慣例使用 venv）
bash install.mac.sh
```

或手動建立虛擬環境並安裝：

```bash
cd /path/to/vvip
python3 -m venv ../venv_vvip
source ../venv_vvip/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
```

> 若 `requirements.txt` 內含私有 `--extra-index-url` 且無法連線，可暫時註解該行再安裝，或依團隊提供之方式安裝 `wsos_common`。

### 本地設定（可選）

複製範例並依需求修改，用於啟用 DEBUG、ALLOWED_HOSTS、MySQL、Redis 等：

```bash
cp local_settings.py.example local_settings.py
# 編輯 local_settings.py：DEBUG、ALLOWED_HOSTS、DATABASES、CACHES 等
```

---

## 啟動專案

```bash
# 啟用虛擬環境（若使用）
. ../venv_vvip/bin/activate

# 進入專案目錄
cd /path/to/vvip

# 資料庫遷移（首次或模型異動後）
python manage.py makemigrations
python manage.py migrate

# 建立超級使用者（首次，用於後台與測試）
python manage.py createsuperuser

# 靜態檔（部署或 DEBUG 時若需要）
python manage.py collectstatic --noinput

# 啟動開發伺服器（預設 port 8000）
python manage.py runserver 8000
```

瀏覽器開啟：**http://127.0.0.1:8000/**  
若已設定 `local_settings.py` 的 `ALLOWED_HOSTS`，可改用對應 host/port。

**若啟動失敗**：請確認 Python 為 3.8～3.12（例如 `python3.10 -m venv .venv && source .venv/bin/activate` 後再執行上述指令）。若未安裝 Redis，可於 `local_settings.py` 覆寫 `CACHES` 為 `'BACKEND': 'django.core.cache.backends.dummy.DummyCache'` 以僅做功能測試。

---

## 常用指令參考

### 建立超級使用者

```bash
python manage.py createsuperuser
```

### 建立新 App

```bash
python manage.py startapp <app_name>
```

### 資料表更新

```bash
python manage.py makemigrations
python manage.py migrate
```

### 查看遷移狀態

```bash
python manage.py showmigrations
```

### 重置資料庫（危險：清空表內資料）

> 注意：執行後所有表內資料會被清空，超級使用者也會被刪除。

```bash
python manage.py flush
```

---

## 目錄與模組簡述

- **vvip/**：Django 專案設定（`settings.py`、`urls.py`、`wsgi.py`、`db_router.py`）。
- **v_search/**：土地開發搜尋、帳號／會員管理之 views、templates、static、API。
- **users/**：使用者與公司模型、API（公司／使用者 CRUD）。
- **t_search/**：情資相關模型與邏輯（可對應外部 DB）。
- **fake_data/**：範例或假資料（如地區代碼、登記原因等 CSV）。

---

## 授權與備註

本專案為內部 Tele-Marketing／土地開發情資系統，實際對外網址與權限請依團隊規範使用。
