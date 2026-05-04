"""
Background scheduler service for scheduled container actions.
"""
import logging
import asyncio
from datetime import datetime
from app.db import get_session
from app.db.models import Schedule
from app.services.docker_monitor import get_docker_monitor

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # Check every minute


async def run_scheduler():
    """Run the scheduler loop."""
    logger.info("Scheduler started")
    
    while True:
        try:
            await check_and_execute_schedules()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)


async def check_and_execute_schedules():
    """Check all enabled schedules and execute if time matches."""
    session = get_session()
    try:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A")  # e.g., "Monday"
        
        schedules = session.query(Schedule).filter(Schedule.enabled == 1).all()
        
        for schedule in schedules:
            if schedule.time == current_time:
                await execute_schedule_action(schedule.container_id, schedule.action)
                logger.info(f"Executed schedule {schedule.id}: {schedule.action} for {schedule.container_id}")
    finally:
        session.close()


async def execute_schedule_action(container_id: str, action: str):
    """Execute the specified action on a container."""
    monitor = get_docker_monitor()
    
    if action == "start":
        monitor.start_container(container_id)
    elif action == "stop":
        monitor.stop_container(container_id)
    elif action == "restart":
        monitor.restart_container(container_id)