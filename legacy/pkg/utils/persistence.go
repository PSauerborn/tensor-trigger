package utils

import (
    "fmt"
    "context"

    "github.com/jackc/pgx/v4/pgxpool"
    log "github.com/sirupsen/logrus"
)

type Persistence struct {
    DatabaseURL string
    Session     *pgxpool.Pool
}

// function to connect persistence to postgres server
// note that the connection is returned and should be
// closed with a defer conn.Close(context) statement
func(db *Persistence) Connect() (*pgxpool.Pool, error) {
    log.Debug(fmt.Sprintf("creating new database connection"))
    // connect to postgres server and set session in persistence
    conn, err := pgxpool.Connect(context.Background(), db.DatabaseURL)
    if err != nil {
        log.Error(fmt.Errorf("error connecting to postgres service: %+v", err))
        return nil, err
    }
    db.Session = conn
    return conn, err
}

func NewPersistence(url string) *Persistence {
    return &Persistence{
        DatabaseURL: url,
    }
}