package api

import (
    "fmt"
    "errors"
    "encoding/json"

    "github.com/google/uuid"
    log "github.com/sirupsen/logrus"

    "github.com/PSauerborn/tensor-trigger/pkg/utils"
)

var (
    ErrInvalidMetadata = errors.New("Invalid model metadata: invalid JSON format")
)


// function to update metadata with new file ID
func addFileToMetadata(fileId uuid.UUID, meta ModelMetadata,
    uploader *utils.S3Uploader) error {

    log.Debug(fmt.Sprintf("adding file %s to metadata", fileId))
    meta.Files = append(meta.Files, fileId)

    // generate s3 storage key for metadata and cast to JSON
    key := fmt.Sprintf("metadata/%s", meta.ModelId)
    updatedMeta, err := json.Marshal(meta)
    if err != nil {
        log.Error(fmt.Errorf("unable cast metadat to JSON format: %+v", err))
        return ErrInvalidMetadata
    }

    // upload updated metadata to s3 server
    if err := uploader.UploadFile("tensor-trigger", key, updatedMeta, true); err != nil {
        log.Error(fmt.Errorf("unable to update metadata for model: %+v", err))
        return err
    }
    return nil
}

// function to retrieve model metadata from s3 storage from a given model ID
func getModelMetadata(modelId uuid.UUID, downloader *utils.S3Downloader) (
    ModelMetadata, error) {
    log.Debug(fmt.Sprintf("retrieving model metadata for model %s", modelId))

    var meta ModelMetadata
    key := fmt.Sprintf("metadata/%s", modelId)
    // download file contents into local byte array from s3 storage
    metaJson, err := downloader.DownloadFileToBytes("tensor-trigger", key)
    if err != nil {
        return meta, err
    }
    // cast byte array returned from s3 storage into JSON array
    if err := json.Unmarshal(metaJson, &meta); err != nil {
        log.Error(fmt.Errorf("unable to parse metadata JSON: %+v", err))
        return meta, ErrInvalidMetadata
    }
    return meta, nil
}

// function to retrieve all metadata files from s3 storage container
func getAllMetadataFiles(downloader *utils.S3Downloader) ([]ModelMetadata, error) {
    log.Debug("retrieving metadata for all stored models...")

    models := []ModelMetadata{}
    // get all metadata files from s3 storage bucket
    files, err := downloader.GetAllObjectsInBucketAsync("tensor-trigger")
    if err != nil {
        log.Error(fmt.Errorf("unable to retrieve metadata files: %+v", err))
        return models, err
    }
    // iterate over all files and attempt to cast to struct. ignores any
    // files that do not have the correct JSON format
    for _, file := range(files) {
        var model ModelMetadata
        if err := json.Unmarshal(file, &model); err != nil {
            log.Warn(fmt.Errorf("found invalid JSON model in S3 bucket: %+v", err))
            continue
        } else {
            models = append(models, model)
        }
    }
    return models, nil
}