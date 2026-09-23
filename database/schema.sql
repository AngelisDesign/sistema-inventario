CREATE DATABASE IF NOT EXISTS inventario
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE inventario;

CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  category_id INT,
  stock INT NOT NULL DEFAULT 0,
  stock_min INT NOT NULL DEFAULT 0,
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id)
);

INSERT INTO categories (name) VALUES
  ('Papelería'),
  ('Limpieza'),
  ('Tecnología');

INSERT INTO products (sku, name, category_id, stock, stock_min, price) VALUES
  ('P-001', 'Cuaderno A4 Rayado',      1, 120, 20, 1500.00),
  ('P-002', 'Bolígrafo Azul',          1,   8, 15,  300.00),
  ('P-003', 'Resma A4 500 hojas',      1,  45, 10, 4500.00),
  ('P-004', 'Marcador Pizarra',        1,   0,  5,  850.00),
  ('P-005', 'Carpeta 3 anillos',       1,  60, 10, 2200.00),
  ('P-006', 'Detergente 1L',           2,  30, 10, 1800.00),
  ('P-007', 'Mouse inalámbrico',       3,  12,  5, 9500.00);

  CREATE TABLE IF NOT EXISTS inventory_movements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  type ENUM('in', 'out', 'adjust') NOT NULL,
  quantity INT NOT NULL,
  stock_before INT NOT NULL,
  stock_after INT NOT NULL,
  note VARCHAR(255),
  user_name VARCHAR(100) DEFAULT 'admin',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id),
  INDEX idx_product (product_id),
  INDEX idx_created (created_at)
);

INSERT INTO inventory_movements
  (product_id, type, quantity, stock_before, stock_after, note, user_name, created_at)
VALUES
  (1, 'in',    50,  70, 120, 'Compra a proveedor', 'admin', NOW() - INTERVAL 2 HOUR),
  (2, 'out',   12,  20,   8, 'Venta mostrador',    'admin', NOW() - INTERVAL 3 HOUR),
  (3, 'in',    20,  25,  45, 'Reposición',         'admin', NOW() - INTERVAL 4 HOUR),
  (4, 'adjust', 3,   3,   0, 'Producto dañado',    'admin', NOW() - INTERVAL 1 DAY),
  (5, 'in',    60,   0,  60, 'Compra inicial',     'admin', NOW() - INTERVAL 2 DAY);