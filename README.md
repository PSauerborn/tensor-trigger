# Tensor Trigger - Distributed Tensorflow Event Framework

Tensor Trigger is a distributed REST Tensorflow respository. Tensorflow modules that can be trained and developed locally, and once complete, can be exported to HD5 file(s). Once exported, the HD5 files can be uploaded directly to Tensor Trigger, where they can be stored and managed. Uploaded models can then be ran against provided input vectors via the REST interface in live time. Additionally, large datasets can be uploaded in CSV formats and run asyncronously by the Tensor Worker, which saves the outputed data for later retrieval. Data points can also be streamed directly to the event interface for on-deman model training and learning in live time. Check out <a>https://docs.alpinesoftware.net/tensor-trigger</a> to view the API docs for the current live application.

All components are designed as stateless micro-services, and can be safely scaled both horizontally and vertically. Helm charts are provided for deployment to Kubernetes clusters. Note that access to the container registry at `docker.alpinesoftware.net` is required to run the Helm Charts as they are.

#### Features

The prototype of Tensor Trigger supports the following features

1. Storage and managment of trained Tensorflow models
2. Running models in live-time for both single input vector and input vector batches
3. Async processing of uploaded CSV data files by worker processes
4. Live event stream for online learning

Note that Tensor Trigger is only in protoype stage, and currently only supports models with 1 dimensional input vectors.

#### Tech Stack

Tensor Trigger runs on the following technologies

1. Python and FastAPI for REST interface and workers
2. PostgreSQL and AWS S3 for persistence layer
3. RabbitMQ via AMQP for async event bus
4. Docker + Kubernetes for deployment
5. Github Workflows + Terraform + Helm for release management

### Tensor Trigger: Models

Tensor Trigger models are created with the `POST - /models/new` endpoint. Creating a model requires two inputs

1. Tensorflow model in HD5 format, `base64` encoded
2. Input vector schema in JSON format

The input vector schema defines the format the input vectors need to have in order to be ran against a particular model. The REST interface will subsequently return a `400` response code if a model is ran with an input vector does not match the defined schema. Note that the input vector dimensions are checked against the input layer of the uploaded tensorflow model.

Once a model has been uploaded, it can be retrieved using either the `GET - /models` endpoint or `GET - /models/<model-id>`.

### Tensor Trigger: Events

Once a model has been uploaded, it can be evaluated against a particular input vector via the `POST - /tensor/run` endpoint. The body of the `POST` request must contain the ID of the model, as well as the input vector (see API docs for endpoint and request documentation). Additionally, large datasets can be uploaded in CSV format via the `POST - /tensor/run/async`. The CSV data is uploaded to the S3 layer, and the Tensor Worker then picks up the job, retrieves the CSV file and runs the model on the provided inputs. The model outpus are then stored in JSON format, and can be retrieved using the `GET /job/<job-id>/results` endpoint.
