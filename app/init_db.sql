CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('employee', 'moderator'))
);


CREATE TABLE IF NOT EXISTS pvz (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    city VARCHAR(50) NOT NULL CHECK (city IN ('Moscow', 'Saint Petersburg', 'Kazan'))
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
    type VARCHAR(50) NOT NULL CHECK (type IN ('Электроника', 'Одежда', 'Обувь')),
    reception_id UUID NOT NULL REFERENCES receptions(id),
    FOREIGN KEY (reception_id) REFERENCES receptions(id) ON DELETE CASCADE
);