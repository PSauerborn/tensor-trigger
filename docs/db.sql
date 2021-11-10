CREATE TABLE models(
    model_id UUID PRIMARY KEY NOT NULL,
    username TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_description TEXT NOT NULL,
    model_schema JSON NOT NULL,
    size INT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
)