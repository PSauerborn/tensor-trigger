package api

import (
    "fmt"
    "time"
    "net/http"

    "github.com/gin-gonic/gin"
    log "github.com/sirupsen/logrus"
)

// middleware used to inject postgres connection into request
func PostgresSessionMiddleware(postgresUrl string) gin.HandlerFunc {
    return func(ctx *gin.Context) {
        // create new persistence instance and connect to postgres
        db := NewPersistence(postgresUrl)
        conn, err := db.Connect()
        if err != nil {
            log.Error(fmt.Errorf("unable to retrieve assets from postgres: %+v", err))
            ctx.JSON(http.StatusInternalServerError, gin.H{
                "http_code": http.StatusInternalServerError, "message": "Internal server error"})
            return
        }
        defer conn.Close()

        ctx.Set("persistence", db)
        ctx.Next()
    }
}

func TimerMiddleware() gin.HandlerFunc {
    return func(ctx *gin.Context) {
        start := time.Now()
        ctx.Next()
        // measure execution time and log time for call
        executionTime := time.Now().Sub(start)
        log.Info(fmt.Sprintf("call execution time: %fs", executionTime.Seconds()))
    }
}