import boto3
import os
from utils.logger import logger

def upload_to_s3(file_path, config):
    s3_conf = config["s3"]
    bucket = s3_conf["bucket"]
    key = os.path.basename(file_path)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=s3_conf["aws_access_key_id"],
        aws_secret_access_key=s3_conf["aws_secret_access_key"],
        region_name=s3_conf["region"]
    )

    logger.info(f"Uploading {file_path} to S3 bucket {bucket}")
    s3.upload_file(file_path, bucket, key)
    logger.info("Upload successful.")
    s3.close()

def list_backups(config, db):
    s3_conf = config["s3"]
    bucket = s3_conf["bucket"]

    s3 = boto3.client(
        "s3",
        aws_access_key_id=s3_conf["access_key"],
        aws_secret_access_key=s3_conf["secret_key"],
        region_name=s3_conf["region"]
    )

    logger.info(f"Listing backups in S3 bucket {bucket}")
    response = s3.list_objects_v2(Bucket=bucket)
    for obj in response.get('Contents', []):
        if db in obj['Key']:
            print(obj['Key'])
