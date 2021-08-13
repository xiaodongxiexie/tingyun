# -*- coding: utf-8 -*-
# @Author: xiaodong
# @Date  : 2021/8/10

import json
import time
import asyncio
import logging
from typing import Awaitable
from datetime import datetime, timedelta

# pip install aiohttp
import aiohttp

from script import table
from script.table import session, _bulk_insert


logger = logging.getLogger("aiops")


# -------------------------------------------------------------------------------------------------
URL = "https://api.tingyun.com/server/latest/accounts/1635961/charts/account-applications.json"

URL_PREFIX = "https://api.tingyun.com/server/latest/accounts/1635961/application/{applicationId}/charts"

URL_APDEX = "%s/application-apdex.json" % URL_PREFIX
URL_ERRORS = "%s/application-errors.json" % URL_PREFIX
URL_TOPN = "%s/application-webaction-topn.json" % URL_PREFIX
URL_APPLICATION = "%s/application-application.json" % URL_PREFIX

URL_THROUGHPUT = "%s/application-throughput.json" % URL_PREFIX
URL_OVERVIEW_QUANTILE = "%s/application-overview-quantile.json" % URL_PREFIX
URL_CPU = "%s/application-cpu.json" % URL_PREFIX
URL_MEM = "%s/application-mem.json" % URL_PREFIX

HEADERS = {"X-Auth-Key": "dnngfb73"}
DATA = {"timePeriod": "", "endTime": "", "instanceId": ""}

URLS_DICT = {
    "Apdex": URL_APDEX,
    "Error": URL_ERRORS,
    "TopN": URL_TOPN,
    "Application": URL_APPLICATION,

    "Throughput": URL_THROUGHPUT,
    "ResponseQuantile": URL_OVERVIEW_QUANTILE,
    "CPU": URL_CPU,
    "Memory": URL_MEM,
}
# -------------------------------------------------------------------------------------------------


class Transform(object):
    mapping = {
        "time": "time",

        "Apdex": "apdex",
        "满意的次数": "satisfied_count",
        "可忍受的次数": "tolerable_count",
        "令人沮丧的次数": "frustrated_count",
        "成功访问次数": "success_count",

        "错误百分比": "error_percent",
        "错误量": "error_count",

        "访问量": "visit_count",

        "墙钟时间比": "duration_wall",
        "平均响应时间": "duration_total",
        "最大值": "max",
        "最小值": "min",
        "标准差": "duration_square",

        "性能": "performance",

        "吞吐率": "throughtoutt",
        "响应时间": "response_time_total",
        "内存使用量": "mem_usage_total",
        "CPU使用率": "cpu_usage_total",
    }

    async def transform(self, out: dict):
        newout = {}
        for k, v in self.mapping.items():
            if k in out:
                newout[v] = out.pop(k)
        newout.update(out)
        return newout

    async def transforms(self, outs: list):
        newouts = []
        for out in outs:
            newouts.append(await self.transform(out))
        return newouts


async def transforms(outs: list):
    return await Transform().transforms(outs)


class APICalled:
    """统计接口调用次数"""
    _c = 0


class Request(object):

    async def post(self, url: str, headers: dict, data: dict) -> Awaitable:
        connector = aiohttp.TCPConnector(limit=50)
        timeout = aiohttp.ClientTimeout(total=3 * 60)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                async with session.post(url, headers=headers, data=data) as response:
                    APICalled._c += 1
                    return await response.json()
            except aiohttp.ServerDisconnectedError:
                await asyncio.sleep(0)

    async def get(self, url: str, headers: dict) -> Awaitable:
        connector = aiohttp.TCPConnector(limit=30)
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                APICalled._c += 1
                return await response.json()

    async def ask(self, furl: str, headers: dict, data: dict, obj: dict) -> Awaitable:
        url = furl.format(applicationId=obj["applicationId"])
        logger.info("[url] %s", url)
        response = await self.post(url, headers, data)
        logger.debug("[ask][response] %s", json.dumps(response, ensure_ascii=False, indent=4))
        return response


class Parse(object):

    async def parse(self, response: dict, data: dict = None):
        if data is None:
            data = {}
        out = []
        if response is None:
            return
        colnames = [obj["name"] for obj in response["chart"]["dataset"][0]["head"]["cols"]] + ["time"]
        serieses = response["chart"]["dataset"][0]["head"]["serieses"]
        for i, series in enumerate(serieses):
            for value, time in zip(
                    response["chart"]["dataset"][0]["data"][0][i],
                    response["chart"]["dataset"][0]["head"]["rows"]
            ):
                if not value:
                    value = [None] * (len(colnames) - 1)
                out.append({
                    **data,
                    "serieses_id": series["id"],
                    "serieses_name": series["name"],
                    **dict(zip(colnames, value + [time["name"]]))
                })
        return out


def retry(count: int = 10, allow_error=(Exception,)):
    def o(f):
        async def i(*args, **kwargs):
            error = None
            for i in range(count):
                try:
                    out = await f(*args, **kwargs)
                    return out
                except allow_error as e:
                    error = e
                    pass
            raise error
        return i
    return o


# 放在全局变量里是因为异步调用老是会超时 -_-|
gouts = {}


class TingYunApi(Request, Parse):

    def __init__(self, url: str, urls_dict: dict, headers: dict):
        self.url = url
        self.headers = headers
        self.urls_dicts = urls_dict

    @retry(count=30)
    async def get_instance_id(self, applicationId, data, Cookie):
        headers = {"Cookie": f"{Cookie}"}
        url = f"https://report.tingyun.com/server/application/instances?applicationId={applicationId}"
        url += f"&endTime=&timePeriod={data.get('timePeriod', '30')}"
        return await self.get(url, headers)

    async def srunme(self, name, furl, response, data, Cookie):
        logger.info("[name] %s", name)

        async def run_per_ins(kw, obj):
            # 每个实例的数据
            # ------------------------------------------------------------------------
            ids = await self.get_instance_id(obj["applicationId"], data, Cookie)
            for iid in ids:
                d = data.copy()
                d["instanceId"] = iid["id"]
                newresponse = await self.ask(furl, self.headers, d, obj)

                kw.update(
                    instance_id=iid["id"],
                    instance_name=iid["name"],
                )
                outs = await self.parse(newresponse, kw)
                if outs is None:
                    return
                outs = await transforms(outs)
                gouts.setdefault(name, []).extend(outs)

        async def run_all_ins(kw, obj):
            # 所有实例数据
            # ------------------------------------------------------------------------
            newresponse = await self.ask(furl, self.headers, data, obj)
            kw.update(
                instance_id=-1,
            )
            outs = await self.parse(newresponse, kw)
            if outs is None:
                return
            outs = await transforms(outs)
            gouts.setdefault(name, []).extend(outs)

        async def run_per_app(obj):
            kw = {
                "application_id": obj["applicationId"],
                "application_name": obj["name"],
                "group_id": obj["groupId"],
                "group_name": obj["groupName"],

            }
            await asyncio.gather(*[
                # run_per_ins(kw, obj),
                run_all_ins(kw, obj),
            ])

        await asyncio.gather(*[run_per_app(obj) for obj in response["data"]])

    async def runme(self, dt: str, period: int = 30, Cookie: str = None):
        data = {
            "timePeriod": str(period),
            "endTime": dt
        }
        response = await self.post(url=self.url, headers=self.headers, data=data)

        await asyncio.gather(
            *[
                self.srunme(name, furl, response, data, Cookie)
                for name, furl in self.urls_dicts.items()
            ]
        )
        return self

    def get_dt(self, dt: str, i: int):
        end_day = datetime.fromisoformat(dt)
        end_day_with_minute = end_day + timedelta(minutes=i * 30)
        end_day_with_minute = str(end_day_with_minute)
        return end_day_with_minute

    async def fast_fetch_one_day(self, dt: str, Cookie: str):
        await asyncio.gather(
            *[self.runme(dt=self.get_dt(dt, i), period=30, Cookie=Cookie) for i in range(1, 49)]
        )
        return self
    
    async def fetch_one_day(self, dt: str, Cookie: str, semaphore: int = 5):
        for i in range(1, 49, semaphore):
            await asyncio.gather(
                *[
                    self.runme(dt=self.get_dt(dt, ii), period=30, Cookie=Cookie)
                    for ii in range(i, i+semaphore)
                    if ii < 49
                ]
            )
        return self


def insert2table(outs: dict, batch_size: int = 1000):
    bulk_insert = _bulk_insert(batch_size=batch_size)
    for k, vs in outs.items():
        for v in vs:
            bulk_insert(getattr(table, k)(**v))
    bulk_insert(force=True)
    
