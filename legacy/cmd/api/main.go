
package main

import (
    "fmt"
    "strconv"

    "github.com/aws/aws-sdk-go/aws"
    "github.com/aws/aws-sdk-go/aws/credentials"

    "github.com/PSauerborn/tensor-trigger/pkg/api"
    "github.com/PSauerborn/tensor-trigger/pkg/utils"
)

var (
    cfg = utils.NewConfigMapWithValues(
        map[string]string{
            "listen_address": "0.0.0.0",
            "listen_port": "10776",
            "s3_url": "http://192.168.99.100:8080",
            "s3_access_key_id": "accessKey1",
            "s3_secret_access_key": "verySecretKey1",
            "s3_region": "us-east-1",
        },
    )
)

func generateS3Config() *aws.Config {
    // generate new set of static credentials for s3 server
    creds := credentials.NewStaticCredentials(cfg.Get("s3_access_key_id"),
        cfg.Get("s3_secret_access_key"), "")
    return &aws.Config{
        Endpoint: aws.String(cfg.Get("s3_url")),
        Credentials: creds,
        Region: aws.String(cfg.Get("s3_region")),
        S3ForcePathStyle: aws.Bool(true),
    }
}

func main() {

    s3Config := generateS3Config()
    // generate s3 configuration and create initial buckets. note that
    // if the bucket already exists, creation of the bucket is skipped
    neededBuckets := []string{"tensor-trigger"}
    if err := utils.CreateS3Buckets(neededBuckets, s3Config); err != nil {
        panic("unable to create/validate needed s3 bucket")
    }

    port, err := strconv.Atoi(cfg.Get("listen_port"))
    if err != nil {
        panic(err)
    }
    // generate new instance of API gateway with config settings
    router := api.New(s3Config)
    router.Run(fmt.Sprintf("%s:%d", cfg.Get("listen_address"), port))
}