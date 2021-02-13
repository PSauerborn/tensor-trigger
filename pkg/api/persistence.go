package api

import (
    "github.com/PSauerborn/tensor-trigger/pkg/utils"
)

type Persistence struct {
    *utils.Persistence
}

func NewPersistence(postgresUrl string) *Persistence {
    // create instance of base persistence
    basePersistence := utils.NewPersistence(postgresUrl)
    return &Persistence{
        basePersistence,
    }
}

