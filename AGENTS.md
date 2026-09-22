# Project Guidelines

- Keep Docker and Docker Compose configuration minimal.
- Do not add fallback defaults or required-variable guards in Compose; developer-managed environment files are expected to provide valid values.
- Keep startup ordering that is required for services and migrations to run correctly.
- Keep runtime and migration/bootstrap database credentials separated; do not pass privileged database credentials to the API container.
- Keep `Settings` limited to loading and typing environment values; assume developer-managed environment values are valid and do not add configuration validators or normalizers.
