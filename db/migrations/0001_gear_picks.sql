-- 0001_gear_picks.sql — D1 affiliate pattern for the gear site (mirrors realufo's 0040_affiliate.sql).
-- products.json is the build-time source of truth; this table is the queryable record.
-- Seed with:  python3 build.py --dump-sql   (paste the INSERTs after creating the table)

CREATE TABLE IF NOT EXISTS gear_picks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  slug         TEXT NOT NULL,
  product_name TEXT NOT NULL,
  retailer     TEXT NOT NULL,
  url          TEXT NOT NULL,
  price_cents  INTEGER,
  asin         TEXT,
  notes        TEXT,
  updated_at   TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_gear_picks_slug_retailer
  ON gear_picks (slug, retailer);
