# -*- coding: utf-8 -*-
# @Author: xiaodong
# @Date  : 2021/8/10

from sqlalchemy import create_engine

from script.secret import AUTHKEY

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

HEADERS = {"X-Auth-Key": AUTHKEY}
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


db = "sqlite:///{}".format("aiops.tingyun.db")
engine = create_engine(db, echo=0, connect_args={"check_same_thread": False})
