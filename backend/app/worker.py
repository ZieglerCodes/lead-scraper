"""Standalone durable PostgreSQL worker process (run on Render worker service)."""
import logging
import os
import signal
import time

from app import postgres
from app.services.pipeline import demo_search, import_csv

logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'))
log = logging.getLogger('lead-scraper-worker')
stopping = False


def stop(*_):
    global stopping
    stopping = True


def process_one():
    job = postgres.claim_next_job()
    if job is None:
        return False
    owner_id, job_id = job['owner_id'], job['id']
    try:
        if job['kind'] == 'search-demo':
            leads = demo_search(job['query'],job['location'],job['requested'])
            message = 'Synthetic sample data only'
        elif job['kind'] == 'csv-import':
            if job.get('csv_bytes') is None:
                raise ValueError('CSV payload unavailable; please resubmit')
            leads = import_csv(job['csv_bytes'])
            message = 'Imported authorized CSV'
        else:
            raise ValueError('Unknown job type')
        postgres.finish_job(owner_id,job_id,leads,message)
        log.info('Job complete %s; %d records',job_id,len(leads))
    except ValueError as exc:
        log.warning('Job validation failure %s: %s',job_id,exc)
        postgres.fail_job(owner_id,job_id,str(exc))
    except Exception:
        log.exception('Unexpected worker failure for job %s',job_id)
        postgres.fail_job(owner_id,job_id,'Processing failed; see server logs')
    return True


def main():
    if not os.environ.get('DATABASE_URL'):
        raise SystemExit('Refusing worker startup without DATABASE_URL')
    postgres.init_db()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    log.info('Worker started')
    while not stopping:
        try:
            if not process_one():
                time.sleep(2)
        except Exception:
            log.exception('Worker polling error')
            time.sleep(5)


if __name__ == '__main__':
    main()
