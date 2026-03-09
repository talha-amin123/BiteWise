import sqlite3
from rapidfuzz import fuzz

DB_PATH = "data/bitewise.db"


def load_recalls():
    """Load all active, non-Spanish recalls with their products"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            r.recall_id,
            r.recall_source,
            r.recall_announcement_title,
            r.recall_reason,
            r.recall_brand_name,
            r.recall_company_name,
            r.recall_url,
            r.recall_announcement_date,
            r.recall_publish_date,
            r.recall_risk_level,
            p.product_id,
            p.product_description,
            p.raw_detail
        FROM recalls r
        JOIN products p ON r.recall_id = p.recall_id
        WHERE r.is_recall_terminated = 0
        AND r.recall_announcement_title NOT LIKE '%Retira%'
        AND r.recall_announcement_title NOT LIKE '%Alerta%'
    """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def normalize(text):
    if not text:
        return ""
    return " ".join(text.lower().split())


def hybrid_brand_score(brand, target):
    """
    Hybrid brand matching score.
    Blends multiple fuzzy signals with a length penalty.

    - ratio: strict character-by-character similarity
    - token_sort_ratio: handles word reordering
    - partial_ratio: finds best substring match
    - len_ratio: penalizes when strings are very different lengths

    This prevents short generic words like "signature" from
    matching long brand names like "kirkland signature".
    """
    if not brand or not target:
        return 0

    exact = fuzz.ratio(brand, target)
    sorted_score = fuzz.token_sort_ratio(brand, target)
    partial = fuzz.partial_ratio(brand, target)
    len_ratio = min(len(brand), len(target)) / max(len(brand), len(target))

    score = (exact * 0.3) + (sorted_score * 0.3) + (partial * 0.2) + (len_ratio * 100 * 0.2)
    return score


def hybrid_product_score(product, target):
    """
    Hybrid product matching score.
    More forgiving than brand matching since product names
    vary wildly between retailer and recall descriptions.

    - token_set_ratio: ignores word order and extra words (best for products)
    - token_sort_ratio: rewards same words in any order
    - partial_ratio: finds substring matches
    """
    if not product or not target:
        return 0

    set_score = fuzz.token_set_ratio(product, target)
    sorted_score = fuzz.token_sort_ratio(product, target)
    partial = fuzz.partial_ratio(product, target)

    score = (set_score * 0.4) + (sorted_score * 0.35) + (partial * 0.25)
    return score


def brand_match(brand_norm, recall_brand, recall_company):
    """
    Match Instacart brand against recall brand and company name.
    Returns the best score from both comparisons.
    """
    score_brand = hybrid_brand_score(brand_norm, recall_brand)
    score_company = hybrid_brand_score(brand_norm, recall_company)
    return max(score_brand, score_company)


def product_match(product_norm, brand_norm, recall_product, raw_detail, recall_title):
    """
    Match Instacart product name against recall product fields.
    Strips brand from product name first to avoid inflated scores.
    """
    # Remove brand name from product to compare just the product part
    product_clean = product_norm.replace(brand_norm, "").strip() if brand_norm else product_norm

    score_desc = hybrid_product_score(product_clean, recall_product)
    score_raw = hybrid_product_score(product_clean, raw_detail)
    score_title = hybrid_product_score(product_clean, recall_title)

    return max(score_desc, score_raw, score_title)


def match_product(brand, product_name, size=None, brand_threshold=75, product_threshold=60):
    """
    Match an Instacart product against the recall database.

    Tier 1: Brand match → must pass brand_threshold
    Tier 2: Product match
            → passes product_threshold → "high"
            → brand passed but product didn't → "warning"

    Returns list of matches sorted by score, deduplicated by recall_id.
    """
    recalls = load_recalls()
    brand_norm = normalize(brand)
    product_norm = normalize(product_name)
    matches = []

    for row in recalls:
        recall_brand = normalize(row["recall_brand_name"])
        recall_company = normalize(row["recall_company_name"])
        recall_product = normalize(row["product_description"])
        raw_detail = normalize(row["raw_detail"])
        recall_title = normalize(row["recall_announcement_title"])

        # Tier 1: Brand match
        b_score = brand_match(brand_norm, recall_brand, recall_company)

        if b_score < brand_threshold:
            continue

        # Tier 2: Product match
        p_score = product_match(product_norm, brand_norm, recall_product, raw_detail, recall_title)

        # Categorize
        if p_score >= product_threshold:
            match_level = "high"
        else:
            match_level = "warning"

        combined_score = round(b_score * 0.4 + p_score * 0.6, 1)

        matches.append({
            "recall_id": row["recall_id"],
            "score": combined_score,
            "brand_score": round(b_score, 1),
            "product_score": round(p_score, 1),
            "match_level": match_level,
            "recall_source": row["recall_source"],
            "recall_announcement_title": row["recall_announcement_title"],
            "recall_reason": row["recall_reason"],
            "recall_company_name": row["recall_company_name"],
            "recall_brand_name": row["recall_brand_name"],
            "recall_url": row["recall_url"],
            "recall_date": row["recall_announcement_date"] or row["recall_publish_date"],
            "recall_risk_level": row["recall_risk_level"],
            "product_description": row["product_description"],
        })

    # Deduplicate: keep highest score per recall_id
    seen = {}
    for m in matches:
        rid = m["recall_id"]
        if rid not in seen or m["score"] > seen[rid]["score"]:
            seen[rid] = m

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


if __name__ == "__main__":
    test_cases = [
        ("rosina", "Rosina Meatballs, Italian Style"),
        ("olympia provisions", "Olympia Provisions Bratwurst Sausage"),
        ("great value", "Great Value 4% Milkfat Minimum Small Curd Cottage Cheese"),
        ("prego", "Prego Marinara Sauce"),
        ("janes", "Janes Fu Zhou Fish Ball"),
        ("tippy toes", "Tippy Toes Banana Blueberry Apple Oat Organic Baby Food"),
        ("chips ahoy!", "Chips Ahoy! Baked Bites, Blondie"),
        ("spring & mulberry", "Spring & Mulberry Mint Leaf, Date Sweetened, 72% Dark Chocolate"),
        ("true sea moss", "True Sea Moss Strawberry Sea Moss Gel Superfood"),
        ("forward farms", "Forward Farms 85% Lean/15% Fat Ground Beef"),
        ("hormel compleats", "HORMEL COMPLEATS Chicken Breast & Gravy With Mashed Potatoes, 10 OZ"),
        ("golden island", "Golden Island Pork Snack Bites, Korean Barbecue, 1.5 oz, 12 ct"),
        ("kirkland signature", "Kirkland Signature Grass-Fed Beef Sticks, 1.15 oz, 12 ct")
    ]

    for brand, product in test_cases:
        print(f"\n--- {brand} / {product} ---")
        results = match_product(brand, product)
        if results:
            for r in results[:3]:
                print(f"  [{r['match_level'].upper()}] Score: {r['score']} (brand: {r['brand_score']}, product: {r['product_score']})")
                print(f"  {r['recall_source']}: {r['recall_announcement_title'][:80]}...")
        else:
            print("  No matches found")