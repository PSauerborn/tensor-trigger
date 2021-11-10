import uvicorn

from src.config import LISTEN_PORT, LISTEN_ADDRESS, S3_REGION_NAME, S3_BUCKET_NAME
from src.persistence import s3

if __name__ == '__main__':

    # s3.CLIENT.create_bucket(Bucket=S3_BUCKET_NAME, CreateBucketConfiguration={'LocationConstraint': S3_REGION_NAME})

    uvicorn.run('src.app:APP', host=LISTEN_ADDRESS, port=LISTEN_PORT, reload=True)