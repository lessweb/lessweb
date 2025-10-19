from os import environ
from typing import Annotated

from shared.bullmq.bullmq_plugin import Processor
from shared.wxwork_alarm.wxwork_alarm import WxworkAlarm


async def openai_ping_30min(wxwork_alarm: WxworkAlarm) -> Annotated[str, Processor('openai_ping_30min')]:
    if environ.get('ENV') != 'production':
        return ''
    # OPENAI_ALERTING_KEY = 'ocr_task:openai:alerting'
    # try:
    #     await openai_util.ping()
    #     await wxwork_alarm.send_alarm('OpenAI服务已恢复。', alarm_on=False, alarm_key=OPENAI_ALERTING_KEY)
    # except Exception as e:
    #     await wxwork_alarm.send_alarm(f'OpenAI服务异常：{e}', alarm_on=True, alarm_key=OPENAI_ALERTING_KEY)
    return 'OK'
