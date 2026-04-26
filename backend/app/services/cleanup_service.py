import logging
from datetime import datetime, timedelta
from sqlalchemy import delete
from app.db import get_session
from app.db.models import Metric
from app.core.config import get_config

logger = logging.getLogger(__name__)

_cleanup_interval_seconds = 86400


def get_cleanup_interval() -> int:
    return _cleanup_interval_seconds


async def cleanup_old_metrics() -> int:
    config = get_config()
    ttl_days = config.database.metrics_ttl_days
    cutoff = datetime.utcnow() - timedelta(days=ttl_days)

    session = get_session()
    try:
        result = session.execute(delete(Metric).where(Metric.timestamp < cutoff))
        session.commit()
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} metrics older than {ttl_days} days")
        return deleted_count
    except Exception as e:
        logger.error(f"Error during metrics cleanup: {e}")
        session.rollback()
        return 0
    finally:
        session.close()


async def run_periodic_cleanup():
    while True:
        await cleanup_old_metrics()
        import asyncio

        await asyncio.sleep(get_cleanup_interval())
