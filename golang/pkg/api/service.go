package api

import (
    "fmt"
    "bytes"
    "time"
    "net/http"
    "io/ioutil"
    "encoding/json"

    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    "github.com/aws/aws-sdk-go/aws"
    log "github.com/sirupsen/logrus"

    "github.com/PSauerborn/tensor-trigger/pkg/utils"
)

// function used to generate new API
func New(s3Config *aws.Config) *gin.Engine {
    // set global module configuration
    router := gin.Default()

    router.GET("/tensor-trigger/health", healthCheckHandler)
    // create routes with upload and download middleware
    router.GET("/tensor-trigger/models", utils.S3DownloadMiddelware(s3Config), getModelsMetadataHandler)
    router.GET("/tensor-trigger/file/:modelId/:fileId", utils.S3DownloadMiddelware(s3Config), downloadModelHandler)
    // create routes to handle model uploading and triggering
    router.POST("/tensor-trigger/model", utils.S3UploadMiddelware(s3Config), createModelHandler)
    router.PUT("/tensor-trigger/file/:modelId", utils.S3UploadMiddelware(s3Config),
        utils.S3DownloadMiddelware(s3Config), uploadModelHandler)
    router.PUT("/tensor-trigger/models/trigger/:modelId/:fileId", triggerModelHandler)
    return router
}

// function to serve health check
func healthCheckHandler(ctx *gin.Context) {
    log.Info("received request for health check handler")
    ctx.JSON(http.StatusOK,
        gin.H{"http_code": http.StatusOK, "message": "Service running"})
}

type ModelMetadata struct {
    ModelName        string      `json:"model_name" binding:"required"`
    ModelDescription string      `json:"model_description"`
    ModelId          uuid.UUID   `json:"model_id"`
    Created          time.Time   `json:"created"`
    Files            []uuid.UUID `json:"files"`
}

// API handler to create a new models. models are created
// as JSON objects, and tensor flow files can then be uploaded
// against a given model
func createModelHandler(ctx *gin.Context) {
    log.Info("received request to generate new model")
    var request struct {
        ModelName        string `json:"model_name" binding:"required"`
        ModelDescription string `json:"model_description"`
    }
    if err := ctx.ShouldBind(&request); err != nil {
        log.Error(fmt.Errorf("unable to parse request model: %+v", err))
        ctx.JSON(http.StatusBadRequest,
            gin.H{"http_code": http.StatusBadRequest, "message": "Invalid request body"})
        return
    }

    modelId := uuid.New()
    uploader, _ := ctx.MustGet("s3_uploader").(*utils.S3Uploader)
    // generate JSON string from given data
    modelJson, _ := json.Marshal(ModelMetadata{
        ModelName: request.ModelName,
        ModelDescription: request.ModelDescription,
        ModelId: modelId,
        Created: time.Now(),
        Files: []uuid.UUID{},
    })

    // upload metadata to S3 bucket
    key := fmt.Sprintf("metadata/%s", modelId.String())
    if err := uploader.UploadFile("tensor-trigger", key, modelJson, false); err != nil {
        log.Error(fmt.Errorf("unable to upload metadata to S3 storage: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }
    ctx.JSON(http.StatusCreated, gin.H{"http_code": http.StatusCreated,
        "message": "Successfully created model", "model_id": modelId})
}

// function to upload a new tensorflow model
func uploadModelHandler(ctx *gin.Context) {
    log.Info("received request to upload new tensorflow model")
    // extract model ID from path parameters and convert to UUID
    modelId, err := uuid.Parse(ctx.Param("modelId"))
    if err != nil {
        log.Error(fmt.Errorf("unable to parse model ID %s", ctx.Param("modelId")))
        ctx.JSON(http.StatusBadRequest,
            gin.H{"http_code": http.StatusBadRequest, "message": "Invalid model ID"})
        return
    }

    // extract request body and read
    body, err := ioutil.ReadAll(ctx.Request.Body)
    if err != nil {
        log.Error(fmt.Errorf("unable to extract request body: %+v", err))
        ctx.JSON(http.StatusBadRequest,
            gin.H{"http_code": http.StatusBadRequest, "message": "Invalid request body"})
        return
    }

    // get s3 downloader from request context and retrieve model metadata
    downloader, _ := ctx.MustGet("s3_downloader").(*utils.S3Downloader)
    meta, err := getModelMetadata(modelId, downloader)
    if err != nil {
        switch err {
        case utils.ErrKeyDoesNotExist:
            log.Error(fmt.Errorf("unable to download model for key %s: %+v", modelId, err))
            ctx.JSON(http.StatusBadRequest,
                gin.H{"http_code": http.StatusBadRequest, "message": "Cannot find model with given model ID"})
        default:
            log.Error(fmt.Errorf("unable to download model for key %s: %+v", modelId, err))
            ctx.JSON(http.StatusInternalServerError,
                gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        }
        return
    }

    fileId := uuid.New()
    // get S3 uploader from context and upload file to S3 server using
    // combination of model ID and File ID
    uploader, _ := ctx.MustGet("s3_uploader").(*utils.S3Uploader)
    key := fmt.Sprintf("models/%s/%s", modelId, fileId)
    if err := uploader.UploadFile("tensor-trigger", key, body, false); err != nil {
        log.Error(fmt.Errorf("unable to upload file to S3 server: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }

    // add generated file ID to metadata and update metadata in S3 bucket
    if err := addFileToMetadata(fileId, meta, uploader); err != nil {
        log.Error(fmt.Errorf("unable to update model metadata: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }
    ctx.JSON(http.StatusOK,
        gin.H{"http_code": http.StatusOK, "message": "Successfully uploaded file", "file_id": fileId})
}

// function to retrieve list of models
func getModelsMetadataHandler(ctx *gin.Context) {
    log.Info("received request to retrieve tensorflow models")

    downloader, _ := ctx.MustGet("s3_downloader").(*utils.S3Downloader)
    // retrive all metadata files from s3 storage
    models, err := getAllMetadataFiles(downloader)
    if err != nil {
        log.Error(fmt.Errorf("unable to retrieve metadata files: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }
    ctx.JSON(http.StatusOK,
        gin.H{"http_code": http.StatusOK, "data": models})
}

// function to download binary model
func downloadModelHandler(ctx *gin.Context) {
    log.Info("received request to download tensorflow model")
    // extract model ID from path parameters and convert to UUID
    modelId, err := uuid.Parse(ctx.Param("modelId"))
    if err != nil {
        log.Error(fmt.Errorf("unable to parse model ID %s", ctx.Param("modelId")))
        ctx.JSON(http.StatusBadRequest,
            gin.H{"http_code": http.StatusBadRequest, "message": "Invalid model ID"})
        return
    }

    // extract file ID from path parameters and convert to UUID
    fileId, err := uuid.Parse(ctx.Param("fileId"))
    if err != nil {
        log.Error(fmt.Errorf("unable to parse model ID %s", ctx.Param("fileId")))
        ctx.JSON(http.StatusBadRequest,
            gin.H{"http_code": http.StatusBadRequest, "message": "Invalid file ID"})
        return
    }

    // get download from request context and download file to bytes array
    downloader, _ := ctx.MustGet("s3_downloader").(*utils.S3Downloader)
    key := fmt.Sprintf("models/%s/%s", modelId, fileId)
    data, err := downloader.DownloadFileToBytes("tensor-trigger", key)
    if err != nil {
        switch err {
        case utils.ErrKeyDoesNotExist:
            log.Error(fmt.Errorf("unable to download model for key %s: %+v", modelId, err))
            ctx.JSON(http.StatusNotFound,
                gin.H{"http_code": http.StatusNotFound, "message": "Cannot find model with given model ID"})
        default:
            log.Error(fmt.Errorf("unable to download model for key %s: %+v", modelId, err))
            ctx.JSON(http.StatusInternalServerError,
                gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        }
        return
    }
    // write data to new reader and return
    responseBody := bytes.NewReader(data)
    ctx.DataFromReader(http.StatusOK, int64(len(data)), "",
        responseBody, nil)
}

// function to trigger tensorflow model
func triggerModelHandler(ctx *gin.Context) {
    log.Info(fmt.Sprintf("received request to trigger model %s", ctx.Param("modelId")))
    ctx.JSON(http.StatusNotImplemented,
        gin.H{"http_code": http.StatusNotImplemented, "message": "Feature not yet implemented"})
}
