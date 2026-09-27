-- SecureSign RLS policies (defense-in-depth).
-- Applied separately from Prisma migrations against Supabase Postgres.
-- Primary authorization lives in the application layer; these policies guard
-- any future direct Supabase client access.

alter table profiles enable row level security;
alter table documents enable row level security;
alter table signing_keys enable row level security;
alter table signing_requests enable row level security;
alter table signature_positions enable row level security;
alter table signatures enable row level security;
alter table verification_records enable row level security;
alter table audit_logs enable row level security;

drop policy if exists profiles_select_own on profiles;
create policy profiles_select_own on profiles
  for select to authenticated using (auth.uid() = id);

drop policy if exists profiles_update_own on profiles;
create policy profiles_update_own on profiles
  for update to authenticated using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists profiles_insert_own on profiles;
create policy profiles_insert_own on profiles
  for insert to authenticated with check (auth.uid() = id);

drop policy if exists documents_all_own on documents;
create policy documents_all_own on documents
  for all to authenticated
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

drop policy if exists signing_keys_all_own on signing_keys;
create policy signing_keys_all_own on signing_keys
  for all to authenticated
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

drop policy if exists signing_requests_own on signing_requests;
create policy signing_requests_own on signing_requests
  for all to authenticated
  using (
    signer_id = auth.uid()
    or exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  )
  with check (
    signer_id = auth.uid()
    or exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  );

drop policy if exists signature_positions_own on signature_positions;
create policy signature_positions_own on signature_positions
  for all to authenticated
  using (
    exists (
      select 1
      from signing_requests sr
      join documents d on d.id = sr.document_id
      where sr.id = signing_request_id
        and (sr.signer_id = auth.uid() or d.owner_id = auth.uid())
    )
  )
  with check (
    exists (
      select 1
      from signing_requests sr
      join documents d on d.id = sr.document_id
      where sr.id = signing_request_id
        and (sr.signer_id = auth.uid() or d.owner_id = auth.uid())
    )
  );

drop policy if exists signatures_own on signatures;
create policy signatures_own on signatures
  for all to authenticated
  using (
    signer_id = auth.uid()
    or exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  )
  with check (
    signer_id = auth.uid()
    or exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  );

drop policy if exists verification_records_own on verification_records;
create policy verification_records_own on verification_records
  for all to authenticated
  using (
    exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from documents d
      where d.id = document_id and d.owner_id = auth.uid()
    )
  );

drop policy if exists audit_logs_select_own on audit_logs;
create policy audit_logs_select_own on audit_logs
  for select to authenticated using (actor_id = auth.uid());

drop policy if exists audit_logs_insert_own on audit_logs;
create policy audit_logs_insert_own on audit_logs
  for insert to authenticated with check (actor_id = auth.uid());