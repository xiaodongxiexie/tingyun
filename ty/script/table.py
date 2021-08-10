# -*- coding: utf-8 -*-
# @Author: xiaodong
# @Date  : 2021/8/5

import re
import logging
import asyncio
from typing import List, Optional

import aiosqlite
from databases import Database
from sqlalchemy import insert
from sqlalchemy.orm import Session
from sqlalchemy import Column, DECIMAL, CHAR, INTEGER, VARCHAR
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base

from script.config import db, engine


Base = declarative_base()
metadata = Base.metadata

logger = logging.getLogger("aiops.db")


async def insert2table(table, values, dbconnection: Database = Database(db, check_same_thread=False)):
    """
    用于边获取数据边插入到数据库

    写入到sqlite时遇到databas locked问题，暂时不使用该方式插入数据库，
    使用GP或mysql时可以考虑这种方式
    """
    if not dbconnection.is_connected:
        await dbconnection.connect()
    try:
        await dbconnection.execute_many(insert(table), values)
    except aiosqlite.OperationalError:
        await asyncio.sleep(0)
    if dbconnection.is_connected:
        await dbconnection.disconnect()

session = Session(bind=engine)


def camel2snake(v):
    return re.sub(r"[A-Z]", lambda obj: "_" + obj.group()[0].lower(), v)


class Mixin:

    prefix = "aiops"

    time = Column(CHAR(30), primary_key=True, comment="时间,分钟级别")
    group_id = Column(INTEGER, primary_key=True)
    application_id = Column(INTEGER, primary_key=True, comment="应用id")
    instance_id = Column(INTEGER, primary_key=True, default=-1, comment="应用实例id, 默认为-1：即所有实例对应数据")
    serieses_id = Column(INTEGER, primary_key=True)

    group_name = Column(VARCHAR)
    application_name = Column(VARCHAR, comment="应用名称")
    instance_name = Column(VARCHAR, comment="实例名称")
    serieses_name = Column(VARCHAR(64))

    @declared_attr
    def __tablename__(cls):
        return cls.prefix + camel2snake(cls.__name__)


class Apdex(Mixin, Base):
    """application-apdex"""

    apdex = Column(DECIMAL(10, 2), comment="Apdex")
    satisfied_count = Column(INTEGER, comment="满意次数")
    tolerable_count = Column(INTEGER, comment="可忍受次数")
    frustrated_count = Column(INTEGER, comment="令人沮丧的次数")
    success_count = Column(INTEGER, comment="成功访问次数")


class Error(Mixin, Base):
    """application-errors"""

    error_percent = Column(DECIMAL(10, 2), comment="错误百分比")
    error_count = Column(INTEGER, comment="错误量")
    visit_count = Column(INTEGER, comment="访问量")


class Throughput(Mixin, Base):
    """application-throughput"""

    throughtoutt = Column(DECIMAL(10, 3), comment="吞吐率")
    visit_count = Column(INTEGER, comment="访问量")


class Memory(Mixin, Base):
    """application-mem"""

    mem_usage_total = Column(DECIMAL(10, 3), comment="内存使用量")


class CPU(Mixin, Base):
    """application-cpu"""

    __tablename__ = "aiops_cpu"

    cpu_usage_total = Column(DECIMAL(10, 3), comment="CPU使用率")


class Application(Mixin, Base):
    """application-application"""

    performance = Column(DECIMAL(10, 3), comment="性能")
    visit_count = Column(INTEGER, comment="访问量")


class ResponseQuantile(Mixin, Base):
    """application-overview-quantile"""

    response_time_total = Column(DECIMAL(10, 3), comment="响应时间")


class TopN(Mixin, Base):
    """application-webaction-topn"""

    __tablename__ = "aiops_topn"

    duration_wall = Column(DECIMAL(10, 3), comment="墙钟时间比")
    visit_count = Column(INTEGER, comment="访问量")
    duration_total = Column(DECIMAL(10, 3), comment="平均响应时间")
    max = Column(DECIMAL(10, 3), comment="响应时间最大值")
    min = Column(DECIMAL(10, 3), comment="响应时间最小值")
    duration_square = Column(DECIMAL(10, 3), comment="响应时间标准差")


def _bulk_insert(objs: List[Base] = None, batch_size: int = 200) -> callable:
    """
    用于批量向数据库插入数据
    :param objs:
    :param batch_size: 批量插入条数
    :return: callable
    """
    _bulk_insert.error = False
    if objs is None:
        objs = []

    def bulk(obj: Optional[Base] = None, batch_size: int = batch_size, force: bool = False, session: Session = session):
        """
        用于批量插入
        :param obj:
        :param batch_size: 批量插入条数
        :param force: 是否强制插入，及不满足批量插入条数也执行插入
        :param session:
        :return: None
        """
        if obj is not None:  # 这么写是为了强制提交时可以不给定obj，即force=True
            objs.append(obj)
        will_clear = True
        if len(objs) >= batch_size or (force and objs):
            if _bulk_insert.error:
                return

            try:
                session.bulk_save_objects(objs)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.exception("[write to database][error] %s", e, exc_info=False)
                will_clear = False
                _bulk_insert.error = True
            if will_clear:
                logger.info("[write to database][count] %s", len(objs))
                objs.clear()

    _bulk_insert.objs = objs
    return bulk
