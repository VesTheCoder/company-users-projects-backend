set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=runtime_user="$DB_USER" --set=runtime_password="$DB_PASSWORD" \
  --set=migration_user="$DB_MIGRATION_USER" --set=migration_password="$DB_MIGRATION_PASSWORD" <<'SQL'
CREATE ROLE :"runtime_user" LOGIN PASSWORD :'runtime_password';
CREATE ROLE :"migration_user" LOGIN PASSWORD :'migration_password';
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"runtime_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"migration_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"runtime_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_user" IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO :"runtime_user";
SQL
