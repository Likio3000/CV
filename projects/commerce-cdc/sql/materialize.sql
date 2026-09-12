-- Rebuild from the journal: late source positions repair history deterministically.
-- These statements run inside the same transaction as journal insertion.
DELETE FROM customer_history;
INSERT INTO customer_history
SELECT entity_id,
       json_extract(payload, '$.after.segment'),
       position,
       LEAD(position) OVER (PARTITION BY entity_id ORDER BY position),
       operation = 'd'
FROM change_log WHERE entity = 'customer';

DELETE FROM customers;
INSERT INTO customers
SELECT customer_id, segment, valid_from, is_deleted
FROM customer_history WHERE valid_to IS NULL;

DELETE FROM orders;
INSERT INTO orders
SELECT entity_id,
       json_extract(payload, '$.after.customer_id'),
       json_extract(payload, '$.after.amount_cents'),
       json_extract(payload, '$.after.status'), position
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY position DESC) AS rank
    FROM change_log WHERE entity = 'order'
) WHERE rank = 1 AND operation <> 'd';
