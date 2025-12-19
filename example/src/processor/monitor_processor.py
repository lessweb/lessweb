import logging
from typing import Annotated

from commondao import Commondao

from shared.bullmq_plugin import Processor


async def database_health_check_2h(dao: Commondao) -> Annotated[str, Processor('database_health_check_2h')]:
    """Every 2 hours execute SELECT 1 to check database connectivity"""
    result = await dao.execute_query('SELECT 1 as status')
    logging.info(f"Database health check completed: {result}")
    return 'OK'
