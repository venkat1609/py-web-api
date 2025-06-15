import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.tasks.fetch_exchange_rates import fetch_and_store_rates
from app.tasks.queue_upcoming_subscriptions import queue_upcoming_subscriptions

scheduler = AsyncIOScheduler()


def start_scheduler():
    # Fetch every day at 00:00 UTC (can customize to your needs)
    scheduler.start()
    asyncio.create_task(fetch_and_store_rates())  # run immediately
    # asyncio.create_task(queue_upcoming_subscriptions())  # run immediately
    scheduler.add_job(fetch_and_store_rates, IntervalTrigger(hours=12))
    # scheduler.add_job(queue_upcoming_subscriptions, IntervalTrigger(hours=12))
