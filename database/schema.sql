create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  name text not null default '',
  email text,
  created_at timestamptz not null default now()
);

create table if not exists public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  filename text not null,
  file_path text not null,
  extracted_text text not null default '',
  uploaded_at timestamptz not null default now()
);

create table if not exists public.job_descriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_title text not null default '',
  company_name text not null default '',
  description text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.analysis_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  resume_id uuid references public.resumes(id) on delete set null,
  job_id uuid references public.job_descriptions(id) on delete set null,
  ats_score integer not null check (ats_score between 0 and 100),
  matched_skills jsonb not null default '[]'::jsonb,
  missing_skills jsonb not null default '[]'::jsonb,
  suggestions jsonb not null default '[]'::jsonb,
  analysis_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists resumes_user_idx on public.resumes(user_id);
create index if not exists reports_user_created_idx on public.analysis_reports(user_id, created_at desc);
create index if not exists jobs_user_idx on public.job_descriptions(user_id);

alter table public.profiles enable row level security;
alter table public.resumes enable row level security;
alter table public.job_descriptions enable row level security;
alter table public.analysis_reports enable row level security;

create policy "profiles select own" on public.profiles for select using (auth.uid() = id);
create policy "profiles update own" on public.profiles for update using (auth.uid() = id);
create policy "resumes own access" on public.resumes for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "jobs own access" on public.job_descriptions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "reports own access" on public.analysis_reports for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('resumes','resumes',false,5242880,array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
on conflict (id) do nothing;

create policy "users upload own resumes" on storage.objects for insert
with check (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "users read own resumes" on storage.objects for select
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "users delete own resumes" on storage.objects for delete
using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles(id,name,email)
  values(new.id, coalesce(new.raw_user_meta_data->>'name',''), new.email)
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute procedure public.handle_new_user();
