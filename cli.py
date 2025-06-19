import click
from config_loader import load_config
from backup import mysql_backup, postgres_backup
from s3 import uploader
from cleanup import s3_cleanup
from utils.logger import logger
from utils.email_notifier import EmailNotifier
from datetime import datetime

@click.group()
def cli():
    pass

@cli.command()
@click.option('--db', required=True, type=click.Choice(['postgres', 'mysql']))
@click.option('--count', default=1, help='Number of backups to take')
@click.option('--tables', default=None, help='Comma-separated list of tables')
@click.option('--schema-only', is_flag=True)
@click.option('--data-only', is_flag=True)
@click.option('--compress', is_flag=True)
@click.option('--notify', is_flag=True, help='Send notification after backup completion')
def backup(db, count, tables, schema_only, data_only, compress):
    config = load_config()
    emailer = EmailNotifier(config)

    tables_list = tables.split(',') if tables else None

    for i in range(count):
        date_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        logger.info(f"Starting backup {i+1} of {count}")

        if db == 'postgres':
            file_path = postgres_backup.backup(config, date_str, tables_list, schema_only, data_only, compress)
        elif db == 'mysql':
            file_path = mysql_backup.backup(config, date_str, tables_list, schema_only, data_only, compress)
        else:
            logger.error("Unsupported DB type")
            return

        uploader.upload_to_s3(file_path, config)

    logger.info("All backups completed")
    emailer.send_notification(
        subject="Backup Completed",
        body=f"{count} backups completed for database {db}."
    )

@cli.command()
@click.option('--retention-days', required=True, type=int)
def cleanup(retention_days):
    config = load_config()
    s3_cleanup.cleanup_s3(config, retention_days)

if __name__ == '__main__':
    cli()
