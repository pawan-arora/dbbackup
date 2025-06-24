import boto3
import datetime
from utils.logger import logger

def cleanup_s3(config, retention_days):
    s3_conf = config['s3']
    session = boto3.Session(
        aws_access_key_id=s3_conf['aws_access_key_id'],
        aws_secret_access_key=s3_conf['aws_secret_access_key'],
        region_name=s3_conf['region']
    )
    s3 = session.client('s3')

    bucket = s3_conf['bucket']
    logger.info(f"Cleaning up files older than {retention_days} days from {bucket}")

    response = s3.list_objects_v2(Bucket=bucket)
    if 'Contents' not in response:
        logger.info("No files found.")
        return

    now = datetime.datetime.now(datetime.timezone.utc)

    for obj in response['Contents']:
        last_modified = obj['LastModified']
        age = (now - last_modified).days
        if age >= retention_days:
            logger.info(f"Deleting {obj['Key']} (age: {age} days)")
            s3.delete_object(Bucket=bucket, Key=obj['Key'])
