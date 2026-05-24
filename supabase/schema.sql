-- Click2Serve — Supabase schema migration
--
-- Run this once in: Supabase dashboard → SQL Editor → New query → Run.
-- After running, also create a private Storage bucket named
-- "click2serve-documents" via Supabase dashboard → Storage → New bucket.
--
-- Idempotent: safe to re-run (uses CREATE TABLE IF NOT EXISTS).

create table if not exists services (
    id           bigserial primary key,
    name         text    not null unique,
    category     text    not null,
    description  text    not null default '',
    govt_fee     integer not null default 0,
    service_charge integer not null default 0,
    eta_hours    integer not null default 24,
    requirements text    not null default '',
    active       boolean not null default true
);
create index if not exists ix_services_active on services(active);

create table if not exists bookings (
    id             bigserial primary key,
    token          text not null unique,
    service_id     bigint not null references services(id),
    customer_name  text not null,
    customer_phone text not null,
    customer_email text,
    notes          text,
    status         text not null default 'Pending',
    payment_method text not null default 'Unpaid',
    payment_status text not null default 'unpaid',
    payment_ref    text,
    amount_paid    integer not null default 0,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
create index if not exists ix_bookings_token   on bookings(token);
create index if not exists ix_bookings_phone   on bookings(customer_phone);
create index if not exists ix_bookings_status  on bookings(status);
create index if not exists ix_bookings_created on bookings(created_at);

create table if not exists documents (
    id          bigserial primary key,
    booking_id  bigint not null references bookings(id) on delete cascade,
    file_name   text not null,
    file_path   text not null,                -- key inside the storage bucket
    file_type   text,
    size_bytes  bigint,
    uploaded_at timestamptz not null default now()
);
create index if not exists ix_documents_booking on documents(booking_id);

create table if not exists users (
    id            bigserial primary key,
    username      text not null unique,
    password_hash text not null,
    role          text not null default 'owner',
    created_at    timestamptz not null default now()
);

create table if not exists shop_config (
    id              integer primary key check (id = 1),  -- singleton row
    shop_name       text not null default 'Click2Serve',
    owner_name      text not null default '',
    owner_phone     text not null default '',
    address         text not null default '',
    upi_vpa         text not null default '',
    upi_payee_name  text not null default '',
    opening_hours   text not null default '',
    updated_at      timestamptz not null default now()
);

-- Ensure the singleton config row exists
insert into shop_config (id, updated_at)
values (1, now())
on conflict (id) do nothing;

-- ─────────────────────────────────────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────────────────────────────────────
-- For an MVP single-tenant shop, we keep RLS DISABLED and rely on the
-- anon key being kept in Streamlit secrets only. If you later expose the
-- Supabase project publicly, enable RLS on each table and add policies
-- that scope reads/writes to authenticated owner roles.
