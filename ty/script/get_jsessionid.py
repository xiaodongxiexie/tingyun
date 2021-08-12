# -*- coding: utf-8 -*-
# @Author: xiaodong
# @Date  : 2021/8/11

import re
import requests

class Secret:
    username: str = ""
    password: str = ""
    hashpassword: str = ""


class LoginThenGetJSESSIONID(object):
    loginurl = 'https://account.tingyun.com/cas/login?service=' \
               'https://report.tingyun.com/server/cas-shiro?loginView=casLoginTingyun&lang=zh_CN'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                  '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Content-Length': '158',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'account.tingyun.com',
        'Origin': 'https://account.tingyun.com',
        'Referer': 'http://account.tingyun.com/cas/login?'
                   'service=https://report.tingyun.com/server/cas-shiro?loginView=casLoginTingyun',
        'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        'sec-ch-ua-mobile': '?0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.164 Safari/537.36'
    }
    headers2 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.164 Safari/537.36'}

    @classmethod
    def get_JSESSIONID(cls):
        
        data = {
            'lt': '',
            'execution': 'e3s1',
            '_eventId': 'submit',
            'abcValue': '',
            'username': Secret.username,
            'password': "",
            'rememberMe': 'true'
        }
        data2 = data.copy()
        data2["password"] = Secret.password

        s = requests.Session()
        # 必须要post两次，why?
        # ----------------------------------------------------------
        r = s.post(cls.loginurl, data=data, headers=cls.headers)
        r = s.post(cls.loginurl, data=data, headers=cls.headers)

        rr = s.get(cls.loginurl)

        data["lt"] = re.findall("value=\"(LT.*?)\"", rr.text)[0]
        data["password"] = Secret.hashpassword

        # 必须要换掉用headers2, why?
        r = s.post(cls.loginurl, data=data, headers=cls.headers2)
        JSESSIONID = re.findall("(JSESSIONID=.*?);", r.request.headers["Cookie"])[0]

        return JSESSIONID


if __name__ == '__main__':

    Secret.hashpassword = "hash-password-by-login-tingyun-then-get-it"
    Secret.password = "your-password"
    Secret.username = "your-username"
    JSESSIONID = LoginThenGetJSESSIONID.get_JSESSIONID()

    print(JSESSIONID)
