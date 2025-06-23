-- Enable UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- COMPANIES
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    url TEXT UNIQUE,
    founded_year INTEGER,
    total_employees INTEGER,
    headquarters_city VARCHAR(255),
    employee_locations TEXT,
    employee_growth_2y FLOAT,
    employee_growth_1y FLOAT,
    employee_growth_6m FLOAT,
    description TEXT,
    industry VARCHAR(255),
    imported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- RULES
CREATE TABLE rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    input_name VARCHAR(255) NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    target_object TEXT NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    operation_payload JSONB NOT NULL,
    match_value TEXT,
    default_value TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- PROCESSING RESULTS
CREATE TABLE processing_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    feature_name VARCHAR(255) NOT NULL,
    result_value TEXT,
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
