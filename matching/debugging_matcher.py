import json

from matching.matcher import match_product


def print_matches(brand, product_name, size=""):
    """Debug a single product query against the local recall database."""
    results = match_product(brand, product_name, size)

    print(f"Query: brand={brand!r}, product_name={product_name!r}, size={size!r}")
    print(f"Matches found: {len(results)}")

    for index, match in enumerate(results[:5], start=1):
        print(f"\nMatch {index}")
        print(json.dumps(match, indent=2))


if __name__ == "__main__":
    print_matches(
        brand="rosina",
        product_name="Rosina Meatballs, Italian Style",
        size="26 oz",
    )
