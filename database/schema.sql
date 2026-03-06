-- BiteWise Database Schema
-- SQLite3
-- Two normalized tables: recalls (one per event) → products (one per product listing)

CREATE TABLE IF NOT EXISTS recalls (
    recall_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recall_entry_created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    recall_entry_updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    recall_source TEXT NOT NULL CHECK (recall_source IN ('FDA', 'FSIS')),
    recall_announcement_title TEXT,
    recall_reason TEXT,
    recall_brand_name TEXT,
    recall_company_name TEXT,
    is_recall_terminated INTEGER NOT NULL DEFAULT 0,
    recall_url TEXT,
    recall_announcement_date TEXT,
    recall_publish_date TEXT,
    recall_announcement_html TEXT,
    recall_announcement_text TEXT,
    recall_risk_level TEXT,
    recall_classification TEXT,
    recall_number_official TEXT,
    recall_states TEXT,
    recall_photo_urls TEXT
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recall_id INTEGER NOT NULL,
    product_description TEXT,
    product_type TEXT,
    raw_detail TEXT,
    FOREIGN KEY (recall_id) REFERENCES recalls (recall_id) ON DELETE CASCADE
);

-- Indexes for matching queries
CREATE INDEX IF NOT EXISTS idx_recalls_source ON recalls (recall_source);
CREATE INDEX IF NOT EXISTS idx_recalls_brand ON recalls (recall_brand_name);
CREATE INDEX IF NOT EXISTS idx_recalls_company ON recalls (recall_company_name);
CREATE INDEX IF NOT EXISTS idx_recalls_terminated ON recalls (is_recall_terminated);
CREATE INDEX IF NOT EXISTS idx_products_recall_id ON products (recall_id);