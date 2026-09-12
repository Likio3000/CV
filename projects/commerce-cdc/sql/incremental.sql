-- Rebuild complete histories only for entities accepted in this transaction.
-- Filtering precedes LEAD, but retains every journal version of each touched key.
DELETE FROM customer_history
WHERE customer_id IN (SELECT entity_id FROM touched WHERE entity = 'customer');
INSERT INTO customer_history
SELECT entity_id, json_extract(payload, '$.after.segment'), position,
       LEAD(position) OVER (PARTITION BY entity_id ORDER BY position), operation = 'd'
FROM change_log
WHERE entity = 'customer' AND entity_id IN
      (SELECT entity_id FROM touched WHERE entity = 'customer');

DELETE FROM customers
WHERE customer_id IN (SELECT entity_id FROM touched WHERE entity = 'customer');
INSERT INTO customers
SELECT customer_id, segment, valid_from, is_deleted
FROM customer_history WHERE valid_to IS NULL AND customer_id IN
     (SELECT entity_id FROM touched WHERE entity = 'customer');

DELETE FROM orders
WHERE order_id IN (SELECT entity_id FROM touched WHERE entity = 'order');
INSERT INTO orders
SELECT entity_id, json_extract(payload, '$.after.customer_id'),
       json_extract(payload, '$.after.amount_cents'),
       json_extract(payload, '$.after.status'), position
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY position DESC) AS rank
    FROM change_log WHERE entity = 'order' AND entity_id IN
         (SELECT entity_id FROM touched WHERE entity = 'order')
) WHERE rank = 1 AND operation <> 'd';
