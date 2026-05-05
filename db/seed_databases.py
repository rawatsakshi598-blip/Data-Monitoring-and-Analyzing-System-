#!/usr/bin/env python3
"""Seed all sample databases with rich data for SQL Playground."""

import sqlite3, os, random, json
from datetime import datetime, timedelta

random.seed(42)
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

states = ['Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal']
languages = ['Hindi','Bengali','Telugu','Marathi','Tamil','Gujarati','Kannada','Malayalam','Odia','Punjabi','Assamese','Urdu']
city_types = ['Tier-2','Tier-3','Town','Small Town','Village']
indian_cities_list = ['Delhi','Mumbai','Bangalore','Hyderabad','Chennai','Kolkata','Pune','Ahmedabad','Jaipur','Lucknow','Surat','Nagpur','Indore','Bhopal','Chandigarh','Coimbatore','Kochi','Mysore','Noida','Gurgaon','Thane','Bhubaneswar','Varanasi','Agra','Dehradun','Mangalore','Visakhapatnam','Vijayawada','Trivandrum','Kanpur']


def seed_cities_db():
    db = sqlite3.connect(os.path.join(DB_DIR, 'cities.db'))
    c = db.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS cities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        state TEXT,
        country TEXT NOT NULL,
        population INTEGER,
        area_sq_km REAL,
        latitude REAL,
        longitude REAL,
        elevation_m INTEGER,
        timezone TEXT,
        is_capital INTEGER DEFAULT 0,
        language TEXT,
        literacy_rate REAL,
        avg_annual_rainfall_mm REAL,
        avg_temp_celsius REAL,
        established_year INTEGER,
        city_type TEXT,
        hd_index REAL,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS city_infrastructure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER,
        airports INTEGER DEFAULT 0,
        railway_stations INTEGER DEFAULT 0,
        metro_lines INTEGER DEFAULT 0,
        hospitals INTEGER DEFAULT 0,
        universities INTEGER DEFAULT 0,
        parks INTEGER DEFAULT 0,
        malls INTEGER DEFAULT 0,
        internet_penetration_pct REAL,
        green_cover_pct REAL,
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS city_economy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city_id INTEGER,
        gdp_billion_usd REAL,
        gdp_per_capita_usd REAL,
        main_industry TEXT,
        unemployment_rate REAL,
        it_companies INTEGER DEFAULT 0,
        startups INTEGER DEFAULT 0,
        fdi_inflow_million_usd REAL,
        cost_of_living_index REAL,
        FOREIGN KEY (city_id) REFERENCES cities(id)
    )''')

    # Major Indian cities
    indian_cities = [
        ('Delhi', 'Delhi', 'India', 16787949, 1484, 28.6139, 77.2090, 216, 'Asia/Kolkata', 1, 'Hindi', 88.7, 790, 25.0, 1911, 'Mega', 0.74),
        ('Mumbai', 'Maharashtra', 'India', 12442373, 603, 19.0760, 72.8777, 14, 'Asia/Kolkata', 0, 'Marathi', 89.7, 2422, 27.2, 1507, 'Mega', 0.78),
        ('Bangalore', 'Karnataka', 'India', 8443675, 709, 12.9716, 77.5946, 920, 'Asia/Kolkata', 0, 'Kannada', 88.5, 970, 24.1, 1537, 'Mega', 0.82),
        ('Hyderabad', 'Telangana', 'India', 6809970, 650, 17.3850, 78.4867, 505, 'Asia/Kolkata', 0, 'Telugu', 83.2, 810, 27.3, 1591, 'Mega', 0.76),
        ('Chennai', 'Tamil Nadu', 'India', 4681087, 426, 13.0827, 80.2707, 6, 'Asia/Kolkata', 0, 'Tamil', 90.2, 1400, 28.6, 1639, 'Mega', 0.75),
        ('Kolkata', 'West Bengal', 'India', 4496694, 185, 22.5726, 88.3639, 9, 'Asia/Kolkata', 0, 'Bengali', 87.1, 1750, 26.8, 1690, 'Mega', 0.69),
        ('Pune', 'Maharashtra', 'India', 3124458, 331, 18.5204, 73.8567, 560, 'Asia/Kolkata', 0, 'Marathi', 91.2, 730, 24.5, 1818, 'Metro', 0.80),
        ('Ahmedabad', 'Gujarat', 'India', 5577940, 464, 23.0225, 72.5714, 53, 'Asia/Kolkata', 0, 'Gujarati', 89.6, 750, 27.4, 1411, 'Mega', 0.72),
        ('Jaipur', 'Rajasthan', 'India', 3073350, 467, 26.9124, 75.7873, 431, 'Asia/Kolkata', 0, 'Hindi', 84.3, 560, 25.5, 1727, 'Metro', 0.71),
        ('Lucknow', 'Uttar Pradesh', 'India', 2817105, 349, 26.8467, 80.9462, 123, 'Asia/Kolkata', 0, 'Hindi', 79.3, 950, 25.9, 1775, 'Metro', 0.66),
        ('Surat', 'Gujarat', 'India', 4467797, 327, 21.1702, 72.8311, 13, 'Asia/Kolkata', 0, 'Gujarati', 88.6, 1100, 27.2, 1528, 'Metro', 0.73),
        ('Nagpur', 'Maharashtra', 'India', 2405665, 228, 21.1458, 79.0882, 311, 'Asia/Kolkata', 0, 'Marathi', 91.0, 1050, 26.7, 1702, 'Metro', 0.70),
        ('Indore', 'Madhya Pradesh', 'India', 1964086, 165, 22.7196, 75.8577, 553, 'Asia/Kolkata', 0, 'Hindi', 86.4, 950, 25.1, 1716, 'Metro', 0.68),
        ('Bhopal', 'Madhya Pradesh', 'India', 1795648, 285, 23.2599, 77.4126, 500, 'Asia/Kolkata', 0, 'Hindi', 83.5, 1120, 24.9, 1707, 'Metro', 0.67),
        ('Visakhapatnam', 'Andhra Pradesh', 'India', 2035922, 542, 17.6868, 83.2185, 5, 'Asia/Kolkata', 0, 'Telugu', 82.1, 950, 27.8, 1683, 'Metro', 0.69),
        ('Chandigarh', 'Chandigarh', 'India', 961587, 114, 30.7333, 76.7794, 321, 'Asia/Kolkata', 0, 'Hindi', 93.5, 1050, 23.5, 1948, 'Union Territory', 0.85),
        ('Coimbatore', 'Tamil Nadu', 'India', 1050721, 246, 11.0168, 76.9558, 411, 'Asia/Kolkata', 0, 'Tamil', 89.8, 650, 26.3, 1800, 'Metro', 0.74),
        ('Kochi', 'Kerala', 'India', 602046, 95, 9.9312, 76.2673, 0, 'Asia/Kolkata', 0, 'Malayalam', 97.4, 3000, 27.5, 1341, 'Metro', 0.79),
        ('Trivandrum', 'Kerala', 'India', 957470, 214, 8.5241, 76.9366, 10, 'Asia/Kolkata', 0, 'Malayalam', 96.8, 1800, 27.4, 1745, 'Metro', 0.78),
        ('Mysore', 'Karnataka', 'India', 920550, 155, 12.2958, 76.6394, 763, 'Asia/Kolkata', 0, 'Kannada', 87.5, 760, 24.2, 1399, 'Tier-2', 0.73),
        ('Varanasi', 'Uttar Pradesh', 'India', 1198491, 82, 25.3176, 83.0068, 81, 'Asia/Kolkata', 0, 'Hindi', 76.2, 1010, 25.3, -1000, 'Metro', 0.60),
        ('Agra', 'Uttar Pradesh', 'India', 1576831, 87, 27.1767, 78.0081, 170, 'Asia/Kolkata', 0, 'Hindi', 74.6, 690, 25.7, 1475, 'Metro', 0.62),
        ('New Delhi', 'Delhi', 'India', 109279, 35, 28.6139, 77.2090, 216, 'Asia/Kolkata', 1, 'Hindi', 90.1, 790, 25.0, 1931, 'Capital District', 0.86),
        ('Noida', 'Uttar Pradesh', 'India', 642381, 203, 28.5355, 77.3910, 194, 'Asia/Kolkata', 0, 'Hindi', 88.5, 720, 25.0, 1976, 'Metro', 0.78),
        ('Gurgaon', 'Haryana', 'India', 876824, 232, 28.4595, 77.0266, 220, 'Asia/Kolkata', 0, 'Hindi', 87.0, 590, 25.1, 1970, 'Metro', 0.77),
        ('Thane', 'Maharashtra', 'India', 1841814, 147, 19.2183, 72.9781, 7, 'Asia/Kolkata', 0, 'Marathi', 88.5, 2400, 27.1, 1853, 'Metro', 0.76),
        ('Bhubaneswar', 'Odisha', 'India', 881988, 186, 20.2961, 85.8245, 45, 'Asia/Kolkata', 0, 'Odia', 89.3, 1440, 27.0, 1948, 'Metro', 0.71),
        ('Vijayawada', 'Andhra Pradesh', 'India', 1034000, 61, 16.5062, 80.6480, 12, 'Asia/Kolkata', 0, 'Telugu', 80.1, 1030, 28.2, 1850, 'Metro', 0.65),
        ('Mangalore', 'Karnataka', 'India', 488968, 132, 12.9141, 74.8560, 22, 'Asia/Kolkata', 0, 'Kannada', 94.2, 3800, 27.1, 1850, 'Tier-2', 0.76),
        ('Dehradun', 'Uttarakhand', 'India', 578420, 200, 30.3165, 78.0322, 447, 'Asia/Kolkata', 0, 'Hindi', 89.7, 2070, 21.8, 1676, 'Tier-2', 0.72),
        ('Kanpur', 'Uttar Pradesh', 'India', 2765348, 403, 26.4499, 80.3319, 126, 'Asia/Kolkata', 0, 'Hindi', 79.6, 880, 25.4, 1803, 'Metro', 0.63),
    ]

    # Generate more Indian cities
    for i in range(3500):
        name = f'City_{i+1:04d}'
        state = random.choice(states)
        pop = random.randint(5000, 500000)
        area = round(random.uniform(5, 200), 1)
        lat = round(random.uniform(8.0, 35.0), 4)
        lon = round(random.uniform(68.0, 97.0), 4)
        elev = random.randint(0, 2500)
        lang = random.choice(languages)
        lit = round(random.uniform(55, 95), 1)
        rain = round(random.uniform(200, 3500), 0)
        temp = round(random.uniform(15, 35), 1)
        year = random.randint(1700, 2020)
        ctype = random.choice(city_types)
        hdi = round(random.uniform(0.4, 0.8), 2)
        if i % 200 == 0:
            name = f'Delhi Extension {i//200}'
            state = 'Delhi'
            pop = random.randint(50000, 200000)
        indian_cities.append((name, state, 'India', pop, area, lat, lon, elev, 'Asia/Kolkata', 0, lang, lit, rain, temp, year, ctype, hdi))

    c.executemany('INSERT INTO cities (name, state, country, population, area_sq_km, latitude, longitude, elevation_m, timezone, is_capital, language, literacy_rate, avg_annual_rainfall_mm, avg_temp_celsius, established_year, city_type, hd_index) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', indian_cities)

    # Infrastructure
    for i in range(1, 32):
        c.execute('INSERT INTO city_infrastructure (city_id, airports, railway_stations, metro_lines, hospitals, universities, parks, malls, internet_penetration_pct, green_cover_pct) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (i, random.randint(1,3), random.randint(2,10), random.randint(0,7), random.randint(50,500), random.randint(5,50), random.randint(20,200), random.randint(5,50), round(random.uniform(50,95),1), round(random.uniform(5,30),1)))

    # Economy
    economies = [
        (1, 370, 22036, 'Government/Services', 7.2, 500, 7000, 2500, 65),
        (2, 368, 29555, 'Finance/Bollywood', 6.8, 300, 8000, 3200, 72),
        (3, 110, 26000, 'IT/Biotechnology', 4.5, 1500, 12000, 4500, 58),
        (4, 75, 22000, 'IT/Pharmaceuticals', 5.8, 800, 7000, 2800, 52),
        (5, 78, 16680, 'Automotive/IT', 5.2, 600, 5000, 2200, 55),
        (6, 150, 33300, 'Manufacturing/IT', 8.1, 200, 3000, 1500, 60),
        (7, 68, 21750, 'IT/Education', 4.8, 900, 8000, 3000, 55),
        (8, 80, 14340, 'Textiles/Diamonds', 6.5, 100, 4000, 1800, 48),
        (9, 42, 13670, 'Tourism/Gems', 7.0, 50, 2000, 1200, 50),
        (10, 28, 9940, 'Government/IT', 8.5, 80, 3000, 800, 45),
    ]
    for e in economies:
        c.execute('INSERT INTO city_economy (city_id, gdp_billion_usd, gdp_per_capita_usd, main_industry, unemployment_rate, it_companies, startups, fdi_inflow_million_usd, cost_of_living_index) VALUES (?,?,?,?,?,?,?,?,?)', e)

    # World cities
    world_cities = [
        ('New York', 'New York', 'USA', 8336817, 783, 40.7128, -74.0060, 10, 'America/New_York', 0, 'English', 89.0, 1268, 12.9, 1624, 'Mega', 0.94),
        ('London', 'England', 'UK', 8982000, 1572, 51.5074, -0.1278, 11, 'Europe/London', 0, 'English', 99.0, 602, 11.3, 43, 'Mega', 0.93),
        ('Tokyo', 'Tokyo', 'Japan', 13960000, 2194, 35.6762, 139.6503, 40, 'Asia/Tokyo', 0, 'Japanese', 99.0, 1530, 15.4, 1457, 'Mega', 0.95),
        ('Paris', 'Ile-de-France', 'France', 2161000, 105, 48.8566, 2.3522, 35, 'Europe/Paris', 0, 'French', 99.0, 637, 12.3, -250, 'Mega', 0.92),
        ('Beijing', 'Beijing', 'China', 21540000, 16411, 39.9042, 116.4074, 43, 'Asia/Shanghai', 1, 'Mandarin', 97.0, 570, 12.9, -1045, 'Mega', 0.90),
        ('Sydney', 'New South Wales', 'Australia', 5312000, 12368, -33.8688, 151.2093, 3, 'Australia/Sydney', 0, 'English', 99.0, 1213, 18.4, 1788, 'Mega', 0.94),
        ('Dubai', 'Dubai', 'UAE', 3331000, 4114, 25.2048, 55.2708, 5, 'Asia/Dubai', 0, 'Arabic', 95.0, 94, 27.2, 1833, 'Mega', 0.86),
        ('Singapore', '', 'Singapore', 5686000, 733, 1.3521, 103.8198, 15, 'Asia/Singapore', 1, 'English', 97.5, 2340, 27.0, 1819, 'City-State', 0.94),
        ('Toronto', 'Ontario', 'Canada', 2930000, 630, 43.6532, -79.3832, 76, 'America/Toronto', 0, 'English', 99.0, 831, 9.4, 1793, 'Mega', 0.92),
        ('Berlin', 'Berlin', 'Germany', 3645000, 892, 52.5200, 13.4050, 34, 'Europe/Berlin', 0, 'German', 99.0, 570, 10.3, 1237, 'Mega', 0.93),
    ]
    c.executemany('INSERT INTO cities (name, state, country, population, area_sq_km, latitude, longitude, elevation_m, timezone, is_capital, language, literacy_rate, avg_annual_rainfall_mm, avg_temp_celsius, established_year, city_type, hd_index) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', world_cities)

    db.commit()
    count = c.execute('SELECT COUNT(*) FROM cities').fetchone()[0]
    print(f'cities.db: {count} cities inserted')
    db.close()


def seed_sales_db():
    db = sqlite3.connect(os.path.join(DB_DIR, 'sales.db'))
    s = db.cursor()

    s.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        city TEXT,
        state TEXT,
        country TEXT DEFAULT 'India',
        segment TEXT,
        created_at TEXT
    )''')

    s.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        sub_category TEXT,
        price REAL,
        cost REAL,
        weight_kg REAL,
        brand TEXT,
        rating REAL DEFAULT 4.0,
        stock INTEGER DEFAULT 100
    )''')

    s.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        discount REAL DEFAULT 0,
        total_amount REAL,
        order_date TEXT,
        ship_date TEXT,
        ship_mode TEXT,
        status TEXT DEFAULT 'Delivered',
        city TEXT,
        state TEXT,
        payment_method TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    s.execute('''CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        product_id INTEGER,
        reason TEXT,
        amount REAL,
        return_date TEXT,
        status TEXT DEFAULT 'Processed'
    )''')

    segments = ['Consumer', 'Corporate', 'Home Office']
    indian_names = ['Amit Sharma','Priya Patel','Rahul Gupta','Sneha Singh','Vikram Kumar','Anjali Verma','Rajesh Iyer','Deepika Reddy','Arjun Nair','Kavita Joshi','Suresh Menon','Lakshmi Das','Manish Agarwal','Ritu Saxena','Nitin Chopra','Pooja Bhatt','Sanjay Mishra','Neha Rao','Ashok Pillai','Meera Choudhury','Kiran Desai','Swati Pandey','Ravi Shastri','Jyoti Mehta','Gaurav Malhotra','Divya Kapoor','Anand Bhat','Shalini Mukherjee','Pradeep Jain','Sunita Chauhan']

    for i in range(500):
        dt = datetime(2023,1,1) + timedelta(days=random.randint(0,730))
        s.execute('INSERT INTO customers (name, email, phone, city, state, country, segment, created_at) VALUES (?,?,?,?,?,?,?,?)',
            (random.choice(indian_names), f'customer{i+1}@email.com', f'+91-{random.randint(7000000000,9999999999)}', random.choice(indian_cities_list), random.choice(states), 'India', random.choice(segments), dt.isoformat()))

    categories = {
        'Electronics': ['Smartphone','Laptop','Tablet','Headphones','Smart Watch','Camera','Speaker','Monitor','Keyboard','Mouse'],
        'Clothing': ['T-Shirt','Jeans','Jacket','Saree','Kurta','Sneakers','Sandals','Hoodie','Dress','Cap'],
        'Home': ['Bed Sheet','Curtain','Lamp','Pillow','Rug','Vase','Cushion','Candle','Mirror','Clock'],
        'Food': ['Rice Bag','Spice Set','Tea Pack','Coffee Beans','Honey Jar','Olive Oil','Pasta','Chocolate','Nuts Mix','Jam'],
        'Books': ['Fiction Novel','Textbook','Comic','Biography','Self-Help','Cookbook','Sci-Fi','Thriller','History','Poetry'],
    }
    brands = ['Tata','Reliance','Amul','Dabur','Himalaya','Bata','Raymond','Prestige','Philips','Samsung','LG','Mi','Boat','Noise','HP','Dell','Lenovo','Canon','Sony','Nike']
    for cat, items in categories.items():
        for item in items:
            price = round(random.uniform(100, 50000), 2)
            cost = round(price * random.uniform(0.3, 0.7), 2)
            s.execute('INSERT INTO products (name, category, sub_category, price, cost, weight_kg, brand, rating, stock) VALUES (?,?,?,?,?,?,?,?,?)',
                (item, cat, cat, price, cost, round(random.uniform(0.1, 5), 2), random.choice(brands), round(random.uniform(3.5, 5.0), 1), random.randint(0, 500)))

    ship_modes = ['Standard', 'Express', 'Same Day', 'Economy']
    statuses = ['Delivered', 'Shipped', 'Processing', 'Cancelled', 'Returned']
    payments = ['UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'Cash on Delivery', 'EMI']

    for i in range(5000):
        cust_id = random.randint(1, 500)
        prod_id = random.randint(1, 50)
        qty = random.randint(1, 5)
        price_row = s.execute('SELECT price FROM products WHERE id=?', (prod_id,)).fetchone()[0]
        discount = round(random.choice([0, 0, 0, 5, 10, 15, 20, 25]), 1)
        total = round(price_row * qty * (1 - discount/100), 2)
        order_date = datetime(2023,1,1) + timedelta(days=random.randint(0,730))
        ship_date = order_date + timedelta(days=random.randint(1,10))
        city = random.choice(indian_cities_list)
        state_idx = indian_cities_list.index(city) % len(states)
        s.execute('INSERT INTO orders (order_id, customer_id, product_id, quantity, unit_price, discount, total_amount, order_date, ship_date, ship_mode, status, city, state, payment_method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (f'ORD-{i+1:06d}', cust_id, prod_id, qty, price_row, discount, total, order_date.isoformat(), ship_date.isoformat(), random.choice(ship_modes), random.choice(statuses), city, states[state_idx], random.choice(payments)))

    for i in range(200):
        order_row = s.execute('SELECT order_id, product_id, total_amount FROM orders WHERE status IN ("Cancelled","Returned") ORDER BY RANDOM() LIMIT 1').fetchone()
        if order_row:
            s.execute('INSERT INTO returns (order_id, product_id, reason, amount, return_date, status) VALUES (?,?,?,?,?,?)',
                (order_row[0], order_row[1], random.choice(['Defective','Wrong Item','Not As Described','Changed Mind','Late Delivery']), order_row[2], (datetime(2023,6,1) + timedelta(days=random.randint(0,365))).isoformat(), random.choice(['Processed','Pending','Rejected'])))

    db.commit()
    cust_count = s.execute('SELECT COUNT(*) FROM customers').fetchone()[0]
    prod_count = s.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    order_count = s.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    ret_count = s.execute('SELECT COUNT(*) FROM returns').fetchone()[0]
    print(f'sales.db: {cust_count} customers, {prod_count} products, {order_count} orders, {ret_count} returns')
    db.close()


def seed_hr_db():
    db = sqlite3.connect(os.path.join(DB_DIR, 'hr.db'))
    h = db.cursor()

    h.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT,
        department TEXT,
        designation TEXT,
        salary REAL,
        city TEXT,
        state TEXT,
        join_date TEXT,
        birth_date TEXT,
        gender TEXT,
        status TEXT DEFAULT 'Active',
        manager_id TEXT,
        performance_rating REAL
    )''')

    h.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        head_count INTEGER DEFAULT 0,
        budget_million REAL,
        location TEXT
    )''')

    h.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        date TEXT,
        check_in TEXT,
        check_out TEXT,
        status TEXT DEFAULT 'Present',
        hours_worked REAL,
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    )''')

    h.execute('''CREATE TABLE IF NOT EXISTS payroll (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        month TEXT,
        base_salary REAL,
        bonus REAL DEFAULT 0,
        tax_deduction REAL DEFAULT 0,
        pf_deduction REAL DEFAULT 0,
        net_pay REAL,
        payment_date TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
    )''')

    depts = ['Engineering','Marketing','Sales','HR','Finance','Operations','Legal','Design','QA','Support','Product','Data Science','DevOps','Security','Research']
    designations_by_dept = {
        'Engineering': ['Software Engineer','Senior Engineer','Tech Lead','Principal Engineer','Architect','VP Engineering'],
        'Marketing': ['Marketing Associate','Marketing Manager','Brand Manager','CMO','Content Strategist','SEO Specialist'],
        'Sales': ['Sales Rep','Sales Manager','Regional Head','VP Sales','Account Executive','Business Dev'],
        'HR': ['HR Associate','HR Manager','HR Director','CHRO','Recruiter','Compensation Analyst'],
        'Finance': ['Accountant','Finance Manager','CFO','Auditor','Tax Specialist','Financial Analyst'],
        'Operations': ['Ops Associate','Ops Manager','VP Operations','Supply Chain Lead','Logistics Coordinator'],
        'Legal': ['Legal Associate','Legal Counsel','General Counsel','Compliance Officer','Paralegal'],
        'Design': ['Designer','Senior Designer','Design Lead','Art Director','UX Researcher','Product Designer'],
        'QA': ['QA Engineer','Senior QA','QA Lead','Test Manager','Automation Engineer','SDET'],
        'Support': ['Support Agent','Senior Support','Support Manager','VP Support','Technical Writer'],
        'Product': ['Product Analyst','Product Manager','Senior PM','VP Product','Product Owner'],
        'Data Science': ['Data Analyst','Data Scientist','Senior Data Scientist','ML Engineer','AI Lead','Chief Data Officer'],
        'DevOps': ['DevOps Engineer','Senior DevOps','SRE','Cloud Architect','Platform Engineer'],
        'Security': ['Security Analyst','Security Engineer','CISO','Penetration Tester','SOC Analyst'],
        'Research': ['Research Associate','Research Scientist','Principal Researcher','VP Research','PhD Fellow'],
    }
    first_names_m = ['Amit','Rahul','Vikram','Rajesh','Arjun','Manish','Nitin','Sanjay','Ashok','Kiran','Ravi','Gaurav','Anand','Pradeep','Suresh','Deepak','Ajay','Rohit','Sumit','Tarun']
    first_names_f = ['Priya','Sneha','Anjali','Deepika','Kavita','Lakshmi','Ritu','Pooja','Neha','Swati','Divya','Shalini','Meera','Jyoti','Sunita','Aarti','Rekha','Nisha','Pallavi','Rashmi']
    last_names = ['Sharma','Patel','Gupta','Singh','Kumar','Verma','Iyer','Reddy','Nair','Joshi','Menon','Das','Agarwal','Saxena','Chopra','Bhatt','Mishra','Rao','Pillai','Choudhury','Desai','Pandey','Shastri','Mehta','Malhotra','Kapoor','Bhat','Mukherjee','Jain','Chauhan']

    for dept in depts:
        budget = round(random.uniform(5, 100), 1)
        h.execute('INSERT INTO departments (name, budget_million, location) VALUES (?,?,?)',
            (dept, budget, random.choice(['Delhi HQ','Mumbai Office','Bangalore Campus','Hyderabad Center','Chennai Branch','Pune Office'])))

    for i in range(1000):
        emp_id = f'EMP{i+1:05d}'
        gender = random.choice(['M','F'])
        fn = random.choice(first_names_m if gender == 'M' else first_names_f)
        ln = random.choice(last_names)
        name = f'{fn} {ln}'
        dept = random.choice(depts)
        desig = random.choice(designations_by_dept[dept])
        salary = round(random.uniform(300000, 5000000), 0)
        city = random.choice(indian_cities_list)
        join = datetime(2015,1,1) + timedelta(days=random.randint(0,3000))
        birth = datetime(1975,1,1) + timedelta(days=random.randint(0,15000))
        rating = round(random.uniform(2.0, 5.0), 1)
        h.execute('INSERT INTO employees (emp_id, name, email, department, designation, salary, city, state, join_date, birth_date, gender, status, performance_rating) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (emp_id, name, f'{fn.lower()}.{ln.lower()}@company.com', dept, desig, salary, city, states[indian_cities_list.index(city) % len(states)], join.isoformat(), birth.isoformat(), gender, random.choice(['Active','Active','Active','Active','On Leave','Terminated']), rating))

    # Attendance (last 90 days for 200 active employees)
    active_emps = h.execute('SELECT emp_id FROM employees WHERE status="Active" LIMIT 200').fetchall()
    for emp in active_emps:
        for day_offset in range(90):
            d = datetime(2024,10,1) + timedelta(days=day_offset)
            if d.weekday() < 5:
                status = random.choice(['Present','Present','Present','Present','Present','Absent','Half Day','Work From Home'])
                check_in = f'09:{random.randint(0,59):02d}' if status != 'Absent' else None
                check_out = f'18:{random.randint(0,59):02d}' if status != 'Absent' else None
                hours = round(random.uniform(7, 10), 1) if status == 'Present' else (round(random.uniform(3,5),1) if status == 'Half Day' else 0)
                h.execute('INSERT INTO attendance (emp_id, date, check_in, check_out, status, hours_worked) VALUES (?,?,?,?,?,?)',
                    (emp[0], d.isoformat(), check_in, check_out, status, hours))

    # Payroll
    for emp in active_emps:
        salary = h.execute('SELECT salary FROM employees WHERE emp_id=?', (emp[0],)).fetchone()[0]
        for m in range(12):
            month = datetime(2024,1,1) + timedelta(days=m*30)
            month_str = month.strftime('%Y-%m')
            bonus = round(random.choice([0, 0, 0, 0, salary*0.1, salary*0.2]), 0)
            tax = round(salary * 0.2, 0)
            pf = round(salary * 0.12, 0)
            net = round(salary + bonus - tax - pf, 0)
            h.execute('INSERT INTO payroll (emp_id, month, base_salary, bonus, tax_deduction, pf_deduction, net_pay, payment_date) VALUES (?,?,?,?,?,?,?,?)',
                (emp[0], month_str, salary, bonus, tax, pf, net, (month + timedelta(days=28)).isoformat()))

    db.commit()
    emp_count = h.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
    dept_count = h.execute('SELECT COUNT(*) FROM departments').fetchone()[0]
    att_count = h.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]
    pay_count = h.execute('SELECT COUNT(*) FROM payroll').fetchone()[0]
    print(f'hr.db: {emp_count} employees, {dept_count} departments, {att_count} attendance, {pay_count} payroll records')
    db.close()


def seed_main_db():
    db = sqlite3.connect(os.path.join(DB_DIR, 'custom.db'))
    m = db.cursor()

    # Insert services
    services_data = [
        ('PostgreSQL Production', 'Main production database', 'database', 'postgresql', 'postgresql://prod:5432/main', 'active', 'Data Team'),
        ('MySQL Analytics', 'Analytics data warehouse', 'database', 'mysql', 'mysql://analytics:3306/dw', 'active', 'Analytics Team'),
        ('Kafka Streams', 'Real-time event streaming', 'messaging', 'kafka', 'kafka://streams:9092', 'active', 'Platform Team'),
        ('S3 Data Lake', 'Raw data storage', 'storage', 's3', 's3://data-lake/raw', 'active', 'Data Engineering'),
        ('MongoDB Logs', 'Application logs store', 'database', 'mongodb', 'mongodb://logs:27017', 'warning', 'DevOps Team'),
    ]
    svc_ids = []
    for svc in services_data:
        sid = f'svc_{random.randint(10000,99999)}'
        svc_ids.append(sid)
        m.execute('INSERT OR IGNORE INTO Service (id, name, description, serviceType, platform, connectionUrl, status, owner, createdAt, updatedAt) VALUES (?,?,?,?,?,?,?,?,datetime("now"),datetime("now"))',
            (sid, *svc))

    # Insert tables
    tables_data = [
        ('users', 'prod_db.public.users', 'User accounts table', 'prod_db', 'public', 8, 2450000, 97.2),
        ('orders', 'prod_db.public.orders', 'Customer orders', 'prod_db', 'public', 12, 8900000, 94.8),
        ('products', 'prod_db.public.products', 'Product catalog', 'prod_db', 'public', 15, 34500, 99.1),
        ('transactions', 'prod_db.public.transactions', 'Payment transactions', 'prod_db', 'public', 10, 15340000, 91.5),
        ('analytics_events', 'dw.events.raw', 'Raw analytics events', 'dw', 'events', 22, 45000000, 88.3),
        ('customer_segments', 'dw.analytics.segments', 'Customer segmentation data', 'dw', 'analytics', 8, 890000, 96.1),
        ('inventory', 'prod_db.public.inventory', 'Inventory tracking', 'prod_db', 'public', 6, 567000, 93.7),
        ('logs_api', 'logs.api.requests', 'API request logs', 'logs', 'api', 5, 120000000, 78.2),
    ]
    for tbl in tables_data:
        tid = f'tbl_{random.randint(10000,99999)}'
        m.execute('''INSERT OR IGNORE INTO "Table" (id, name, fullyQualifiedName, description, database, schema, serviceId, columnCount, rowCount, qualityScore, freshnessStatus, tier, tags, owners, createdAt, updatedAt)
            VALUES (?,?,?,?,?,?,?,?,?,?,'fresh','T1','[]','[]',datetime('now'),datetime('now'))''',
            (tid, tbl[0], tbl[1], tbl[2], tbl[3], tbl[4], svc_ids[0], tbl[5], tbl[6], tbl[7]))

    # Insert quality rules
    rules = [
        ('Null Check - Users', 'Check for null values in critical columns', 'not_null', 'completeness', 'error'),
        ('Uniqueness - Order IDs', 'Ensure order IDs are unique', 'unique', 'uniqueness', 'error'),
        ('Range Check - Prices', 'Validate product prices are within range', 'range', 'validity', 'warning'),
        ('Freshness - Transactions', 'Check data freshness for transactions', 'freshness', 'timeliness', 'error'),
        ('Completeness - Events', 'Ensure all required fields are populated', 'not_null', 'completeness', 'warning'),
    ]
    for r in rules:
        rid = f'rule_{random.randint(10000,99999)}'
        m.execute('INSERT OR IGNORE INTO QualityRule (id, name, description, type, dimension, severity, config, enabled, schedule, createdAt, updatedAt) VALUES (?,?,?,?,?,?,?,1,"manual",datetime("now"),datetime("now"))',
            (rid, r[0], r[1], r[2], r[3], r[4], '{}'))

    # Insert teams
    for team_name in ['Data Engineering', 'Analytics', 'Platform', 'Data Science', 'DevOps']:
        m.execute('INSERT OR IGNORE INTO Team (id, name, displayName, description, email, createdAt, updatedAt) VALUES (?,?,?,?,?,datetime("now"),datetime("now"))',
            (f'team_{random.randint(10000,99999)}', team_name.lower().replace(' ','_'), team_name, f'{team_name} team', f'{team_name.lower().replace(" ",".")}@company.com'))

    # Insert alerts
    alert_types = ['quality_degradation', 'freshness_breach', 'anomaly_detected', 'schema_change']
    for i in range(8):
        m.execute('INSERT OR IGNORE INTO Alert (id, title, message, severity, alertType, source, status, createdAt) VALUES (?,?,?,?,?,?,?,datetime("now"))',
            (f'alert_{random.randint(10000,99999)}', f'Alert {i+1}', f'Description for alert {i+1}', random.choice(['error','warning','info']), random.choice(alert_types), random.choice(['users','orders','products']), random.choice(['active','resolved'])))

    db.commit()
    svc_count = m.execute('SELECT COUNT(*) FROM Service').fetchone()[0]
    tbl_count = m.execute('SELECT COUNT(*) FROM "Table"').fetchone()[0]
    rule_count = m.execute('SELECT COUNT(*) FROM QualityRule').fetchone()[0]
    team_count = m.execute('SELECT COUNT(*) FROM Team').fetchone()[0]
    alert_count = m.execute('SELECT COUNT(*) FROM Alert').fetchone()[0]
    print(f'custom.db: {svc_count} services, {tbl_count} tables, {rule_count} rules, {team_count} teams, {alert_count} alerts')
    db.close()


if __name__ == '__main__':
    seed_cities_db()
    seed_sales_db()
    seed_hr_db()
    seed_main_db()
    print('\nAll databases seeded successfully!')
