-- Mo rong 3: co so du lieu studentdb + bang students
CREATE DATABASE IF NOT EXISTS studentdb
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE studentdb;

-- Cho phép chạy lại script nhiều lần mà không bị trùng dữ liệu
DROP TABLE IF EXISTS students;

CREATE TABLE students (
  id         INT PRIMARY KEY AUTO_INCREMENT,
  student_id VARCHAR(10),
  fullname   VARCHAR(100),
  dob        DATE,
  major      VARCHAR(50)
);

INSERT INTO students (student_id, fullname, dob, major) VALUES
  ('SV001', 'Huỳnh Mạnh Phát', '2004-05-21', 'Kỹ thuật phần mềm'),
  ('SV002', 'Nguyễn Văn A',   '2004-03-14', 'Khoa học máy tính'),
  ('SV003', 'Trần Thị B',   '2004-07-02', 'Hệ thống thông tin'),
  ('SV004', 'Lê Minh C',    '2003-11-30', 'An toàn thông tin');


  