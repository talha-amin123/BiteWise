import sqlite3
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "bitewise.db")
SCHEMA_PATH = os.path.join(ROOT_DIR, "database", "schema.sql")
FDA_DATA = os.path.join(DATA_DIR, "fda_all_records.json")
FSIS_DATA = os.path.join(DATA_DIR, "fsis_all_records.json")


def create_db():
    """Create database from schema file"""
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    print("Database created from schema.sql")
    return conn


def insert_fda_records(conn, records):
    """Insert FDA records into recalls and products tables"""
    cursor = conn.cursor()
    fda_count = 0
    product_count = 0

    for record in records:
        if "error" in record:
            continue

        # Insert into recalls
        cursor.execute("""
            INSERT INTO recalls (
                recall_source, recall_announcement_title, recall_reason,
                recall_brand_name, recall_company_name, is_recall_terminated,
                recall_url, recall_announcement_date, recall_publish_date,
                recall_announcement_html, recall_announcement_text,
                recall_risk_level, recall_classification, recall_number_official,
                recall_states, recall_photo_urls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "FDA",
            record.get("announcement_title"),
            record.get("recall_reason"),
            record.get("brand_name"),
            record.get("company_name"),
            1 if record.get("is_terminated") else 0,
            record.get("detail_url"),
            record.get("company_announcement_date"),
            record.get("fda_publish_date"),
            record.get("announcement_html"),
            record.get("announcement_text"),
            None,  # risk_level — FDA doesn't have this
            None,  # recall_classification
            None,  # recall_number_official
            None,  # states
            json.dumps(record.get("photo_urls", [])),
        ))

        recall_id = cursor.lastrowid
        fda_count += 1

        # Extract product_type as comma-separated string
        product_type_list = record.get("product_type", [])
        product_type = ", ".join(product_type_list) if product_type_list else None

        # Insert into products
        product_details = record.get("product_details")

        if product_details and len(product_details) > 0:
            # Has structured product details (dicts with keys like Product, UPC, etc.)
            for item in product_details:
                if isinstance(item, dict):
                    # Try common keys for product description
                    desc = (
                        item.get("Product")
                        or item.get("product")
                        or item.get("Product Name")
                        or item.get("Description")
                        or str(item)
                    )
                    raw = json.dumps(item)
                else:
                    desc = str(item)
                    raw = str(item)

                cursor.execute("""
                    INSERT INTO products (recall_id, product_description, product_type, raw_detail)
                    VALUES (?, ?, ?, ?)
                """, (recall_id, desc, product_type, raw))
                product_count += 1
        else:
            # No product_details — use main product_description as single product
            cursor.execute("""
                INSERT INTO products (recall_id, product_description, product_type, raw_detail)
                VALUES (?, ?, ?, ?)
            """, (
                recall_id,
                record.get("product_description"),
                product_type,
                record.get("product_description"),
            ))
            product_count += 1

    print(f"FDA: {fda_count} recalls, {product_count} products inserted")
    return fda_count, product_count


def insert_fsis_records(conn, records):
    """Insert FSIS records into recalls and products tables"""
    cursor = conn.cursor()
    fsis_count = 0
    product_count = 0

    for record in records:
        if "error" in record:
            continue

        # Insert into recalls
        cursor.execute("""
            INSERT INTO recalls (
                recall_source, recall_announcement_title, recall_reason,
                recall_brand_name, recall_company_name, is_recall_terminated,
                recall_url, recall_announcement_date, recall_publish_date,
                recall_announcement_html, recall_announcement_text,
                recall_risk_level, recall_classification, recall_number_official,
                recall_states, recall_photo_urls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "FSIS",
            record.get("announcement_title"),
            record.get("recall_reason"),
            record.get("brand_name"),
            record.get("company_name"),
            1 if record.get("is_terminated") else 0,
            record.get("detail_url"),
            record.get("recall_date"),
            record.get("recall_date"),
            record.get("announcement_html"),
            record.get("announcement_text"),
            record.get("risk_level"),
            record.get("recall_classification"),
            record.get("recall_number"),
            record.get("states"),
            json.dumps(record.get("photo_urls", [])),
        ))

        recall_id = cursor.lastrowid
        fsis_count += 1

        # Insert into products
        product_details = record.get("product_details")

        if product_details and len(product_details) > 0:
            for item in product_details:
                cursor.execute("""
                    INSERT INTO products (recall_id, product_description, product_type, raw_detail)
                    VALUES (?, ?, ?, ?)
                """, (recall_id, str(item), None, str(item)))
                product_count += 1
        else:
            # Fallback to main product_description
            cursor.execute("""
                INSERT INTO products (recall_id, product_description, product_type, raw_detail)
                VALUES (?, ?, ?, ?)
            """, (
                recall_id,
                record.get("product_description"),
                None,
                record.get("product_description"),
            ))
            product_count += 1

    print(f"FSIS: {fsis_count} recalls, {product_count} products inserted")
    return fsis_count, product_count


if __name__ == "__main__":
    conn = create_db()

    # Load and insert FDA data
    with open(FDA_DATA, "r") as f:
        fda_records = json.load(f)
    print(f"\nLoaded {len(fda_records)} FDA records from JSON")
    insert_fda_records(conn, fda_records)

    # Load and insert FSIS data
    with open(FSIS_DATA, "r") as f:
        fsis_records = json.load(f)
    print(f"\nLoaded {len(fsis_records)} FSIS records from JSON")
    insert_fsis_records(conn, fsis_records)

    conn.commit()

    # Quick verification
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recalls")
    total_recalls = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    cursor.execute("SELECT recall_source, COUNT(*) FROM recalls GROUP BY recall_source")
    by_source = cursor.fetchall()

    print(f"\n--- Summary ---")
    print(f"Total recalls: {total_recalls}")
    print(f"Total products: {total_products}")
    for source, count in by_source:
        print(f"{source}: {count}")

    conn.close()
    print(f"\nDatabase saved to {DB_PATH}")
