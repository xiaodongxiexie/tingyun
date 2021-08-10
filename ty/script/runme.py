# -*- coding: utf-8 -*-
# @Author: xiaodong
# @Date  : 2021/8/10

import time
import asyncio
import logging
from datetime import datetime, timedelta

from script.config import URL, URLS_DICT, HEADERS
from script.api import TingYunApi

if __name__ == '__main__':

    logging.basicConfig(format="[%(asctime)s] %(levelname)s %(message)s", level=logging.INFO)

    loop = asyncio.get_event_loop()


    def get_dt(dt: str, i: int):
        end_day = datetime.fromisoformat(dt)
        end_day_with_minute = end_day + timedelta(minutes=i * 30)
        end_day_with_minute = str(end_day_with_minute)
        return end_day_with_minute


    start = time.perf_counter()
    for i in range(45, 49):
        r = loop.run_until_complete(
            TingYunApi(url=URL, urls_dict=URLS_DICT, headers=HEADERS)
                .runme(dt=get_dt("2021-08-02", i), JSESSIONID="F94BA433B6BC77F32825FF286582D28B")
        )

        # 请求次数过多会导致接口数据响应缓慢,这里做下降速
        if i % 3 == 0:
            time.sleep(5)
    end1 = time.perf_counter()
