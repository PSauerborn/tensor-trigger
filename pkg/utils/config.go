package utils

import (
    "os"
    "fmt"
    "strings"
    "errors"

    log "github.com/sirupsen/logrus"
)

var (
    // define custom errors for config map
    ErrKeyNotFound = errors.New("Cannot find specified key in mapped values")
)

type ConfigMap struct{
    ValueMaps map[string]string
}

// function to create a new config map
func NewConfigMap() *ConfigMap {
    return &ConfigMap{map[string]string{}}
}

// function to create new config map with a collection of defaults
func NewConfigMapWithValues(defaults map[string]string) *ConfigMap {
    return &ConfigMap{defaults}
}

// function used to set a default value for a given key
func(cfg *ConfigMap) Set(key string, defaultVal string) {
    cfg.ValueMaps[key] = defaultVal
}

// function used to retrieve mappings. environment variables override
// hard coded defaults
func(cfg *ConfigMap) Get(key string) string {
    // retrieve and return value from environment variables if set
    value := os.Getenv(strings.ToUpper(key))
    if len(value) > 0 {
        log.Info(fmt.Sprintf("overriding variable '%s' with value %s",
            strings.ToUpper(key), value))
        return value
    }
    // retrieve value from local mappings and return if set
    if val, ok := cfg.ValueMaps[key]; ok {
        return val
    }
    return ""
}

// function used to retrieve mappings. environment variables override
// hard coded defaults. error is returned if no value is set
func(cfg *ConfigMap) MustGet(key string) (string, error) {
    // retrieve and return value from environment variables if set
    value := os.Getenv(strings.ToUpper(key))
    if len(value) > 0 {
        log.Info(fmt.Sprintf("overriding variable '%s' with value %s",
            strings.ToUpper(key), value))
        return value, nil
    }
    // retrieve value from local mappings and return if set
    if val, ok := cfg.ValueMaps[key]; ok {
        return val, nil
    }
    return "", ErrKeyNotFound
}