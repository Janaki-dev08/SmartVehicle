-- ============================================================
-- Farm2Home — Phase 1 Initial Migration
-- Tables: users, farmers, consumers, bulk_buyers, farms, addresses
-- Run: psql -U postgres -d farm2home -f 001_init.sql
-- ============================================================

-- Enable uuid-ossp for UUID generation (PostgreSQL extension)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── users ────────────────────────────────────────────────────────────────────
-- Core identity table for all roles (farmer, consumer, bulk_buyer, admin).
-- Passwords are stored as bcrypt hashes — never plain text.
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash TEXT        NOT NULL,
  role          VARCHAR(20) NOT NULL CHECK (role IN ('farmer', 'consumer', 'bulk_buyer', 'admin')),
  is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role  ON users(role);

-- ─── farmers ──────────────────────────────────────────────────────────────────
-- Profile extension for users with role='farmer'.
CREATE TABLE IF NOT EXISTS farmers (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id    UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  full_name  VARCHAR(150),
  phone      VARCHAR(20),
  state      VARCHAR(100),
  district   VARCHAR(100),
  village    VARCHAR(150),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_farmers_user_id ON farmers(user_id);

-- ─── consumers ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consumers (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id    UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  full_name  VARCHAR(150),
  phone      VARCHAR(20),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consumers_user_id ON consumers(user_id);

-- ─── bulk_buyers ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bulk_buyers (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id       UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  full_name     VARCHAR(150),
  org_name      VARCHAR(200),
  phone         VARCHAR(20),
  business_type VARCHAR(100), -- e.g. restaurant, hotel, distributor, retailer
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bulk_buyers_user_id ON bulk_buyers(user_id);

-- ─── farms ────────────────────────────────────────────────────────────────────
-- A farmer can own multiple farms.
CREATE TABLE IF NOT EXISTS farms (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  farmer_id    UUID        NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
  farm_name    VARCHAR(200),
  area_acres   NUMERIC(10,2),
  soil_type    VARCHAR(100),
  water_source VARCHAR(100),
  lat          NUMERIC(10,7),  -- GPS latitude (optional)
  lng          NUMERIC(10,7),  -- GPS longitude (optional)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_farms_farmer_id ON farms(farmer_id);

-- ─── addresses ────────────────────────────────────────────────────────────────
-- Delivery/contact addresses linked to any user.
-- Used for consumer delivery addresses and farmer location addresses.
CREATE TABLE IF NOT EXISTS addresses (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label      VARCHAR(100) DEFAULT 'Home', -- e.g. Home, Office, Farm
  line1      VARCHAR(255),
  line2      VARCHAR(255),
  city       VARCHAR(100),
  district   VARCHAR(100),
  state      VARCHAR(100),
  pincode    VARCHAR(10),
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_addresses_user_id ON addresses(user_id);

-- ─── Auto-update updated_at trigger ──────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables
DO $$
DECLARE
  t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','farmers','consumers','bulk_buyers','farms','addresses']
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS set_updated_at ON %I;
      CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON %I
        FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
    ', t, t);
  END LOOP;
END;
$$;

-- Done
SELECT 'Phase 1 migration applied successfully ✅' AS status;
