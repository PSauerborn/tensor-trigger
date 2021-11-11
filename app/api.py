import uvicorn

from src.config import LISTEN_PORT, LISTEN_ADDRESS, S3_REGION_NAME, S3_BUCKET_NAME
from src.persistence import s3

if __name__ == '__main__':

    uvicorn.run('src.app:APP', host=LISTEN_ADDRESS, port=LISTEN_PORT)