import logging
import sys
import json
import os
import subprocess
from time import strftime, gmtime

import boto3
import backoff

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()


class DbUnavailableError(Exception):
    pass


def main():
    SOURCE_DB_IDENTIFIER = os.environ['SOURCE_DB_IDENTIFIER']
    SOURCE_DB_DATABASE = os.environ['SOURCE_DB_DATABASE']
    CREDENTIALS_SECRET = os.environ['CREDENTIALS_SECRET']

    logger.info(f'Starting PITR for {SOURCE_DB_IDENTIFIER}..')
    source_db_network_config = get_db_instance_network_config(SOURCE_DB_IDENTIFIER)
    pitr_identifier = do_pitr(SOURCE_DB_IDENTIFIER, source_db_network_config)
    logger.info(f'PITR instance ({pitr_identifier}) created.')

    logger.info('Waiting for PITR instance to become available..')
    check_if_db_available(pitr_identifier)
    logger.info('PITR instance available!')

    source_endpoint = get_db_instance_endpoint(SOURCE_DB_IDENTIFIER)
    pitr_endpoint = get_db_instance_endpoint(pitr_identifier)
    db_credentials = get_secret_value(CREDENTIALS_SECRET)

    logger.info('Starting pg_dump backup from PITR instance..')
    backup_path = run_pg_dump(pitr_endpoint, SOURCE_DB_DATABASE, db_credentials)
    logger.info(f'Backup (pg_dump) successful at path {backup_path}!')

    logger.info(f'Starting pg_restore from {backup_path} to instance {SOURCE_DB_IDENTIFIER}..')
    run_pg_restore(source_endpoint, SOURCE_DB_DATABASE,
                   db_credentials, backup_path)
    logger.info(f'Restore (pg_restore) successful at instance {SOURCE_DB_IDENTIFIER}!')

    logger.info(f'Cleaning up..')
    os.remove(backup_path)
    delete_instance(pitr_identifier)
    logger.info(f'Clean up successful, all done!')


def get_db_instance_network_config(db_identifier: str) -> dict:
    """
    Function which will fetch current network configuration for given RDS DB instance.

    :param db_identifier: RDS instance identifier
    :return: relevant network configuration
    """
    client = boto3.client('rds')

    instance = client.describe_db_instances(DBInstanceIdentifier=db_identifier)['DBInstances'][0]

    return {
        'subnet_group': instance['DBSubnetGroup']['DBSubnetGroupName'],
        'vpc_security_groups': [
            x['VpcSecurityGroupId'] for x in instance['VpcSecurityGroups']
        ],
        'publicly_accessible': instance['PubliclyAccessible']
    }


def do_pitr(source_db_identifier: str, network_config: dict) -> str:
    """
    Function which will start Point-in-Time Recovery instance from given RDS DB instance.

    :param source_db_identifier: RDS instance identifier
    :param network_config: relevant network configuration
    :return: PITR instance identifier
    """
    client = boto3.client('rds')

    target_db_identifier = f'{source_db_identifier}-pitr'

    return client.restore_db_instance_to_point_in_time(
        SourceDBInstanceIdentifier=source_db_identifier,
        TargetDBInstanceIdentifier=target_db_identifier,
        UseLatestRestorableTime=True,  # Can be replaced with `RestoreToTime` for exact time,
        VpcSecurityGroupIds=network_config['vpc_security_groups'],
        DBSubnetGroupName=network_config['subnet_group'],
        PubliclyAccessible=network_config['publicly_accessible']
    )['DBInstance']['DBInstanceIdentifier']


@backoff.on_exception(backoff.constant, DbUnavailableError, interval=30)
def check_if_db_available(db_identifier: str) -> None:
    """
    Function which checks if given RDS DB instance is available.

    :param db_identifier: RDS instance identifier
    :raises DbUnavailableError: raised if RDS DB instance is not available
    :return:
    """
    client = boto3.client('rds')
    status = client.describe_db_instances(DBInstanceIdentifier=db_identifier)['DBInstances'][0]['DBInstanceStatus']

    if status != 'available':
        err_msg = f'DB in status {status}.'
        raise DbUnavailableError(err_msg)


def get_db_instance_endpoint(db_identifier: str) -> str:
    """
    Function which returns endpoint address for given RDS DB instance.

    :param db_identifier: RDS instance identifier
    :return: RDS instance endpoint address
    """
    client = boto3.client('rds')

    return client.describe_db_instances(DBInstanceIdentifier=db_identifier)['DBInstances'][0]['Endpoint']['Address']


def get_secret_value(secret_name: str) -> dict:
    """
    Function which returns un-serialized value of given Secrets Manager secret.

    :param secret_name: Name of the Secrets Manager secret
    :return: un-serialized value of the secret
    """
    client = boto3.client('secretsmanager')

    return json.loads(client.get_secret_value(SecretId=secret_name)['SecretString'])


def run_pg_dump(host: str, database: str, credentials: dict) -> str:
    """
    Function which will start pg_dump backup for given database on given PostgreSQL host.

    :param host: hostname of the host
    :param database: selected database to backup
    :param credentials: database credentials
    :return: path of the created backup
    """
    backup_path = "/tmp/backup-{}-{}.sql.gz".format(database, strftime("%Y-%m-%d_%H%M%S", gmtime()))

    with open(backup_path, 'w') as backup:
        completed_process = subprocess.run(
            [
                '/usr/bin/pg_dump',
                '-h', host,
                '-U', credentials['username'],
                '-Fc',
                '-c',
                '-O',
                '--if-exists', database
            ],
            stdout=backup,
            env={'PGPASSWORD': credentials['password']})

    try:
        completed_process.check_returncode()
        return backup_path
    except subprocess.CalledProcessError as e:
        logger.info('pg_dump failed!')
        exit(e)


def run_pg_restore(host: str, database: str, credentials: dict, backup_path: str) -> None:
    """
    Function which will start pg_dump backup for given database on given PostgreSQL host.

    :param host: hostname of the host
    :param database: selected database to backup
    :param credentials: database credentials
    :param backup_path: path of the backup to restore
    :return:
    """
    with open(backup_path, 'r') as backup:
        completed_process = subprocess.run(
            [
                '/usr/bin/pg_restore',
                '-h', host,
                '-U', credentials['username'],
                '-c',
                '-d', database
            ],
            stdin=backup,
            env={'PGPASSWORD': credentials['password']})

    try:
        completed_process.check_returncode()
    except subprocess.CalledProcessError as e:
        logger.info('pg_dump failed!')
        exit(e)


def delete_instance(instance_id: str) -> dict:
    """
    Function which will delete given RDS DB instance.

    :param instance_id: RDS instance identifier
    :return: AWS API delete_db_instance response
    """
    client = boto3.client('rds')

    return client.delete_db_instance(
        DBInstanceIdentifier=instance_id,
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True
    )


if __name__ == '__main__':
    main()
