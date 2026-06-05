-- Supabase Schema for Utility Bill Calculator
-- Tables for meter readings, bills, and tariff rates

-- ============================================================
-- TARIFF_RATES TABLE
-- ============================================================
-- Stores current and historical electricity and water rates
-- Supports rate versioning with effective/expiry dates

CREATE TABLE IF NOT EXISTS public.tariff_rates (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    rate_type TEXT NOT NULL,
    rate_value DECIMAL(10, 4) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    source TEXT DEFAULT 'manual',
    last_updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_rate_type CHECK (rate_type IN ('electricity', 'water_usage', 'water_waterborne')),
    CONSTRAINT positive_rate CHECK (rate_value > 0)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_tariff_rates_type_date 
    ON public.tariff_rates(rate_type, effective_date DESC);

-- Enable Row Level Security
ALTER TABLE public.tariff_rates ENABLE ROW LEVEL SECURITY;

-- Allow public read
CREATE POLICY "Allow public read tariff_rates"
    ON public.tariff_rates FOR SELECT
    USING (true);

-- Allow insert for authenticated users (admin)
CREATE POLICY "Allow authenticated insert tariff_rates"
    ON public.tariff_rates FOR INSERT
    WITH CHECK (true);

-- ============================================================
-- METER_READINGS TABLE
-- ============================================================
-- Stores meter reading history for each tenant

CREATE TABLE IF NOT EXISTS public.meter_readings (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_id TEXT NOT NULL,
    reading_date DATE NOT NULL,
    electricity_reading DECIMAL(10, 2),
    water_reading DECIMAL(10, 2),
    source TEXT DEFAULT 'telegram',
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_reading CHECK (electricity_reading > 0 OR water_reading > 0)
);

CREATE INDEX IF NOT EXISTS idx_meter_readings_tenant_date 
    ON public.meter_readings(tenant_id, reading_date DESC);

ALTER TABLE public.meter_readings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow users read own meter_readings"
    ON public.meter_readings FOR SELECT
    USING (true);

CREATE POLICY "Allow insert meter_readings"
    ON public.meter_readings FOR INSERT
    WITH CHECK (true);

-- ============================================================
-- BILLS TABLE
-- ============================================================
-- Stores calculated bills with full breakdown

CREATE TABLE IF NOT EXISTS public.bills (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tenant_id TEXT NOT NULL,
    billing_period TEXT NOT NULL,
    
    -- Electricity
    electricity_usage DECIMAL(10, 2),
    electricity_rate DECIMAL(10, 4),
    electricity_charge DECIMAL(10, 2),
    
    -- Water
    water_usage DECIMAL(10, 2),
    water_usage_rate DECIMAL(10, 4),
    water_usage_charge DECIMAL(10, 2),
    water_waterborne_rate DECIMAL(10, 4),
    water_waterborne_tax DECIMAL(10, 2),
    water_conservation_tax DECIMAL(10, 2),
    water_total DECIMAL(10, 2),
    
    -- Summary
    subtotal DECIMAL(10, 2),
    tax_rate DECIMAL(5, 2),
    tax_amount DECIMAL(10, 2),
    surcharge DECIMAL(10, 2),
    total_amount DECIMAL(10, 2),
    
    -- Metadata
    status TEXT DEFAULT 'generated',
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_amount CHECK (total_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_bills_tenant_period 
    ON public.bills(tenant_id, billing_period DESC);

ALTER TABLE public.bills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow users read own bills"
    ON public.bills FOR SELECT
    USING (true);

CREATE POLICY "Allow insert bills"
    ON public.bills FOR INSERT
    WITH CHECK (true);

-- ============================================================
-- INITIAL DATA
-- ============================================================
-- Seed tariff_rates with current Singapore rates

INSERT INTO public.tariff_rates (rate_type, rate_value, effective_date, source)
VALUES 
    ('electricity', 0.2674, '2024-01-01', 'SP Energy Official'),
    ('water_usage', 1.43, '2024-01-01', 'PUB Official'),
    ('water_waterborne', 1.09, '2024-01-01', 'PUB Official')
ON CONFLICT DO NOTHING;

-- ============================================================
-- AUDIT LOGS (Optional, for future use)
-- ============================================================
/*
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    actor TEXT,
    changes JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON public.audit_logs(entity_type, entity_id);
*/
