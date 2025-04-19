CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('employee', 'moderator'))
);


CREATE TABLE IF NOT EXISTS pvz (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    city VARCHAR(50) NOT NULL CHECK (city IN ('Москва', 'Санкт-Петербург', 'Казань'))
);


CREATE TABLE IF NOT EXISTS receptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pvz_id UUID NOT NULL REFERENCES pvz(id),
    status VARCHAR(50) NOT NULL CHECK (status IN ('in_progress', 'close')),
    FOREIGN KEY (pvz_id) REFERENCES pvz(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(50) NOT NULL CHECK (type IN ('электроника', 'одежда', 'обувь')),
    reception_id UUID NOT NULL REFERENCES receptions(id),
    FOREIGN KEY (reception_id) REFERENCES receptions(id) ON DELETE CASCADE
);

TRUNCATE TABLE products, receptions, pvz, users CASCADE;

INSERT INTO users (id, email, password_hash, role) VALUES
    ('11111111-1111-1111-1111-111111111111', 'moderator@example.com', '$2b$12$cf5zKkBNPw8eybwl3iArNONuCgvu.NRe.e1zdLgaqC4Fdc8PoqTmi', 'moderator'),
    ('22222222-2222-2222-2222-222222222222', 'employee1@example.com', '$2b$12$cf5zKkBNPw8eybwl3iArNONuCgvu.NRe.e1zdLgaqC4Fdc8PoqTmi', 'employee'),
    ('33333333-3333-3333-3333-333333333333', 'employee2@example.com', '$2b$12$cf5zKkBNPw8eybwl3iArNONuCgvu.NRe.e1zdLgaqC4Fdc8PoqTmi', 'employee');

-- Пароль для всех: '123456'

INSERT INTO pvz (id, registration_date, city) VALUES
    ('44444444-4444-4444-4444-444444444444', '2023-02-01 09:00:00', 'Москва'),
    ('55555555-5555-5555-5555-555555555555', '2023-02-02 10:00:00', 'Санкт-Петербург'),
    ('66666666-6666-6666-6666-666666666666', '2023-02-03 11:00:00', 'Казань');

INSERT INTO receptions (id, date_time, pvz_id, status) VALUES
    ('77777777-7777-7777-7777-777777777777', '2023-03-01 13:00:00', '44444444-4444-4444-4444-444444444444', 'close'),
    ('88888888-8888-8888-8888-888888888888', '2023-03-02 14:00:00', '55555555-5555-5555-5555-555555555555', 'in_progress'),
    ('99999999-9999-9999-9999-999999999999', '2023-03-03 15:00:00', '66666666-6666-6666-6666-666666666666', 'in_progress');

INSERT INTO products (id, date_time, type, reception_id) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '2023-03-01 13:30:00', 'электроника', '77777777-7777-7777-7777-777777777777'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '2023-03-01 13:35:00', 'одежда', '77777777-7777-7777-7777-777777777777'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', '2023-03-02 14:05:00', 'обувь', '88888888-8888-8888-8888-888888888888');
