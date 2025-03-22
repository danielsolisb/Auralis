# run_celery.py

from auralis.tasks import celery_app

if __name__ == "__main__":
    # Arrancamos un worker Celery
    celery_app.worker_main(argv=['worker', '-B', '--loglevel=info'])

