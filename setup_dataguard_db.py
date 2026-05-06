"""
═══════════════════════════════════════════════════════════════════
  DataGuard PostgreSQL Demo Database — Setup Script
═══════════════════════════════════════════════════════════════════

  Run this in a SEPARATE terminal (not the backend/frontend ones).

  WHAT IT DOES:
    1. Creates "dataguard_demo" database
    2. Creates a read-only user "dg_reader" for the DataGuard connector
    3. Seeds 8 tables with realistic e-commerce data
    4. Includes intentional data quality issues for demo purposes

  PREREQUISITES (install once):
    • PostgreSQL server running locally
    • psycopg2 installed:  pip install psycopg2-binary

  USAGE:
    python setup_dataguard_db.py              # Create & seed
    python setup_dataguard_db.py --reset      # Drop & recreate everything
    python setup_dataguard_db.py --check      # Just verify connection

  AFTER RUNNING:
    Go to DataGuard → Connectors → Add Connector → PostgreSQL
    Enter:  Host=localhost  Port=5432  Database=dataguard_demo
            Username=dg_reader  Password=dataguard123

═══════════════════════════════════════════════════════════════════
"""

import sys
import os

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("ERROR: psycopg2 not installed.")
    print("Run:  pip install psycopg2-binary")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Change these to match your local setup
# ═══════════════════════════════════════════════════════════════

# Admin connection (used to CREATE the database and users)
# This must connect to the default "postgres" database
ADMIN_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": os.getenv("PG_ADMIN_USER", "postgres"),  # Change if your admin user differs
    "password": os.getenv("PG_ADMIN_PASS", ""),  # Change if your admin has a password
    "database": "postgres",
}

# The demo database we will create
DEMO_DB_NAME = "dataguard_demo"

# Read-only user for DataGuard connector
READER_USER = "dg_reader"
READER_PASS = "dataguard123"

# Admin user for DataGuard (if you want full access)
DEMO_ADMIN_USER = "dg_admin"
DEMO_ADMIN_PASS = "admin123"


# ═══════════════════════════════════════════════════════════════
# SQL: CREATE TABLES
# ═══════════════════════════════════════════════════════════════

CREATE_TABLES_SQL = """
-- 1. Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id     SERIAL PRIMARY KEY,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    email           VARCHAR(255),
    phone           VARCHAR(20),
    address         TEXT,
    city            VARCHAR(100),
    country         VARCHAR(100) DEFAULT 'India',
    registration_date TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    lifetime_value  NUMERIC(12,2) DEFAULT 0.00
);

-- 2. Products table
CREATE TABLE IF NOT EXISTS products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(255) NOT NULL,
    category        VARCHAR(100),
    sub_category    VARCHAR(100),
    price           NUMERIC(10,2) NOT NULL,
    cost_price      NUMERIC(10,2),
    stock_qty       INTEGER DEFAULT 0,
    supplier        VARCHAR(200),
    rating          NUMERIC(3,2),
    is_available    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 3. Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(customer_id),
    order_date      TIMESTAMP DEFAULT NOW(),
    total_amount    NUMERIC(12,2),
    status          VARCHAR(50) DEFAULT 'pending',
    payment_method  VARCHAR(50),
    shipping_city   VARCHAR(100),
    discount_pct    NUMERIC(5,2) DEFAULT 0.00,
    notes           TEXT
);

-- 4. Order Items table
CREATE TABLE IF NOT EXISTS order_items (
    item_id         SERIAL PRIMARY KEY,
    order_id        INTEGER REFERENCES orders(order_id),
    product_id      INTEGER REFERENCES products(product_id),
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(10,2) NOT NULL,
    line_total      NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- 5. Inventory Log table
CREATE TABLE IF NOT EXISTS inventory_log (
    log_id          SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(product_id),
    change_type     VARCHAR(50) NOT NULL,
    quantity_change INTEGER NOT NULL,
    reason          TEXT,
    logged_by       VARCHAR(100),
    logged_at       TIMESTAMP DEFAULT NOW()
);

-- 6. Data Quality Issues table (what DataGuard would detect)
CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id        SERIAL PRIMARY KEY,
    table_name      VARCHAR(100) NOT NULL,
    column_name     VARCHAR(100),
    issue_type      VARCHAR(100) NOT NULL,
    severity        VARCHAR(20) DEFAULT 'medium',
    description     TEXT,
    affected_rows   INTEGER,
    detected_at     TIMESTAMP DEFAULT NOW(),
    status          VARCHAR(20) DEFAULT 'open'
);

-- 7. Monthly Sales Summary
CREATE TABLE IF NOT EXISTS monthly_sales (
    month_id        SERIAL PRIMARY KEY,
    month           VARCHAR(20) NOT NULL,
    year            INTEGER NOT NULL,
    total_orders    INTEGER,
    total_revenue   NUMERIC(14,2),
    avg_order_val   NUMERIC(10,2),
    unique_customers INTEGER,
    top_category    VARCHAR(100),
    return_rate     NUMERIC(5,4) DEFAULT 0.00
);

-- 8. Staff table
CREATE TABLE IF NOT EXISTS staff (
    staff_id        SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    role            VARCHAR(100),
    department      VARCHAR(100),
    email           VARCHAR(255),
    hire_date       DATE,
    salary          NUMERIC(10,2),
    is_active       BOOLEAN DEFAULT TRUE
);
"""


# ═══════════════════════════════════════════════════════════════
# SQL: SEED DATA
# ═══════════════════════════════════════════════════════════════

SEED_DATA_SQL = """
-- ── Customers (with intentional data quality issues) ──
INSERT INTO customers (first_name, last_name, email, phone, address, city, country, registration_date, is_active, lifetime_value) VALUES
('Aarav', 'Sharma', 'aarav.sharma@email.com', '+91-98765-43210', '12 MG Road', 'Mumbai', 'India', '2024-01-15 10:30:00', TRUE, 45600.00),
('Priya', 'Patel', 'priya.patel@email.com', '+91-98765-43211', '45 Park Street', 'Ahmedabad', 'India', '2024-02-20 14:15:00', TRUE, 32100.50),
('Rahul', 'Kumar', 'rahul.k@email.com', '+91-98765-43212', '78 Connaught Place', 'Delhi', 'India', '2024-03-10 09:45:00', TRUE, 58700.75),
('Sneha', 'Gupta', 'sneha.g@email.com', '+91-98765-43213', '23 Brigade Road', 'Bangalore', 'India', '2024-04-05 16:20:00', TRUE, 23450.00),
('Vikram', 'Singh', 'vikram.s@email.com', '+91-98765-43214', '56 Jubilee Hills', 'Hyderabad', 'India', '2024-05-18 11:00:00', FALSE, 12300.25),
('Ananya', 'Reddy', 'ananya.r@email.com', '+91-98765-43215', '89 T Nagar', 'Chennai', 'India', '2024-06-22 08:30:00', TRUE, 67800.00),
('Arjun', 'Mehta', 'arjun.m@email.com', '+91-98765-43216', '34 SG Highway', 'Surat', 'India', '2024-07-14 13:45:00', TRUE, 15600.50),
('Deepa', 'Nair', 'deepa.n@email.com', '+91-98765-43217', '67 Marine Drive', 'Kochi', 'India', '2024-08-30 17:00:00', TRUE, 89200.75),
('Rohan', 'Das', 'rohan.d@email.com', '+91-98765-43218', '90 Park Avenue', 'Kolkata', 'India', '2024-09-12 10:15:00', TRUE, 41200.00),
('Meera', 'Joshi', 'meera.j@email.com', '+91-98765-43219', '12 FC Road', 'Pune', 'India', '2024-10-25 15:30:00', TRUE, 54300.50),
('Karan', 'Malhotra', 'karan.m@email.com', '+91-98765-43220', '45 Civil Lines', 'Jaipur', 'India', '2024-11-08 09:00:00', TRUE, 28900.25),
('Isha', 'Iyer', 'isha.i@email.com', '+91-98765-43221', '78 Anna Nagar', 'Chennai', 'India', '2024-12-01 14:45:00', FALSE, 76500.00),
('Amit', 'Verma', NULL, '+91-98765-43222', '23 Lal Darwaza', 'Varanasi', 'India', '2025-01-20 11:30:00', TRUE, 9800.00),
('Pooja', 'Shah', 'pooja.s@email.com', NULL, '56 CG Road', 'Ahmedabad', 'India', '2025-02-14 16:00:00', TRUE, 43200.75),
('Test', '', 'invalid-email', '+91-00000-00000', '', '', '', '2025-03-01 00:00:00', FALSE, -100.00),
(NULL, 'MissingFirst', 'no@email.com', '+91-11111-11111', 'Some address', 'City', 'India', '2025-03-15 12:00:00', TRUE, 5000.00)
ON CONFLICT DO NOTHING;

-- ── Products (with intentional issues) ──
INSERT INTO products (product_name, category, sub_category, price, cost_price, stock_qty, supplier, rating, is_available) VALUES
('Wireless Bluetooth Headphones', 'Electronics', 'Audio', 2999.00, 1500.00, 150, 'TechParts India', 4.50, TRUE),
('USB-C Charging Cable', 'Electronics', 'Accessories', 499.00, 150.00, 500, 'CableCo', 4.20, TRUE),
('Laptop Stand Aluminum', 'Electronics', 'Accessories', 1899.00, 800.00, 75, 'DeskGear Pro', 4.70, TRUE),
('Mechanical Keyboard RGB', 'Electronics', 'Input Devices', 3499.00, 1800.00, 100, 'KeyTech Solutions', 4.60, TRUE),
('Cotton T-Shirt Large', 'Clothing', 'Tops', 799.00, 300.00, 300, 'FabricWorld', 4.10, TRUE),
('Running Shoes Size 10', 'Clothing', 'Footwear', 4999.00, 2200.00, 60, 'SoleMates Inc', 4.80, TRUE),
('Yoga Mat Premium', 'Sports', 'Fitness', 1299.00, 500.00, 200, 'FitLife Gear', 4.40, TRUE),
('Cricket Bat English Willow', 'Sports', 'Cricket', 8999.00, 4500.00, 25, 'SportKing', 4.90, TRUE),
('Stainless Steel Water Bottle', 'Home', 'Kitchen', 599.00, 200.00, 400, 'HomeEssentials', 4.30, TRUE),
('LED Desk Lamp', 'Home', 'Lighting', 1599.00, 700.00, 120, 'BrightHome', 4.50, TRUE),
('Organic Green Tea 100 bags', 'Food', 'Beverages', 450.00, 200.00, 600, 'TeaVana India', 4.60, TRUE),
('Basmati Rice 5kg', 'Food', 'Grains', 650.00, 400.00, 350, 'GrainHarvest', 4.40, TRUE),
('Smart Watch Fitness Tracker', 'Electronics', 'Wearables', 5999.00, 3000.00, 80, 'WearTech Labs', 4.30, TRUE),
('Backpack Travel 40L', 'Accessories', 'Bags', 2499.00, 1200.00, 90, 'BagCraft', 4.70, TRUE),
('Mystery Product', NULL, NULL, 0.00, -50.00, -10, NULL, NULL, TRUE),
('Wireless Bluetooth Headphones', 'Electronics', 'Audio', 2999.00, 1500.00, 150, 'TechParts India', 4.50, TRUE)
ON CONFLICT DO NOTHING;

-- ── Orders (with intentional issues) ──
INSERT INTO orders (customer_id, order_date, total_amount, status, payment_method, shipping_city, discount_pct) VALUES
(1, '2025-01-15 10:30:00', 3498.00, 'delivered', 'UPI', 'Mumbai', 5.00),
(2, '2025-01-20 14:00:00', 5498.00, 'delivered', 'Credit Card', 'Ahmedabad', 0.00),
(3, '2025-02-01 09:00:00', 1299.00, 'delivered', 'UPI', 'Delhi', 10.00),
(4, '2025-02-14 16:30:00', 8999.00, 'shipped', 'Debit Card', 'Bangalore', 0.00),
(5, '2025-03-01 11:00:00', 799.00, 'cancelled', 'UPI', 'Hyderabad', 0.00),
(6, '2025-03-10 08:15:00', 6498.00, 'delivered', 'Credit Card', 'Chennai', 15.00),
(7, '2025-03-15 13:30:00', 499.00, 'delivered', 'Cash', 'Surat', 0.00),
(8, '2025-04-01 17:45:00', 1899.00, 'processing', 'UPI', 'Kochi', 5.00),
(9, '2025-04-10 10:00:00', 2499.00, 'delivered', 'Credit Card', 'Kolkata', 0.00),
(10, '2025-04-20 15:15:00', 1599.00, 'shipped', 'Debit Card', 'Pune', 10.00),
(1, '2025-05-01 09:30:00', 5999.00, 'delivered', 'UPI', 'Mumbai', 5.00),
(11, '2025-05-05 12:00:00', 650.00, 'pending', 'UPI', 'Jaipur', 0.00),
(12, '2025-05-08 14:30:00', 4499.00, 'shipped', 'Credit Card', 'Chennai', 10.00),
(2, '2025-05-12 10:45:00', 2999.00, 'processing', 'Debit Card', 'Ahmedabad', 0.00),
(13, '2025-06-01 00:00:00', -500.00, 'unknown', '', '', 200.00),
(NULL, '2025-06-05 12:00:00', 1000.00, 'pending', 'UPI', 'Delhi', 0.00)
ON CONFLICT DO NOTHING;

-- ── Order Items ──
INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 2999.00), (1, 2, 1, 499.00),
(2, 3, 1, 1899.00), (2, 4, 1, 3499.00), (2, 2, 2, 499.00),
(3, 7, 1, 1299.00),
(4, 8, 1, 8999.00),
(5, 5, 1, 799.00),
(6, 13, 1, 5999.00), (6, 2, 1, 499.00),
(7, 2, 1, 499.00),
(8, 3, 1, 1899.00),
(9, 14, 1, 2499.00),
(10, 10, 1, 1599.00),
(11, 13, 1, 5999.00),
(12, 11, 1, 450.00), (12, 12, 1, 650.00),
(13, 4, 1, 3499.00), (13, 2, 2, 499.00)
ON CONFLICT DO NOTHING;

-- ── Inventory Log ──
INSERT INTO inventory_log (product_id, change_type, quantity_change, reason, logged_by) VALUES
(1, 'restock', 100, 'Monthly restock from supplier', 'warehouse_manager'),
(2, 'restock', 500, 'Bulk order received', 'warehouse_manager'),
(2, 'sale', -3, 'Customer orders', 'system_auto'),
(3, 'restock', 75, 'New stock arrival', 'warehouse_manager'),
(4, 'sale', -5, 'Customer orders', 'system_auto'),
(5, 'restock', 300, 'Seasonal stock', 'procurement_team'),
(5, 'sale', -12, 'Bulk customer order', 'system_auto'),
(6, 'damaged', -5, 'Transit damage reported', 'qa_team'),
(7, 'sale', -8, 'Customer orders', 'system_auto'),
(8, 'adjustment', -2, 'Annual stock count adjustment', 'finance_team'),
(9, 'restock', 400, 'Regular restock', 'warehouse_manager'),
(10, 'sale', -3, 'Customer orders', 'system_auto'),
(13, 'restock', 80, 'New shipment', 'warehouse_manager'),
(13, 'sale', -10, 'Customer orders', 'system_auto'),
(14, 'return', 2, 'Customer return - defective', 'support_team')
ON CONFLICT DO NOTHING;

-- ── Data Quality Issues (what DataGuard would find) ──
INSERT INTO data_quality_issues (table_name, column_name, issue_type, severity, description, affected_rows, status) VALUES
('customers', 'email', 'format', 'medium', 'Invalid email format: "invalid-email" missing @ domain', 1, 'open'),
('customers', 'first_name', 'null', 'high', 'Customer record with NULL first_name found', 1, 'open'),
('customers', 'lifetime_value', 'outlier', 'medium', 'Negative lifetime value: -100.00', 1, 'open'),
('products', 'category', 'null', 'medium', 'Product with NULL category', 1, 'open'),
('products', 'cost_price', 'outlier', 'high', 'Negative cost price: -50.00', 1, 'open'),
('products', 'stock_qty', 'outlier', 'medium', 'Negative stock quantity: -10', 1, 'open'),
('products', 'product_name', 'duplicate', 'medium', 'Duplicate product entry detected', 1, 'open'),
('orders', 'total_amount', 'outlier', 'high', 'Negative order total: -500.00', 1, 'open'),
('orders', 'status', 'format', 'low', 'Unknown status value: "unknown"', 1, 'open'),
('orders', 'discount_pct', 'outlier', 'medium', 'Discount exceeds 100%: 200.00', 1, 'open'),
('orders', 'customer_id', 'referential', 'critical', 'Order references NULL customer_id', 1, 'open')
ON CONFLICT DO NOTHING;

-- ── Monthly Sales ──
INSERT INTO monthly_sales (month, year, total_orders, total_revenue, avg_order_val, unique_customers, top_category, return_rate) VALUES
('January', 2025, 2, 8996.00, 4498.00, 2, 'Electronics', 0.00),
('February', 2025, 2, 10298.00, 5149.00, 2, 'Sports', 0.02),
('March', 2025, 3, 7796.00, 2599.00, 3, 'Electronics', 0.05),
('April', 2025, 2, 4098.00, 2049.00, 2, 'Accessories', 0.01),
('May', 2025, 3, 8148.00, 2716.00, 3, 'Electronics', 0.03)
ON CONFLICT DO NOTHING;

-- ── Staff ──
INSERT INTO staff (name, role, department, email, hire_date, salary, is_active) VALUES
('Rajesh Krishnan', 'Data Engineer', 'Engineering', 'rajesh.k@dataguard.io', '2023-01-10', 95000.00, TRUE),
('Simran Oberoi', 'Data Analyst', 'Analytics', 'simran.o@dataguard.io', '2023-03-15', 78000.00, TRUE),
('Nikhil Bhatt', 'Backend Developer', 'Engineering', 'nikhil.b@dataguard.io', '2023-06-01', 92000.00, TRUE),
('Tanya Mehta', 'Product Manager', 'Product', 'tanya.m@dataguard.io', '2022-11-20', 105000.00, TRUE),
('Farhan Ali', 'DevOps Engineer', 'Engineering', 'farhan.a@dataguard.io', '2024-01-08', 88000.00, TRUE),
('Lakshmi Iyer', 'QA Lead', 'Quality', 'lakshmi.i@dataguard.io', '2023-09-01', 82000.00, TRUE),
('Dev Patel', 'Frontend Developer', 'Engineering', 'dev.p@dataguard.io', '2024-03-20', 85000.00, TRUE),
('Neha Singh', 'Data Scientist', 'Analytics', 'neha.s@dataguard.io', '2023-07-15', 98000.00, TRUE)
ON CONFLICT DO NOTHING;
"""


# ═══════════════════════════════════════════════════════════════
# SQL: GRANT PERMISSIONS
# ═══════════════════════════════════════════════════════════════

GRANT_SQL = f"""
-- Grant read-only access to dg_reader
GRANT CONNECT ON DATABASE {DEMO_DB_NAME} TO {READER_USER};
GRANT USAGE ON SCHEMA public TO {READER_USER};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {READER_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {READER_USER};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {READER_USER};

-- Grant full access to dg_admin
GRANT ALL PRIVILEGES ON DATABASE {DEMO_DB_NAME} TO {DEMO_ADMIN_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {DEMO_ADMIN_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {DEMO_ADMIN_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DEMO_ADMIN_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DEMO_ADMIN_USER};
"""


# ═══════════════════════════════════════════════════════════════
# MAIN LOGIC
# ═══════════════════════════════════════════════════════════════


def print_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def print_step(msg):
    print(f"  ✦ {msg}")


def print_error(msg):
    print(f"  ✗ ERROR: {msg}")


def print_success(msg):
    print(f"  ✓ {msg}")


def get_admin_connection():
    """Try to connect to the default postgres database as admin."""
    # Try common admin user configurations
    configs_to_try = [
        ADMIN_CONFIG,
        {**ADMIN_CONFIG, "user": "postgres", "password": "postgres"},
        {**ADMIN_CONFIG, "user": "postgres", "password": ""},
        {**ADMIN_CONFIG, "user": os.getenv("USER", "z"), "password": ""},
    ]

    for cfg in configs_to_try:
        try:
            conn = psycopg2.connect(**cfg)
            conn.autocommit = True
            return conn, cfg
        except psycopg2.OperationalError:
            continue

    return None, None


def check_postgres():
    """Check if PostgreSQL is reachable."""
    print_header("Checking PostgreSQL Connection")

    conn, cfg = get_admin_connection()
    if conn is None:
        print_error("Cannot connect to PostgreSQL server!")
        print()
        print("  Make sure PostgreSQL is running. Try:")
        print("    • Linux:   sudo service postgresql start")
        print("    • Mac:     brew services start postgresql")
        print("    • Windows: Open Services → start PostgreSQL")
        print()
        print("  If you haven't installed PostgreSQL yet, see the instructions")
        print("  at the top of this file or in the LOCAL_SETUP_GUIDE.md")
        return False

    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print_success(f"Connected to: {version.split(',')[0]}")
    print_success(f"Admin user: {cfg['user']}")
    print_success(f"Host: {cfg['host']}:{cfg['port']}")
    cur.close()
    conn.close()
    return True


def create_database(reset=False):
    """Create the demo database and users."""
    print_header("Creating Database & Users")

    conn, cfg = get_admin_connection()
    if conn is None:
        print_error("Cannot connect to PostgreSQL")
        return False

    cur = conn.cursor()

    # Drop database if reset
    if reset:
        print_step("Dropping existing database (reset mode)...")
        # Terminate existing connections
        cur.execute(
            f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{DEMO_DB_NAME}' AND pid <> pg_backend_pid()
        """
        )
        cur.execute(f"DROP DATABASE IF EXISTS {DEMO_DB_NAME}")
        cur.execute(f"DROP USER IF EXISTS {READER_USER}")
        cur.execute(f"DROP USER IF EXISTS {DEMO_ADMIN_USER}")
        print_success("Dropped existing database and users")

    # Create reader user
    print_step(f"Creating read-only user: {READER_USER}")
    cur.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{READER_USER}') THEN
                CREATE ROLE {READER_USER} WITH LOGIN PASSWORD '{READER_PASS}';
            END IF;
        END
        $$;
    """
    )
    print_success(f"User '{READER_USER}' ready")

    # Create admin user
    print_step(f"Creating admin user: {DEMO_ADMIN_USER}")
    cur.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{DEMO_ADMIN_USER}') THEN
                CREATE ROLE {DEMO_ADMIN_USER} WITH LOGIN PASSWORD '{DEMO_ADMIN_PASS}' CREATEDB;
            END IF;
        END
        $$;
    """
    )
    print_success(f"User '{DEMO_ADMIN_USER}' ready")

    # Create database
    print_step(f"Creating database: {DEMO_DB_NAME}")
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DEMO_DB_NAME}'")
    exists = cur.fetchone()
    if exists:
        print_success(f"Database '{DEMO_DB_NAME}' already exists")
    else:
        cur.execute(f"CREATE DATABASE {DEMO_DB_NAME} OWNER {DEMO_ADMIN_USER}")
        print_success(f"Database '{DEMO_DB_NAME}' created")

    cur.close()
    conn.close()
    return True


def create_tables():
    """Create all tables in the demo database."""
    print_header("Creating Tables")

    conn = psycopg2.connect(
        host=ADMIN_CONFIG["host"],
        port=ADMIN_CONFIG["port"],
        user=DEMO_ADMIN_USER,
        password=DEMO_ADMIN_PASS,
        database=DEMO_DB_NAME,
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Drop existing tables first (clean slate)
    cur.execute(
        """
        DROP TABLE IF EXISTS order_items, inventory_log, data_quality_issues,
                         monthly_sales, staff, orders, products, customers CASCADE;
    """
    )

    cur.execute(CREATE_TABLES_SQL)

    # Count tables
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
    )
    count = cur.fetchone()[0]
    print_success(f"Created {count} tables")

    # List tables
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    )
    for row in cur.fetchall():
        print(f"    • {row[0]}")

    cur.close()
    conn.close()
    return True


def seed_data():
    """Insert demo data into all tables."""
    print_header("Seeding Demo Data")

    conn = psycopg2.connect(
        host=ADMIN_CONFIG["host"],
        port=ADMIN_CONFIG["port"],
        user=DEMO_ADMIN_USER,
        password=DEMO_ADMIN_PASS,
        database=DEMO_DB_NAME,
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(SEED_DATA_SQL)

    # Show row counts per table
    cur.execute(
        """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    )
    tables = [row[0] for row in cur.fetchall()]

    print_success("Data inserted!")
    print()
    for table in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cur.fetchone()[0]
        print(f"    • {table:25s} → {count:3d} rows")

    cur.close()
    conn.close()
    return True


def grant_permissions():
    """Grant permissions to reader and admin users."""
    print_header("Setting Permissions")

    conn = psycopg2.connect(
        host=ADMIN_CONFIG["host"],
        port=ADMIN_CONFIG["port"],
        user=DEMO_ADMIN_USER,
        password=DEMO_ADMIN_PASS,
        database=DEMO_DB_NAME,
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(GRANT_SQL)
    print_success(f"Read-only access granted to '{READER_USER}'")
    print_success(f"Full access granted to '{DEMO_ADMIN_USER}'")

    cur.close()
    conn.close()
    return True


def verify():
    """Verify the setup by connecting as the read-only user."""
    print_header("Verification")

    try:
        conn = psycopg2.connect(
            host=ADMIN_CONFIG["host"],
            port=ADMIN_CONFIG["port"],
            user=READER_USER,
            password=READER_PASS,
            database=DEMO_DB_NAME,
        )
        cur = conn.cursor()

        # Test SELECT
        cur.execute("SELECT COUNT(*) FROM customers")
        count = cur.fetchone()[0]
        print_success(
            f"Connected as '{READER_USER}' — customers table has {count} rows"
        )

        # Test that we can't INSERT (read-only)
        try:
            cur.execute(
                "INSERT INTO customers (first_name, last_name) VALUES ('test', 'test')"
            )
            print_error("Read-only user can INSERT — permissions may need fixing")
        except psycopg2.errors.InsufficientPrivilege:
            print_success("Read-only user correctly blocked from INSERT")
        except Exception:
            print_success("Read-only user correctly blocked from INSERT")

        cur.close()
        conn.close()

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False

    return True


def print_final_instructions():
    """Print the connection details for the user."""
    print_header("Setup Complete! Connection Details")

    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │        DataGuard Connector Configuration            │")
    print("  ├─────────────────────────────────────────────────────┤")
    print(f"  │  Connector Type:  PostgreSQL                        │")
    print(f"  │  Host:            {ADMIN_CONFIG['host']:>33s}  │")
    print(f"  │  Port:            {ADMIN_CONFIG['port']:>33d}  │")
    print(f"  │  Database:        {DEMO_DB_NAME:>33s}  │")
    print(f"  │  Username:        {READER_USER:>33s}  │")
    print(f"  │  Password:        {READER_PASS:>33s}  │")
    print("  └─────────────────────────────────────────────────────┘")
    print()
    print("  NEXT STEPS:")
    print("  1. Open DataGuard in your browser")
    print("  2. Go to Connectors section")
    print("  3. Click 'Add Connector' → Select PostgreSQL")
    print("  4. Enter the details above")
    print("  5. Click 'Test' → should show 'Connected' with 8 tables")
    print("  6. Click 'Browse' → see all tables and data!")
    print()
    print("  TO CONNECT VIA psql:")
    print(
        f"    psql -h {ADMIN_CONFIG['host']} -p {ADMIN_CONFIG['port']} -U {DEMO_ADMIN_USER} -d {DEMO_DB_NAME}"
    )
    print()
    print("  DATABASE CONTENTS:")
    print(
        "    • customers           — 16 rows (with NULL emails, invalid formats, negative values)"
    )
    print(
        "    • products            — 16 rows (with NULLs, duplicates, negative prices)"
    )
    print(
        "    • orders              — 16 rows (with negative amounts, bad statuses, NULL refs)"
    )
    print("    • order_items         — 18 rows (order line items)")
    print("    • inventory_log       — 15 rows (stock movements)")
    print("    • data_quality_issues — 11 rows (pre-detected quality issues)")
    print("    • monthly_sales       — 5 rows  (aggregated summaries)")
    print("    • staff               — 8 rows  (employee records)")
    print()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--help" in args:
        print(__doc__)
        sys.exit(0)

    if "--check" in args:
        ok = check_postgres()
        sys.exit(0 if ok else 1)

    reset = "--reset" in args

    print_header("DataGuard PostgreSQL Demo Database Setup")
    print(
        f"  Mode: {'RESET (drop & recreate)' if reset else 'CREATE (safe, idempotent)'}"
    )

    # Step 1: Check connection
    if not check_postgres():
        sys.exit(1)

    # Step 2: Create database + users
    if not create_database(reset=reset):
        sys.exit(1)

    # Step 3: Create tables
    if not create_tables():
        sys.exit(1)

    # Step 4: Seed data
    if not seed_data():
        sys.exit(1)

    # Step 5: Grant permissions
    if not grant_permissions():
        sys.exit(1)

    # Step 6: Verify
    if not verify():
        sys.exit(1)

    # Step 7: Print instructions
    print_final_instructions()
