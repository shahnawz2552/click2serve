-- Click2Serve — Supabase schema migration
--
-- Run this in: Supabase dashboard → SQL Editor → New query → Run.
-- After running, also create a private Storage bucket named
-- "click2serve-documents" via Supabase dashboard → Storage → New bucket.
--
-- Idempotent: safe to re-run any time.
--   * CREATE TABLE IF NOT EXISTS  — won't recreate existing tables.
--   * ALTER TABLE ... ADD COLUMN IF NOT EXISTS — safely adds any columns
--     that newer versions of the app introduced. Re-run this whole file
--     after pulling code if you see errors like "Could not find the
--     '<column>' column of '<table>' in the schema cache (PGRST204)".

-- ─────────────────────────────────────────────────────────────────────────
-- Tables
-- ─────────────────────────────────────────────────────────────────────────
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
    whatsapp_enabled boolean not null default true,
    twilio_enabled  boolean not null default false,
    sms_enabled     boolean not null default false,
    -- Google Maps / Local SEO
    business_url    text not null default '',  -- canonical app URL (e.g. https://click2serve.streamlit.app)
    maps_url        text not null default '',  -- shareable Google Maps URL (https://maps.app.goo.gl/...)
    maps_embed_url  text not null default '',  -- iframe-embed URL from Google Maps "Embed a map"
    place_id        text not null default '',  -- Google Place ID, optional
    latitude        numeric,                   -- nullable, only set when known
    longitude       numeric,                   -- nullable
    updated_at      timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────────────────
-- Column-level migrations (safe to re-run)
-- ─────────────────────────────────────────────────────────────────────────
-- Postgres tracks columns independently of CREATE TABLE IF NOT EXISTS, so
-- newer columns added after the original table was created must be added
-- explicitly. Each ALTER below uses ADD COLUMN IF NOT EXISTS so it's a
-- no-op when the column already exists.

-- bookings: payment lifecycle columns added after v0.1
alter table bookings add column if not exists payment_status text not null default 'unpaid';
alter table bookings add column if not exists payment_ref    text;
alter table bookings add column if not exists amount_paid    integer not null default 0;
alter table bookings add column if not exists customer_email text;
alter table bookings add column if not exists notes          text;

-- shop_config: UPI fields, address, opening hours, owner info added later
alter table shop_config add column if not exists shop_name      text not null default 'Click2Serve';
alter table shop_config add column if not exists owner_name     text not null default '';
alter table shop_config add column if not exists owner_phone    text not null default '';
alter table shop_config add column if not exists address        text not null default '';
alter table shop_config add column if not exists upi_vpa        text not null default '';
alter table shop_config add column if not exists upi_payee_name text not null default '';
alter table shop_config add column if not exists opening_hours  text not null default '';
alter table shop_config add column if not exists whatsapp_enabled boolean not null default true;
alter table shop_config add column if not exists twilio_enabled  boolean not null default false;
alter table shop_config add column if not exists sms_enabled     boolean not null default false;
-- Google Maps / Local SEO (safe to re-run on existing deployments)
alter table shop_config add column if not exists business_url   text not null default '';
alter table shop_config add column if not exists maps_url       text not null default '';
alter table shop_config add column if not exists maps_embed_url text not null default '';
alter table shop_config add column if not exists place_id       text not null default '';
alter table shop_config add column if not exists latitude       numeric;
alter table shop_config add column if not exists longitude      numeric;
alter table shop_config add column if not exists updated_at     timestamptz not null default now();

-- services: requirements + active flag may pre-date some installations
alter table services add column if not exists requirements text    not null default '';
alter table services add column if not exists active       boolean not null default true;

-- ─────────────────────────────────────────────────────────────────────────
-- Visitor counter (cheap, append-only, no PII)
-- ─────────────────────────────────────────────────────────────────────────
-- One row per calendar day. Pages atomically `INSERT ... ON CONFLICT DO
-- UPDATE SET visits = visits + 1`. We deliberately don't store IPs,
-- user agents, or any identifier — just a per-day counter. That's
-- enough for "how many people visited" and zero privacy risk.
create table if not exists daily_visits (
    day      date primary key,
    visits   integer not null default 0
);
create index if not exists ix_daily_visits_day on daily_visits(day desc);

-- Row-level security on daily_visits
-- ----------------------------------
-- Supabase enables RLS by default on all new public-schema tables, and
-- denies every operation to the anon role unless an explicit policy
-- allows it. Without these policies the visitor counter writes silently
-- fail (record_visit() swallows the PostgREST error), which manifests
-- on the home page as "you are one of our first visitors" forever even
-- after dozens of real visits.
--
-- We expose three permissive policies so the anon key can: insert a
-- new daily row, increment today's existing row, and read the totals
-- for the footer / dashboard. No PII is stored in this table so the
-- exposure is intentional.
alter table daily_visits enable row level security;

drop policy if exists "daily_visits_select"  on daily_visits;
drop policy if exists "daily_visits_insert"  on daily_visits;
drop policy if exists "daily_visits_update"  on daily_visits;

create policy "daily_visits_select"
on daily_visits for select
to public
using (true);

create policy "daily_visits_insert"
on daily_visits for insert
to public
with check (true);

create policy "daily_visits_update"
on daily_visits for update
to public
using (true)
with check (true);

-- ─────────────────────────────────────────────────────────────────────────
-- Singleton config row
-- ─────────────────────────────────────────────────────────────────────────
insert into shop_config (id, updated_at)
values (1, now())
on conflict (id) do nothing;

-- ─────────────────────────────────────────────────────────────────────────
-- Reload PostgREST schema cache so new columns are visible to supabase-py
-- without waiting for the periodic auto-reload (this is what causes the
-- PGRST204 "could not find column ... in the schema cache" error).
-- ─────────────────────────────────────────────────────────────────────────
-- ─────────────────────────────────────────────────────────────────────────
-- documents.booking_id foreign key — ensure ON DELETE CASCADE is applied
-- ─────────────────────────────────────────────────────────────────────────
-- Older Supabase projects created from earlier versions of this file have
-- the FK without ON DELETE CASCADE, because Postgres won't change FK
-- actions on re-run of CREATE TABLE IF NOT EXISTS. That causes
-- 'violates foreign key constraint "documents_booking_id_fkey"' (23503)
-- when the owner tries to delete a booking that has attached documents.
-- The block below drops the existing FK (under any naming convention)
-- and recreates it with ON DELETE CASCADE.
do $$
declare
    fk_name text;
begin
    select tc.constraint_name
      into fk_name
    from information_schema.table_constraints tc
    join information_schema.key_column_usage kcu
      on tc.constraint_name = kcu.constraint_name
     and tc.table_schema    = kcu.table_schema
    where tc.table_schema    = 'public'
      and tc.table_name      = 'documents'
      and tc.constraint_type = 'FOREIGN KEY'
      and kcu.column_name    = 'booking_id'
    limit 1;

    if fk_name is not null then
        execute format('alter table public.documents drop constraint %I', fk_name);
    end if;

    alter table public.documents
        add constraint documents_booking_id_fkey
        foreign key (booking_id) references public.bookings(id)
        on delete cascade;
end$$;

notify pgrst, 'reload schema';
-- Row Level Security
-- ─────────────────────────────────────────────────────────────────────────
-- For an MVP single-tenant shop, we keep RLS DISABLED and rely on the
-- anon key being kept in Streamlit secrets only. If you later expose the
-- Supabase project publicly, enable RLS on each table and add policies
-- that scope reads/writes to authenticated owner roles.
