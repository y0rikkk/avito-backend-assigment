#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "pvz_db" <<-EOSQL
    CREATE DATABASE pvz_test_db;
    GRANT ALL PRIVILEGES ON DATABASE pvz_test_db TO $POSTGRES_USER;
EOSQL