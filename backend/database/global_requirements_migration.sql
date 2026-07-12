-- Run this in Supabase SQL Editor only if query-resolution columns do not exist.
-- Do not alter visa_requirements: this project uses its existing text fields:
-- applies_to_countries = [ALL] or [Botswana,United States]
-- excluded_countries   = [ALL] or [ALLex,Botswana,United States]

alter table queries add column if not exists status text not null default 'open'
  check (status in ('open', 'resolved'));
alter table queries add column if not exists resolved_at timestamptz;
alter table queries add column if not exists resolved_by uuid references users(id);
create index if not exists queries_resolution_idx on queries (status, created_at);
