CREATE TABLE IF NOT EXISTS plg_agenda_bookings (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    service_name VARCHAR NOT NULL,
    scheduled_at VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    notes VARCHAR,
    created_at VARCHAR NOT NULL
)
