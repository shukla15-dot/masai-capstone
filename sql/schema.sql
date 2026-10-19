-- ============================================================================
-- Part 1, Task 1 — Schema (6 marks)
-- Mamaearth Returns & Growth Intelligence Pipeline — relational layer.
--
-- Three tables: customers, products, orders.
-- Run first:   sqlite3 mamaearth.db < sql/schema.sql
--
-- Re-runnable: each table is dropped first, so running this file again rebuilds
-- a clean schema. (Drop orders before the tables it references.)
-- ============================================================================

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- Customers -------------------------------------------------------------------
CREATE TABLE customers (
    customer_id        VARCHAR(10)  PRIMARY KEY,
    name               VARCHAR(50)  NOT NULL,
    city               VARCHAR(50)  NOT NULL,
    city_tier          INT          NOT NULL,
    signup_date        DATE         NOT NULL,
    acquisition_source VARCHAR(20)  NOT NULL
);

-- Products --------------------------------------------------------------------
CREATE TABLE products (
    product_id   VARCHAR(10)   PRIMARY KEY,
    product_name VARCHAR(100)  NOT NULL,
    category     VARCHAR(30)   NOT NULL,
    price        DECIMAL(10,2) NOT NULL
);

-- Orders ----------------------------------------------------------------------
-- discount_pct and rating are intentionally nullable: a real order can carry no
-- promo code (NULL discount) and be un-rated (NULL rating). NULL is the correct
-- representation of "missing", not a constraint to design away. Part 2 cleans
-- these in Python; Part 1 reports run against the raw, uncleaned values.
CREATE TABLE orders (
    order_id       VARCHAR(10) PRIMARY KEY,
    customer_id    VARCHAR(10) NOT NULL,
    product_id     VARCHAR(10) NOT NULL,
    order_date     DATE        NOT NULL,
    quantity       INT         NOT NULL,
    discount_pct   INT,
    payment_method VARCHAR(10) NOT NULL,
    rating         INT,
    returned       INT         NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);
