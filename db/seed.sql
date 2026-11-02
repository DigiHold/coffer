-- Demo data only, never for production: it empties the tables first.
TRUNCATE payments, user_payment_methods, cart_items, carts, products, users;

-- The task's sample data, verbatim.
INSERT INTO users (id, email, name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'alice@example.com', 'Alice'),
    ('22222222-2222-2222-2222-222222222222', 'bob@example.com',   'Bob');

INSERT INTO products (id, name, price, currency, stock_quantity) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Blue Kettle',   45.00, 'USD',  10),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Wool Blanket',  89.99, 'USD',   5),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Ceramic Mug',   12.50, 'USD', 100);

INSERT INTO carts (id, user_id, status) VALUES
    ('c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1',
     '11111111-1111-1111-1111-111111111111',
     'active');

INSERT INTO cart_items (cart_id, product_id, quantity, unit_price) VALUES
    ('c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1',
     'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 1, 45.00),
    ('c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1',
     'cccccccc-cccc-cccc-cccc-cccccccccccc', 2, 12.50);

INSERT INTO user_payment_methods (id, user_id, provider_token, last_four, is_default) VALUES
    ('11111111-2222-3333-4444-555555555555',
     '11111111-1111-1111-1111-111111111111',
     'tok_test_alice_visa', '4242', TRUE);

-- One more user per scenario of scripts/demo.sh.
INSERT INTO users (id, email, name) VALUES
    ('33333333-3333-3333-3333-333333333333', 'carol@example.com', 'Carol'),
    ('44444444-4444-4444-4444-444444444444', 'dave@example.com',  'Dave'),
    ('55555555-5555-5555-5555-555555555555', 'erin@example.com',  'Erin');

INSERT INTO carts (id, user_id, status) VALUES
    ('c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2', '22222222-2222-2222-2222-222222222222', 'active'),
    ('c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', '33333333-3333-3333-3333-333333333333', 'active'),
    ('c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', '44444444-4444-4444-4444-444444444444', 'active'),
    ('c5c5c5c5-c5c5-c5c5-c5c5-c5c5c5c5c5c5', '55555555-5555-5555-5555-555555555555', 'active'),
    ('c6c6c6c6-c6c6-c6c6-c6c6-c6c6c6c6c6c6', '11111111-1111-1111-1111-111111111111', 'abandoned');

-- Erin's cart stays empty.
INSERT INTO cart_items (cart_id, product_id, quantity, unit_price) VALUES
    ('c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 1, 89.99),
    ('c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 4, 12.50),
    ('c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 1, 45.00),
    ('c6c6c6c6-c6c6-c6c6-c6c6-c6c6c6c6c6c6', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 1, 12.50);

-- Carol has no card. The mock provider decides from the token.
INSERT INTO user_payment_methods (user_id, provider_token, last_four, is_default) VALUES
    ('22222222-2222-2222-2222-222222222222', 'tok_test_bob_decline',      '0002', TRUE),
    ('44444444-4444-4444-4444-444444444444', 'tok_test_dave_unavailable', '0119', TRUE),
    ('55555555-5555-5555-5555-555555555555', 'tok_test_erin_visa',        '1881', TRUE);
