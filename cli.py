#!/usr/bin/env python3

import click
import threading
import os
from datetime import datetime
from config_loader import load_config
from backup import mysql_backup, postgres_backup, incremental_backup
from s3 import uploader
from cleanup import s3_cleanup
from utils.logger import logger
from utils.email_notifier import EmailNotifier
from scheduler import Scheduler
from state_manager import StateManager
from utils.mysql_log_check import is_binary_logging_enabled
from utils.postgres_log_check import is_wal_archiving_enabled

# Globals
STATE_FILE = "schedules.json"
LOG_FILE = "logs/backup.log"

state_manager = StateManager()
scheduler = Scheduler(state_manager)

def run_backup(config, db, count, tables, schema_only, data_only, compress, notify_email, incremental):
    tables_list = tables.split(',') if tables else None
    emailer = EmailNotifier()
    uploaded_files = []
    backup_success = True

    for i in range(count):
        try:
            date_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            logger.info(f"Starting backup {i + 1} of {count} for {db}")

            # Incremental logic
            if incremental:
                if db == 'mysql':
                    if not is_binary_logging_enabled(config):
                        raise Exception("Binary logging is not enabled for MySQL.")
                    file_path = incremental_backup.mysql_incremental_backup(config, date_str)
                elif db == 'postgres':
                    if not is_wal_archiving_enabled(config):
                        raise Exception("WAL archiving is not enabled for PostgreSQL.")
                    file_path = incremental_backup.postgres_incremental_backup(config, date_str)
                else:
                    raise Exception("Unsupported DB type for incremental backup")
            else:
                if db == 'mysql':
                    file_path = mysql_backup.backup(config, date_str, tables_list, schema_only, data_only, compress)
                elif db == 'postgres':
                    file_path = postgres_backup.backup(config, date_str, tables_list, schema_only, data_only, compress)
                else:
                    raise Exception("Unsupported DB type")

            # Upload
            uploader.upload_to_s3(file_path, config)
            uploaded_files.append(file_path)
            logger.info(f"Uploaded backup file {file_path} to S3")

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            backup_success = False

        finally:
            # Always clean up local backup file
            try:
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted local file: {file_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete local file: {cleanup_err}")

    if backup_success:
        logger.info("All backups and uploads completed successfully.")
    else:
        logger.warning("Backup process completed with errors.")

    if notify_email:
        t = threading.Thread(
            target=emailer.notify_in_background,
            args=(config, notify_email, uploaded_files, db, count, backup_success)
        )
        t.daemon = True
        t.start()

@click.group()
def cli():
    pass

@cli.command()
@click.option('--db', required=True, type=click.Choice(['postgres', 'mysql']))
@click.option('--count', default=1, help='Number of backups to take immediately')
@click.option('--tables', default=None, help='Comma-separated list of tables')
@click.option('--schema-only', is_flag=True)
@click.option('--data-only', is_flag=True)
@click.option('--compress', is_flag=True)
@click.option('--notify', default=None, help='Email address to notify after upload completes')
@click.option('--incremental', is_flag=True, help='Perform an incremental backup')
def backup(db, count, tables, schema_only, data_only, compress, notify, incremental):
    """Take immediate backups"""
    config = load_config()
    run_backup(config, db, count, tables, schema_only, data_only, compress, notify, incremental)

@cli.command()
@click.option('--db', required=True, type=click.Choice(['postgres', 'mysql']))
@click.option('--count', required=True, type=int, help='Number of backups to generate')
@click.option('--gap', required=True, type=int, help='Gap between backups in days')
@click.option('--tables', default=None, help='Comma-separated list of tables')
@click.option('--schema-only', is_flag=True)
@click.option('--data-only', is_flag=True)
@click.option('--compress', is_flag=True)
@click.option('--notify', default=None, help='Email address to notify after each backup')
def schedule(db, count, gap, tables, schema_only, data_only, compress, notify):
    """Schedule recurring backups"""
    scheduler.add_schedule(
        db=db,
        count=count,
        gap=gap,
        tables=tables,
        schema_only=schema_only,
        data_only=data_only,
        compress=compress,
        notify=notify
    )
    click.echo(f"Scheduled {count} backups for {db} every {gap} day(s).")

@cli.command()
def status():
    """Show all active backup schedules"""
    schedules = scheduler.get_active_schedules()
    if not schedules:
        click.echo("No active schedules.")
        return
    for db, details in schedules.items():
        click.echo(f"DB: {db}")
        click.echo(f"  Count: {details['count']}")
        click.echo(f"  Gap (days): {details['gap']}")
        click.echo(f"  Backups completed: {details['completed']}")
        click.echo(f"  Tables: {details['tables']}")
        click.echo(f"  Schema only: {details['schema_only']}")
        click.echo(f"  Data only: {details['data_only']}")
        click.echo(f"  Compress: {details['compress']}")
        click.echo(f"  Notify email: {details['notify']}")

@cli.command()
@click.option('--db', required=True, type=click.Choice(['postgres', 'mysql']))
def cancel(db):
    """Cancel active backup schedule for a database"""
    if scheduler.cancel_schedule(db):
        click.echo(f"Cancelled schedule for {db}.")
    else:
        click.echo(f"No active schedule found for {db}.")

@cli.command()
@click.option('--lines', default=20, help='Number of log lines to show')
def logs(lines):
    """Show last N lines of backup logs"""
    if not os.path.exists(LOG_FILE):
        click.echo("No logs found.")
        return
    with open(LOG_FILE, 'r') as f:
        all_lines = f.readlines()
    for line in all_lines[-lines:]:
        click.echo(line.rstrip())

@cli.command()
@click.option('--retention-days', required=True, type=int, help="Delete backups older than N days from S3")
def cleanup(retention_days):
    """Cleanup old backups from S3"""
    config = load_config()
    logger.info(f"Starting cleanup for backups older than {retention_days} days")
    s3_cleanup.cleanup_s3(config, retention_days)
    logger.info(f"Cleanup completed.")

@cli.command()
@click.option('--db', type=click.Choice(['postgres', 'mysql']), default=None, help='Filter backups by DB type')
def list_backups(db):
    """List all backups uploaded to S3"""
    config = load_config()
    backups = uploader.list_backups(config, db_filter=db)

    if not backups:
        click.echo("No backups found.")
        return

    click.echo(f"Backups in S3 ({config['s3']['bucket']}):\n")
    for backup in sorted(backups, key=lambda x: x['last_modified'], reverse=True):
        size_kb = backup['size'] / 1024
        timestamp = backup['last_modified'].strftime('%Y-%m-%d %H:%M:%S')
        click.echo(f"- {backup['key']} | Uploaded at: {timestamp} | Size: {size_kb:.2f} KB")

if __name__ == '__main__':
    cli()
