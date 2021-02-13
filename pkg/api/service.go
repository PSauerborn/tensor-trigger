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
    router.GET("/tensor-trigger/model/:modelId", utils.S3DownloadMiddelware(s3Config), downloadModelHandler)
    // create routes to handle model uploading and triggering
    router.POST("/tensor-trigger/model", utils.S3UploadMiddelware(s3Config), createModelHandler)
    router.PUT("/tensor-trigger/model/:modelId", utils.S3UploadMiddelware(s3Config), uploadModelHandler)
    router.PUT("/tensor-trigger/models/trigger/:modelId", triggerModelHandler)
    return router
}

// function to serve health check
func healthCheckHandler(ctx *gin.Context) {
    log.Info("received request for health check handler")
    ctx.JSON(http.StatusOK,
        gin.H{"http_code": http.StatusOK, "message": "Service running"})
}

type ModelMetadata struct {
    ModelName        string    `json:"model_name" binding:"required"`
    ModelDescription string    `json:"model_description"`
    ModelId          uuid.UUID `json:"model_id"`
    Created          time.Time `json:"created"`
}

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
    })

    // upload metadata to S3 bucket
    key := fmt.Sprintf("metadata/%s", modelId.String())
    if err := uploader.UploadFile("tensor-trigger", key, modelJson); err != nil {
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

    // get S3 uploader from context and upload file to S3 server
    uploader, _ := ctx.MustGet("s3_uploader").(*utils.S3Uploader)
    key := fmt.Sprintf("models/%s", modelId.String())
    if err := uploader.UploadFile("tensor-trigger", key, body); err != nil {
        log.Error(fmt.Errorf("unable to upload file to S3 server: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }

    ctx.JSON(http.StatusOK,
        gin.H{"http_code": http.StatusOK, "message": "Successfully uploaded file"})
}

// function to retrieve list of models
func getModelsMetadataHandler(ctx *gin.Context) {
    log.Info("received request to retrieve tensorflow models")

    downloader, _ := ctx.MustGet("s3_downloader").(*utils.S3Downloader)
    files, err := downloader.GetAllObjectsInBucketAsync("tensor-trigger")
    if err != nil {
        log.Error(fmt.Errorf("unable to retrieve metadata files: %+v", err))
        ctx.JSON(http.StatusInternalServerError,
            gin.H{"http_code": http.StatusInternalServerError, "message": "Internal server error"})
        return
    }

    models := []ModelMetadata{}
    for _, file := range(files) {
        var model ModelMetadata
        if err := json.Unmarshal(file, &model); err != nil {
            log.Warn(fmt.Errorf("found invalid JSON model in S3 bucket: %+v", err))
            continue
        } else {
            models = append(models, model)
        }
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

    // get download from request context and download file to bytes array
    downloader, _ := ctx.MustGet("s3_downloader").(*utils.S3Downloader)
    key := fmt.Sprintf("models/%s", modelId.String())
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
