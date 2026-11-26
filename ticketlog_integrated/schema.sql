-- Supabase SQL Editor에서 한 번 실행. 기존 프로젝트와 분리된 테이블.
create table if not exists public.ticketlog_schedules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  performance_id text not null,
  title text not null check (length(title) between 1 and 500),
  venue text not null default '',
  genre text not null default '',
  vendor text not null check (length(vendor) between 1 and 200),
  vendor_url text not null default '',
  poster text not null default '',
  performance_period text not null default '',
  opening_at timestamptz not null,
  status text not null default '예매 예정' check (status in ('예매 예정','구매 완료','구매 실패','취소')),
  note text not null default '' check (length(note)<=500),
  demo boolean not null default false,
  created_at timestamptz not null default now(),
  unique (user_id, performance_id, vendor, opening_at)
);
alter table public.ticketlog_schedules enable row level security;
revoke all on public.ticketlog_schedules from anon;
grant select,insert,update,delete on public.ticketlog_schedules to authenticated;
drop policy if exists own_ticketlog_schedules on public.ticketlog_schedules;
create policy own_ticketlog_schedules on public.ticketlog_schedules for all to authenticated
using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
