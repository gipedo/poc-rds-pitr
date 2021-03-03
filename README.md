# RDS Point-in-Time Recovery PoC

## Overview

The purpose of this repo is to help with automation of disaster recovery strategy using [RDS PITR](https://rdspg.workshop.aws/lab4-backup/task5.html) process.

High-level tasks:
1. Start PITR by creating a new PITR DB instance
2. Run `pg_dump` on the PITR DB instance
3. Run `pg_restore` on original instance
4. Destroy PITR DB Instance

## Implementation
The architecture of PoC consists of two moving parts:
1. **CDK** - lab infrastructure
2. **Python + Docker** - python script which is doing all the heavy-lifting packaged in the Docker image

### CDK
Before PITR can be started, lab infrastructure has to be deployed. The infrastructure consists of:
1. VPC
2. Secrets Manager DB secret
3. DB Security Group
4. RDS PostgreSQL instance

> IMPORTANT: For lab purpose the database will be in **public** subnet and have public accessible, this is very dangerous and should NOT be used in production!

#### CDK Deployment
Requirements:
1. Valid AWS credentials
2. Nodejs

Following steps are required in order to deploy the lab infrastructure:
```shell
# Add CIDR which DB SG will trust
echo 'TRUSTED_INGRESS_DB_CIDR=<your_public_ip>/32' > .env
# Install the dependencies
npm i
# Deploy the infrastructure
cdk deploy
```

### Python + Docker
Once lab infrastructure is deployed, PITR can be executed.
  
In order to be able to see the results go ahead and modify something in the database (create schemas, tables, rows, ..) and create a manual snapshot.
Once snapshot is created, delete some of those changes, so the actual DB state differs from one in the snapshot.

#### PITR execution
**Because lab DB is public PITR can be executed from local workstation, but for production usage its definetely recommended running PITR within VPC from a container.**

Requirements:
1. Valid AWS credentials
2. Docker

Following steps are required in order to do PITR:
```shell
cd pitr

# Build the pitr docker image
docker build -t pitr .

# Run the docker pitr image
docker run \
-v $HOME/.aws:/root/.aws \
-e SOURCE_DB_IDENTIFIER=<source_db_identifier> \
-e SOURCE_DB_DATABASE=<name_of_database> \
-e CREDENTIALS_SECRET=<name_of_db_credentials_secret> \
pitr
```

##### Sample output
```shell
docker run -v $HOME/.aws:/root/.aws -e SOURCE_DB_IDENTIFIER=pb19uk56bmxfkaf -e SOURCE_DB_DATABASE=PocRdsPitrStack -e CREDENTIALS_SECRET=BackendDbSecret6CDFECCB-eT8IEZ0S3pGP pitr

INFO:root:Starting PITR for pb19uk56bmxfkaf..
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:root:PITR instance (pb19uk56bmxfkaf-pitr) created.
INFO:root:Waiting for PITR instance to become available..
INFO:backoff:Backing off check_if_db_available(...) for 12.1s (DbUnavailableError: DB in status creating.)
INFO:backoff:Backing off check_if_db_available(...) for 10.7s (DbUnavailableError: DB in status creating.)
<truncated..>
INFO:backoff:Backing off check_if_db_available(...) for 26.5s (DbUnavailableError: DB in status modifying.)
INFO:root:PITR instance available!
INFO:root:Starting pg_dump backup from PITR instance..
INFO:root:Backup (pg_dump) successful at path /tmp/backup-PocRdsPitrStack-2021-03-02_160844.sql.gz!
INFO:root:Starting pg_restore from /tmp/backup-PocRdsPitrStack-2021-03-02_160844.sql.gz to instance pb19uk56bmxfkaf..
INFO:root:Restore (pg_restore) successful at instance pb19uk56bmxfkaf!
INFO:root:Cleaning up..
INFO:root:Clean up successful, all done!
```