## processor

```
from os import environ
from typing import Annotated

from shared.bullmq.bullmq_plugin import Processor
from shared.wxwork_alarm.wxwork_alarm import WxworkAlarm


async def openai_ping_30min(wxwork_alarm: WxworkAlarm) -> Annotated[str, Processor('openai_ping_30min')]:
    if environ.get('ENV') != 'production':
        return ''
    OPENAI_ALERTING_KEY = 'ocr_task:openai:alerting'
    try:
        await openai_util.ping()
        await wxwork_alarm.send_alarm('OpenAI服务已恢复。', alarm_on=False, alarm_key=OPENAI_ALERTING_KEY)
    except Exception as e:
        await wxwork_alarm.send_alarm(f'OpenAI服务异常：{e}', alarm_on=True, alarm_key=OPENAI_ALERTING_KEY)
    return 'OK'
```

## service

```
from commondao import Commondao
from lessweb import Service

from src.entity.task import Task


class TaskService(Service):
    dao: Commondao

    def __init__(self, dao: Commondao) -> None:
        self.dao = dao

    async def refresh_weights(self) -> None:
        tasks = await self.dao.select_all("select * from task where taskStatus in ('created', 'in_progress')", Task)
        for task in tasks:
            ...
            await self.dao.execute_mutation(sql, data)

```