PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS change_log (
    event_id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE,
    entity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload TEXT NOT NULL,
    digest TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS change_entity ON change_log(entity, entity_id, position);
CREATE TABLE IF NOT EXISTS quarantine (
    digest TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_history (
    customer_id TEXT NOT NULL,
    segment TEXT,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    is_deleted INTEGER NOT NULL,
    PRIMARY KEY (customer_id, valid_from)
);
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    segment TEXT,
    position INTEGER NOT NULL,
    is_deleted INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    status TEXT NOT NULL,
    position INTEGER NOT NULL
);
CREATE VIEW IF NOT EXISTS revenue_by_segment AS
SELECT CASE WHEN c.is_deleted = 1 THEN '[deleted]' ELSE c.segment END AS segment,
       COUNT(*) AS paid_orders, SUM(o.amount_cents) AS revenue_cents
FROM orders o JOIN customers c USING (customer_id)
WHERE o.status = 'paid'
GROUP BY 1;
