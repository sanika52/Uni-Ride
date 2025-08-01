-- Create the database
CREATE DATABASE IF NOT EXISTS ride_sharing;
USE ride_sharing;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) NOT NULL UNIQUE,
    college_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) 

-- Create rides table
CREATE TABLE IF NOT EXISTS rides (
    ride_id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    source_location VARCHAR(100) NOT NULL,
    destination_location VARCHAR(100) NOT NULL,
    ride_date DATE NOT NULL,
    ride_time TIME NOT NULL,
    seats_offered INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
    FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id) ON DELETE CASCADE
) 

-- Create vehicle table
CREATE TABLE IF NOT EXISTS vehicle (
    vehicle_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    vehicle_no VARCHAR(20) NOT NULL UNIQUE,
    vehicle_model VARCHAR(50) NOT NULL,
    seats_available INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) 

-- Create Ride_Participation table
CREATE TABLE IF NOT EXISTS Ride_Participation (
    participation_id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    student_id INT NOT NULL,
    role ENUM('driver', 'passenger') NOT NULL,
    status ENUM('confirmed', 'cancelled', 'completed', 'no-show') NOT NULL DEFAULT 'confirmed',
    FOREIGN KEY (ride_id) REFERENCES rides(ride_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
) 

-- Create Ride_Request table
CREATE TABLE IF NOT EXISTS Ride_Request (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id INT NOT NULL,
    rider_source VARCHAR(100) NOT NULL,
    rider_destination VARCHAR(100) NOT NULL,
    preferred_date DATE NOT NULL,
    preferred_time TIME NOT NULL,
    status ENUM('matched', 'pending', 'rejected', 'cancelled') NOT NULL DEFAULT 'pending',
    matched_ride_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    driver_accepted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (passenger_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_ride_id) REFERENCES rides(ride_id) ON DELETE SET NULL
) 

-- ===============================================
-- Ride Sharing App: SQL Queries with Placeholders
-- ===============================================

-- -----------------------------------------------
-- 1. Search rides by source, destination, and date
-- -----------------------------------------------
SELECT r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
       r.seats_offered, u.roll_number AS driver_roll, u.college_name AS driver_college,
       v.vehicle_model, v.vehicle_no
FROM rides r
JOIN users u ON r.driver_id = u.id
JOIN vehicle v ON r.vehicle_id = v.vehicle_id
WHERE r.source_location LIKE '%[search_source]%'
AND r.destination_location LIKE '%[search_destination]%'
AND r.ride_date = '[search_date]'
AND r.seats_offered > 0
AND r.status = 'active'
ORDER BY r.ride_time;

-- -----------------------------------------------
-- 2. Create a new ride request
-- -----------------------------------------------
INSERT INTO Ride_Request (
    passenger_id, rider_source, rider_destination,
    preferred_date, preferred_time, status
) VALUES (
    [passenger_id], '[source]', '[destination]',
    '[date]', '[time]', 'pending'
);

-- -----------------------------------------------
-- 3. Get detailed information about a specific ride
-- -----------------------------------------------
SELECT r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
       r.seats_offered, u.roll_number AS driver_roll, u.college_name AS driver_college,
       u.email AS driver_email, v.vehicle_model, v.vehicle_no, v.seats_available,
       COUNT(rp.participation_id) AS current_passengers
FROM rides r
JOIN users u ON r.driver_id = u.id
JOIN vehicle v ON r.vehicle_id = v.vehicle_id
LEFT JOIN Ride_Participation rp ON r.ride_id = rp.ride_id AND rp.role = 'passenger'
WHERE r.ride_id = [ride_id]
GROUP BY r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
         r.seats_offered, u.roll_number, u.college_name, u.email, v.vehicle_model,
         v.vehicle_no, v.seats_available;

-- -----------------------------------------------
-- 4. Get all rides a user has participated in
-- -----------------------------------------------
SELECT r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
       rp.role, rp.status AS participation_status
FROM Ride_Participation rp
JOIN rides r ON rp.ride_id = r.ride_id
WHERE rp.student_id = [user_id]
ORDER BY r.ride_date DESC, r.ride_time DESC;

-- -----------------------------------------------
-- 5. Get all pending ride requests for a driver
-- -----------------------------------------------
SELECT rr.request_id, rr.rider_source, rr.rider_destination, rr.preferred_date, rr.preferred_time,
       u.roll_number AS passenger_roll, u.college_name AS passenger_college
FROM Ride_Request rr
JOIN users u ON rr.passenger_id = u.id
WHERE rr.matched_ride_id = [ride_id]
AND rr.status = 'pending';

-- -----------------------------------------------
-- 6. Cancel a ride request
-- -----------------------------------------------
UPDATE Ride_Request
SET status = 'cancelled'
WHERE request_id = [request_id]
AND passenger_id = [user_id];

-- -----------------------------------------------
-- 7. Mark a ride as completed
-- -----------------------------------------------
UPDATE rides
SET status = 'completed'
WHERE ride_id = [ride_id]
AND driver_id = [driver_id];

-- -----------------------------------------------
-- 8. Update all participations for the ride
-- -----------------------------------------------
UPDATE Ride_Participation
SET status = 'completed'
WHERE ride_id = [ride_id]
AND status = 'confirmed';

-- -----------------------------------------------
-- 9. Check available seats for a ride
-- -----------------------------------------------
SELECT r.ride_id, r.seats_offered,
       COUNT(rp.participation_id) AS current_passengers,
       (r.seats_offered - COUNT(rp.participation_id)) AS available_seats
FROM rides r
LEFT JOIN Ride_Participation rp ON r.ride_id = rp.ride_id AND rp.role = 'passenger'
WHERE r.ride_id = [ride_id]
GROUP BY r.ride_id;

-- -----------------------------------------------
-- 10. Find rides that match a passenger's request
-- -----------------------------------------------
SELECT r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
       r.seats_offered, u.roll_number AS driver_roll, u.college_name AS driver_college,
       v.vehicle_model, v.vehicle_no
FROM rides r
JOIN users u ON r.driver_id = u.id
JOIN vehicle v ON r.vehicle_id = v.vehicle_id
WHERE r.source_location LIKE '%[request_source]%'
AND r.destination_location LIKE '%[request_destination]%'
AND r.ride_date = '[request_date]'
AND r.ride_time BETWEEN '[request_time_min]' AND '[request_time_max]'
AND r.seats_offered > 0
AND r.status = 'active'
ORDER BY r.ride_time;

-- -----------------------------------------------
-- 11. Get all active rides for a driver
-- -----------------------------------------------
SELECT r.ride_id, r.source_location, r.destination_location, r.ride_date, r.ride_time,
       r.seats_offered, COUNT(rp.participation_id) AS current_passengers
FROM rides r
LEFT JOIN Ride_Participation rp ON r.ride_id = rp.ride_id AND rp.role = 'passenger'
WHERE r.driver_id = [driver_id]
AND r.status = 'active'
GROUP BY r.ride_id
ORDER BY r.ride_date, r.ride_time;

-- Add indexes for better performance
CREATE INDEX idx_rides_source_dest ON rides(source_location, destination_location);
CREATE INDEX idx_rides_date ON rides(ride_date);
CREATE INDEX idx_ride_request_status ON Ride_Request(status);







