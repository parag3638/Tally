-- 0001 initial schema: categories, payment_methods, expenses
-- The original three-table model. Multitenancy (user_id) is added in 0002.

CREATE TABLE IF NOT EXISTS categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS payment_methods (
    payment_method_id   SERIAL PRIMARY KEY,
    payment_method_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS expenses (
    transaction_id    SERIAL PRIMARY KEY,
    date              DATE,
    category_id       INTEGER REFERENCES categories(category_id),
    description       TEXT,
    amount            DECIMAL(10, 2),
    vat               DECIMAL(10, 2),
    payment_method_id INTEGER REFERENCES payment_methods(payment_method_id),
    business_personal VARCHAR(50),
    declared_on       DATE
);
