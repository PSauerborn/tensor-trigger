package utils

import (
    "os"
    "fmt"
    "bytes"
    "sync"
    "errors"

    "github.com/gin-gonic/gin"
    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/awserr"
    "github.com/aws/aws-sdk-go/service/s3"
    "github.com/aws/aws-sdk-go/service/s3/s3manager"
    "github.com/aws/aws-sdk-go/aws/session"
    log "github.com/sirupsen/logrus"
)

var (
    // define custom errors
    ErrKeyAlreadyExists = errors.New("Key already exists in specified bucket")
    ErrKeyDoesNotExist  = errors.New("Key does not exist in specified bucket")
)


// function to create list of s3 buckets. if the specified
// bucket already exists, or a bucket with the given name
// is already owned, creation of the bucket is skipped
func CreateS3Buckets(buckets []string, config *aws.Config) error {
    log.Info(fmt.Sprintf("creating initial buckets %+v", buckets))
    // create new service connection using configuration
    svc := s3.New(session.New(config))
    for _, bucket := range(buckets) {
        // generate creation options for bucket
        bucketOpts := &s3.CreateBucketInput{
            Bucket: aws.String(bucket),
        }
        // create bucket and handle any errors
        _, err := svc.CreateBucket(bucketOpts)
        if err != nil {
            if aerr, ok := err.(awserr.Error); ok {
                switch aerr.Code() {
                case s3.ErrCodeBucketAlreadyExists, s3.ErrCodeBucketAlreadyOwnedByYou:
                    log.Warn(fmt.Sprintf("unable to create bucket %s: skipping...", bucket))
                    continue
                default:
                    log.Error(fmt.Errorf("unable to create bucket %s: %+v", bucket, err))
                    return err
                }
            } else {
                log.Error(fmt.Errorf("unable to create bucket %s: %+v", bucket, err))
                return err
            }
        }
    }
    return nil
}

// function to download a file to memory from a S3 server
// given a particular bucket name and key
func ListBucketKeys(bucket string, config *aws.Config) ([]string, error) {
    log.Info(fmt.Sprintf("downloading s3 file(s) in bucket %s", bucket))
    // create new service connection using configuration
    svc := s3.New(session.New(config))
    // generate download opts and download file
    listOpts := &s3.ListObjectsInput{
        Bucket: aws.String(bucket),
    }
    // download file and save to buffer
    results, err := svc.ListObjects(listOpts)
    if err != nil {
        log.Error(fmt.Errorf("unable to download s3 file: %+v", err))
        return nil, err
    }

    keys := []string{}
    for _, object := range(results.Contents) {
        keys = append(keys, *object.Key)
    }
    return keys, nil
}

func KeyExistsInBucket(bucket, key string, config *aws.Config) (bool, error) {
    keys, err := ListBucketKeys(bucket, config)
    if err != nil {
        log.Error(fmt.Errorf("unable to retrieve current keys in bucket: %+v", err))
        return false, err
    }

    for _, k := range(keys) {
        if key == k {
            return true, nil
        }
    }
    return false, nil
}

// gin-gonic middleware used to inject a S3Downloader into
// the request context. the S3Downloader interface is used
// to download files from a given S3 server instance
func S3DownloadMiddelware(config *aws.Config) gin.HandlerFunc {
    return func(ctx *gin.Context) {
        // create new instance of downloader and save to context
        downloader := NewS3Downloader(config)
        ctx.Set("s3_downloader", downloader)
        ctx.Next()
    }
}

// gin-gonic middleware used to inject a S3Uploader into
// the request context. the S3Uploader interface is used
// to upload files to a given S3 server instance
func S3UploadMiddelware(config *aws.Config) gin.HandlerFunc {
    return func(ctx *gin.Context) {
        // create new instance of uploader and save to context
        uploader := NewS3Uploader(config)
        ctx.Set("s3_uploader", uploader)
        ctx.Next()
    }
}


type S3Uploader struct {
    Manager *s3manager.Uploader
    Config  *aws.Config
}

// function to generate new uploader instance
// using a given S3 config
func NewS3Uploader(config *aws.Config) *S3Uploader {
    return &S3Uploader{
        Manager: s3manager.NewUploader(session.New(config)),
        Config: config,
    }
}

// function to upload a file to a configured S3 server
// with a given bucket name and key
func(uploader *S3Uploader) UploadFile(bucket, key string, data []byte, overwrite bool) error {
    log.Info(fmt.Sprintf("uploading s3 file to %s:%s", bucket, key))
    // check if key already exists in S3 bucket
    exists, err := KeyExistsInBucket(bucket, key, uploader.Config)
    if err != nil {
        log.Error(fmt.Errorf("unable to check current keys in bucket: %+v", err))
        return err
    // only overwrite existing key if specified explicitely
    } else if exists && !overwrite {
        log.Error(fmt.Errorf("unable to upload file: key %s already exists", key))
        return ErrKeyAlreadyExists
    }

    // generate new storage opts and upload to s3
    storageOpts := &s3manager.UploadInput{
        Bucket: aws.String(bucket),
        Key: aws.String(key),
        Body: bytes.NewReader(data),
    }
    // upload file to s3 storage and return any errors
    if _, err := uploader.Manager.Upload(storageOpts); err != nil {
        if aerr, ok := err.(awserr.Error); ok {
            switch aerr.Code() {
            case s3.ErrCodeNoSuchKey:
                log.Warn(fmt.Sprintf("unable to upload S3 file: key %s already exists", key))
                return ErrKeyDoesNotExist
            default:
                log.Error(fmt.Errorf("unable to upload file to S3 bucket %s:%s: %+v", bucket, key, err))
                return err
            }
        } else {
            log.Error(fmt.Errorf("unable to upload file to S3 bucket %s:%s: %+v", bucket, key, err))
            return err
        }
    }
    return nil
}


type S3Downloader struct {
    Manager *s3manager.Downloader
    Config  *aws.Config
}

// function to generate new downloader
func NewS3Downloader(config *aws.Config) *S3Downloader {
    return &S3Downloader{
        Manager: s3manager.NewDownloader(session.New(config)),
        Config: config,
    }
}

// function to download a file to disk from a S3 server
// given a particular bucket name and key
func(downloader *S3Downloader) DownloadFileToDisk(bucket, key, fileName string) (*os.File, error) {
    log.Info(fmt.Sprintf("downloading s3 file from %s:%s", bucket, key))
    // open new file for destination path
    f, err := os.Open(fileName)
    if err != nil {
        log.Error(fmt.Errorf("unable to open file %s: %+v", fileName, err))
        return nil, err
    }
    // generate download opts and download file
    downloadOpts := &s3.GetObjectInput{
        Bucket: aws.String(bucket),
        Key: aws.String(key),
    }
    if _, err := downloader.Manager.Download(f, downloadOpts); err != nil {
        if aerr, ok := err.(awserr.Error); ok {
            switch aerr.Code() {
            case s3.ErrCodeNoSuchKey:
                log.Warn(fmt.Sprintf("unable to download S3 file: key %s does not exist", key))
                return nil, ErrKeyDoesNotExist
            default:
                log.Error(fmt.Errorf("unable to download file: S3 file %s:%s: %+v", bucket, key, err))
                return nil, err
            }
        } else {
            log.Error(fmt.Errorf("unable to download file: S3 file %s:%s: %+v", bucket, key, err))
            return nil, err
        }
    }
    return f, nil
}

// function to download a file to memory from a S3 server
// given a particular bucket name and key
func(downloader *S3Downloader) DownloadFileToBytes(bucket, key string) ([]byte, error) {
    log.Info(fmt.Sprintf("downloading s3 file from %s:%s", bucket, key))
    // create buffer for in-memory file storage
    buffer := &aws.WriteAtBuffer{}
    // generate download opts and download file
    downloadOpts := &s3.GetObjectInput{
        Bucket: aws.String(bucket),
        Key: aws.String(key),
    }
    // download file and save to buffer
    if _, err := downloader.Manager.Download(buffer, downloadOpts); err != nil {
        if aerr, ok := err.(awserr.Error); ok {
            switch aerr.Code() {
            case s3.ErrCodeNoSuchKey:
                log.Warn(fmt.Sprintf("unable to download S3 file: key %s does not exist", key))
                return nil, ErrKeyDoesNotExist
            default:
                log.Error(fmt.Errorf("unable to download file: S3 file %s:%s: %+v", bucket, key, err))
                return nil, err
            }
        } else {
            log.Error(fmt.Errorf("unable to download file: S3 file %s:%s: %+v", bucket, key, err))
            return nil, err
        }
    }
    return buffer.Bytes(), nil
}

// function used to download all files in a given S3 bucket
// note that the keys first need to be retrieved for the
// specified bucket, before the files are downloaded, with
// each download occuring over a separate go routine
func(downloader *S3Downloader) GetAllObjectsInBucketAsync(bucket string) ([][]byte, error) {
    log.Info(fmt.Sprintf("getting all files in bucket %s", bucket))

    files := [][]byte{}
    // get all keys in specified bucket
    keys, err := ListBucketKeys(bucket, downloader.Config)
    if err != nil {
        log.Error(fmt.Errorf("unable to retrieve keys in bucket %s: %+v", bucket, err))
        return files, err
    }

    var wg sync.WaitGroup
    // iterate over keys and download each file on go routine
    for _, key := range(keys) {
        wg.Add(1)
        go func(key string) {
            file, err := downloader.DownloadFileToBytes(bucket, key)
            if err != nil {
                log.Error(fmt.Errorf("unable to download file for %s:%s: %+v", bucket, key, err))
            } else {
                files = append(files, file)
            }
            wg.Done()
        }(key)
    }
    wg.Wait()
    return files, nil
}