"""Database schema used by the application.

The schema intentionally stays small: one table per scraped source.  A stable
``source_key`` is computed by the repository and makes imports idempotent even
when a scraper returns the same row more than once.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    price REAL CHECK (price IS NULL OR price >= 0),
    availability TEXT,
    products_on_page INTEGER CHECK (
        products_on_page IS NULL OR products_on_page >= 0
    ),
    rating REAL CHECK (rating IS NULL OR (rating >= 0 AND rating <= 5)),
    review_count INTEGER CHECK (review_count IS NULL OR review_count >= 0),
    description TEXT,
    product_type TEXT,
    category TEXT,
    tax REAL CHECK (tax IS NULL OR tax >= 0),
    url TEXT,
    source_page INTEGER CHECK (source_page IS NULL OR source_page >= 1),
    scraped_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_books_product_type
    ON books(product_type);
CREATE INDEX IF NOT EXISTS idx_books_category
    ON books(category);
CREATE INDEX IF NOT EXISTS idx_books_rating
    ON books(rating);
CREATE INDEX IF NOT EXISTS idx_books_availability
    ON books(availability);

CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    brand TEXT NOT NULL CHECK (length(trim(brand)) > 0),
    model TEXT,
    year INTEGER CHECK (year IS NULL OR (year >= 1886 AND year <= 2100)),
    price REAL CHECK (price IS NULL OR price >= 0),
    mileage REAL CHECK (mileage IS NULL OR mileage >= 0),
    transmission TEXT,
    region TEXT,
    url TEXT,
    source_page INTEGER CHECK (source_page IS NULL OR source_page >= 1),
    scraped_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cars_brand ON cars(brand);
CREATE INDEX IF NOT EXISTS idx_cars_year ON cars(year);
CREATE INDEX IF NOT EXISTS idx_cars_region ON cars(region);
CREATE INDEX IF NOT EXISTS idx_cars_transmission ON cars(transmission);
"""
