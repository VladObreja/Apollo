Apollo is an epistemological extraction engine.

## Configuration Requirements

For local development and testing, you can use the testcontainers integration or the provided `docker-compose.yml`.

For any non-local deployment or production usage, you MUST provide a `.env` file containing the `DATABASE_URL` environment variable.

Example `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/apollo
```
