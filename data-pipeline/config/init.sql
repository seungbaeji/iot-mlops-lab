-- 데이터베이스 및 사용자 생성 (존재하지 않을 때만)
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'iot_ml_lab') THEN
      CREATE DATABASE iot_ml_lab;
   END IF;
END$$;

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lab_admin') THEN
      CREATE USER lab_admin WITH PASSWORD 'changeme';
   END IF;
END$$;

-- 권한 부여
GRANT ALL PRIVILEGES ON DATABASE iot_ml_lab TO lab_admin;

-- sensor_data 테이블 생성 (iot_ml_lab에서 실행되어야 함)
\c iot_ml_lab;
CREATE TABLE IF NOT EXISTS sensor_data (
    device_id VARCHAR(64) NOT NULL,
    timestamp BIGINT NOT NULL,
    temperature FLOAT,
    humidity FLOAT
);

-- 복합 인덱스: device_id + timestamp
CREATE INDEX IF NOT EXISTS idx_sensor_device_time ON sensor_data (device_id, timestamp); 