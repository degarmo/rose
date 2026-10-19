# Restoring the database

There are two independent sources of backups:

1. **Render Postgres backups**: Render's own daily backups and point-in-time
   recovery for the database (the retention depends on the plan).
2. **Nightly encrypted dumps**: every night at 03:15 Chicago, beat runs
   `pg_dump --format=custom`, encrypts the dump with the age public key in
   `BACKUP_AGE_RECIPIENT`, and uploads it to the private bucket as
   `backups/<UTC time>.dump.age`. They are kept 30 days (`BACKUP_RETENTION_DAYS`
   and the bucket's lifecycle rule). The matching **private key is never on the
   server**: it is kept offline by two named people (see the launch checklist).

Media files are not in the database. They are in the buckets, which keep them
independently; restoring the database never touches them.

Always restore into a **new** database first, check it, then switch over.

## A. From a Render backup

1. Render dashboard > the environment's database > Recovery.
2. Choose "Restore to a point in time" (or a daily backup) and **restore into a
   new database** (for example `rose-production-db-restore`). Render creates it.
3. Copy the new database's internal connection string.
4. Check it from a one-off shell on the web service:
   `DATABASE_URL=<new connection string> python manage.py verify_restore`
   (see "Checking a restore" below).
5. Switch over: put the site in maintenance by scaling the web, worker and beat
   services to 0, point the environment's `DATABASE_URL` (Blueprint or service
   settings) at the new database, deploy, scale back up.
6. Keep the old database for a week before deleting it.

## B. From a nightly encrypted dump

On a trusted computer (never the server), with `pg_restore` 16, Python 3.12 and
`pip install pyrage boto3` (or the `age` command-line tool):

1. Download the dump from the private bucket, for example with the AWS CLI:
   `aws s3 cp s3://<private-bucket>/backups/<file>.dump.age . --endpoint-url <S3_ENDPOINT_URL>`
   using a key with read access to the private bucket.
2. Decrypt with the offline private key:
   `python scripts/decrypt_backup.py <file>.dump.age --identity age-key.txt --output restore.dump`
   (or `age --decrypt -i age-key.txt -o restore.dump <file>.dump.age`).
3. Create an empty database (Render: create a new Postgres in the same
   environment; locally: `createdb rose_restore`).
4. Restore:
   `pg_restore --no-owner --no-privileges --exit-on-error -d <connection string> restore.dump`
5. Check it: `DATABASE_URL=<connection string> python manage.py verify_restore`.
6. Switch over as in A.5 and A.6.
7. Delete `restore.dump` and the decrypted copy securely when done: it holds
   member data in the clear.

## Checking a restore

```sh
# On the source, before backing up (optional, gives an exact comparison):
python manage.py verify_restore --write-counts before.json
# On the restored database:
python manage.py verify_restore --counts-file before.json
```

`verify_restore` is read-only. It confirms every migration is applied, compares
row counts for every table, checks that every profile has its account, every
payment its membership and every feed image its file in storage, and calls the
public endpoints, a member's own membership and the feed as restored users
(without creating sessions). Any problem makes it exit with an error.

## Drill: 18 October 2026

A full drill was run locally against the development database (seeded, 44
tables, 566 rows):

1. Row counts recorded with `verify_restore --write-counts`.
2. `run_backup()` with a freshly generated age key: a 175 KB
   `backups/<time>.dump.age` file starting `age-encryption.org/v1`.
3. Decrypted with `scripts/decrypt_backup.py` and the offline key (output
   starts with the `PGDMP` signature).
4. Restored with `pg_restore --exit-on-error` into a brand-new database.
5. `verify_restore --counts-file`: migrations complete, all 44 tables match the
   source row for row, integrity checks pass, the application answers as
   restored users.
6. The site was then served from the restored database and the browser smoke
   tests (age gate, contact, privacy headers, third-party requests and
   accessibility on every public page) ran against it: 44 passed.

Repeat the drill every quarter, and after any change to the backup task.
