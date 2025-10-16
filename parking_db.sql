create database parking_db;

-- Slots
CREATE TABLE slots (
    slot_id SERIAL PRIMARY KEY,
    is_occupied BOOLEAN DEFAULT FALSE,
    vehicle_id INT
);

-- Vehicles
CREATE TABLE vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    vehicle_type VARCHAR(20),
    phone_number VARCHAR(15),
    parked_slot INT,
    entry_time TIMESTAMP
);
