-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: database
-- Generation Time: Dec 02, 2025 at 07:08 PM
-- Server version: 8.0.44
-- PHP Version: 8.3.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+07:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `sdn_controller`
--

-- --------------------------------------------------------

--
-- Table structure for table `access_points`
--

CREATE TABLE `access_points` (
  `id` int NOT NULL,
  `device_id` varchar(20) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `identity` varchar(100) DEFAULT NULL,
  `os_version` varchar(100) DEFAULT NULL,
  `board` varchar(100) DEFAULT NULL,
  `serial_number` varchar(100) DEFAULT NULL,
  `vendor` varchar(100) DEFAULT NULL,
  `main_ip_address` varchar(50) DEFAULT NULL,
  `main_mac_address` varchar(50) DEFAULT NULL,
  `main_interface` varchar(50) DEFAULT NULL,
  `southbound` varchar(50) DEFAULT NULL,
  `status` enum('active','disconnected') DEFAULT 'disconnected',
  `last_seen` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `network_devices`
--

CREATE TABLE `network_devices` (
  `id` int NOT NULL,
  `device_id` varchar(20) NOT NULL,
  `device_type` enum('router','switch','access_point','server') NOT NULL,
  `southbound` varchar(50) NOT NULL DEFAULT 'routeros_api',
  `status` enum('active','disconnected') DEFAULT 'disconnected',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_seen` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `routers`
--

CREATE TABLE `routers` (
  `id` int NOT NULL,
  `device_id` varchar(20) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `identity` varchar(100) DEFAULT NULL,
  `os_version` varchar(100) DEFAULT NULL,
  `board` varchar(100) DEFAULT NULL,
  `serial_number` varchar(100) DEFAULT NULL,
  `vendor` varchar(100) DEFAULT NULL,
  `main_ip_address` varchar(50) DEFAULT NULL,
  `main_mac_address` varchar(50) DEFAULT NULL,
  `main_interface` varchar(50) DEFAULT NULL,
  `southbound` varchar(50) DEFAULT 'routeros_api',
  `status` enum('active','disconnected') DEFAULT 'disconnected',
  `last_seen` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `switchs`
--

CREATE TABLE `switchs` (
  `id` int NOT NULL,
  `device_id` varchar(20) NOT NULL,
  `username` varchar(100) DEFAULT NULL,
  `password` varchar(100) DEFAULT NULL,
  `identity` varchar(100) DEFAULT NULL,
  `os_version` varchar(100) DEFAULT NULL,
  `board` varchar(100) DEFAULT NULL,
  `serial_number` varchar(100) DEFAULT NULL,
  `vendor` varchar(100) DEFAULT NULL,
  `main_ip_address` varchar(50) DEFAULT NULL,
  `main_mac_address` varchar(50) DEFAULT NULL,
  `main_interface` varchar(50) DEFAULT NULL,
  `southbound` varchar(50) DEFAULT 'routeros_api',
  `status` enum('active','disconnected') DEFAULT 'disconnected',
  `last_seen` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `access_points`
--
ALTER TABLE `access_points`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_ap_device_id` (`device_id`);

--
-- Indexes for table `network_devices`
--
ALTER TABLE `network_devices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `device_id` (`device_id`);

--
-- Indexes for table `routers`
--
ALTER TABLE `routers`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_router_device_id` (`device_id`);

--
-- Indexes for table `switchs`
--
ALTER TABLE `switchs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_switch_device_id` (`device_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `access_points`
--
ALTER TABLE `access_points`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `network_devices`
--
ALTER TABLE `network_devices`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `routers`
--
ALTER TABLE `routers`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `switchs`
--
ALTER TABLE `switchs`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `access_points`
--
ALTER TABLE `access_points`
  ADD CONSTRAINT `fk_ap_device_id` FOREIGN KEY (`device_id`) REFERENCES `network_devices` (`device_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `routers`
--
ALTER TABLE `routers`
  ADD CONSTRAINT `fk_router_device_id` FOREIGN KEY (`device_id`) REFERENCES `network_devices` (`device_id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `switchs`
--
ALTER TABLE `switchs`
  ADD CONSTRAINT `fk_switch_device_id` FOREIGN KEY (`device_id`) REFERENCES `network_devices` (`device_id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;