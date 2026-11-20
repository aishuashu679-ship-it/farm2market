CREATE DATABASE IF NOT EXISTS farmer_market_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE farmer_market_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('farmer', 'buyer') NOT NULL DEFAULT 'farmer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS buyers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    business_name VARCHAR(150) NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    location VARCHAR(150) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_buyer_user FOREIGN KEY (user_id) REFERENCES users(id)
      ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS buyer_offers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id INT NOT NULL,
    crop_name VARCHAR(100) NOT NULL,
    price_per_kg DECIMAL(10,2) NOT NULL,
    distance_km DECIMAL(10,2) NOT NULL DEFAULT 0,
    notes VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_offer_buyer FOREIGN KEY (buyer_id) REFERENCES buyers(id)
      ON DELETE CASCADE
);

-- DEMO DATA ONLY: prices and distances below are fictional examples.
INSERT INTO buyers (business_name, contact_name, phone, location)
SELECT 'Green Basket Traders', 'Ravi', '9000000001', 'Local Market'
WHERE NOT EXISTS (SELECT 1 FROM buyers WHERE business_name='Green Basket Traders');

INSERT INTO buyers (business_name, contact_name, phone, location)
SELECT 'Fresh Farm Buyers', 'Meena', '9000000002', 'Town Wholesale Market'
WHERE NOT EXISTS (SELECT 1 FROM buyers WHERE business_name='Fresh Farm Buyers');

INSERT INTO buyers (business_name, contact_name, phone, location)
SELECT 'Harvest Direct', 'Arun', '9000000003', 'Regional Collection Centre'
WHERE NOT EXISTS (SELECT 1 FROM buyers WHERE business_name='Harvest Direct');

INSERT INTO buyer_offers (buyer_id, crop_name, price_per_kg, distance_km, notes)
SELECT b.id, 'Tomato', 24.00, 5.00, 'Demo offer; call to confirm'
FROM buyers b WHERE b.business_name='Green Basket Traders'
AND NOT EXISTS (SELECT 1 FROM buyer_offers o WHERE o.buyer_id=b.id AND o.crop_name='Tomato');

INSERT INTO buyer_offers (buyer_id, crop_name, price_per_kg, distance_km, notes)
SELECT b.id, 'Tomato', 27.00, 18.00, 'Demo offer; call to confirm'
FROM buyers b WHERE b.business_name='Fresh Farm Buyers'
AND NOT EXISTS (SELECT 1 FROM buyer_offers o WHERE o.buyer_id=b.id AND o.crop_name='Tomato');

INSERT INTO buyer_offers (buyer_id, crop_name, price_per_kg, distance_km, notes)
SELECT b.id, 'Tomato', 25.50, 9.00, 'Demo offer; call to confirm'
FROM buyers b WHERE b.business_name='Harvest Direct'
AND NOT EXISTS (SELECT 1 FROM buyer_offers o WHERE o.buyer_id=b.id AND o.crop_name='Tomato');

INSERT INTO buyer_offers (buyer_id, crop_name, price_per_kg, distance_km, notes)
SELECT b.id, 'Onion', 30.00, 8.00, 'Demo offer; call to confirm'
FROM buyers b WHERE b.business_name='Green Basket Traders'
AND NOT EXISTS (SELECT 1 FROM buyer_offers o WHERE o.buyer_id=b.id AND o.crop_name='Onion');

INSERT INTO buyer_offers (buyer_id, crop_name, price_per_kg, distance_km, notes)
SELECT b.id, 'Rice', 42.00, 12.00, 'Demo offer; call to confirm'
FROM buyers b WHERE b.business_name='Fresh Farm Buyers'
AND NOT EXISTS (SELECT 1 FROM buyer_offers o WHERE o.buyer_id=b.id AND o.crop_name='Rice');
