import json
import re
import time
import webbrowser
from collections import namedtuple
from urllib.parse import quote

import requests

from search import Search

Question = namedtuple('Question', ['id', 'desc', 'option_list'])

old_question = []

headers = {
    'Host': 'msg.api.chongdingdahui.com',
    'User-Agent': 'LiveTrivia/1.0.4 (com.chongdingdahui.app; build:0.1.7; iOS 11.2.2) Alamofire/4.6.0',
    'X-Live-App-Version': '1.0.4',
    'Content-Type': 'application/json',
    'X-Live-Device-Identifier': 'AC654DF3-402D-40B3-BF20-19D8A5B57793',
    'X-Live-Session-Token': '1.3071218.845633.ZtC.d650c387f4c187ce54b2ea432bfa4f51',
    'X-Live-Device-Type': 'ios',
    'X-Live-OS-Version': 'Version 11.2.2 (Build 15C202)',
}

fake_json = {
    "data": {
        "event": {
            "desc": "1.山峰“穆迪峰”位于哪里",
            "options": "['南极洲', '西藏', '尼泊尔']",
            "questionId": 1112,
        },
    }
}

remove_mark = '\'|\"|<|>|《|》|\[|\]|\{|\}|\(|\)'

baidu_browser = webbrowser.get("chrome")
google_browser = webbrowser.get("safari")


def get_response(url, headers, timeout):
    try:
        res = requests.get(url, headers=headers, timeout=timeout).text
        return res
    except Exception as e:
        print(e)


def get_question(debug):
    timestamp = int(time.time())
    try:
        if debug:
            res_dict = fake_json
        else:
            res = requests.get('http://msg.api.chongdingdahui.com/msg/current?showTime={}'.format(timestamp), timeout=2,
                               headers=headers).text
            res_dict = json.loads(res)

        if "data" in res_dict.keys():
            question_id = res_dict['data']['event']['questionId']
            desc = res_dict['data']['event']['desc']
            desc = desc[desc.find('.') + 1:]
            if desc in ['?', '!', '.', '？', '！', '。']:
                desc = desc[:-1]
            option_list = eval(res_dict['data']['event']['options'])
            option_list = [re.sub(remove_mark, '', o.strip()) for o in option_list]
            return Question(id=question_id, desc=desc, option_list=option_list)
        else:
            # print(res_dict)
            return None
    except Exception as e:
        print(e)


def run_helper():
    #  debug = True
    debug = False
    while True:
        s = Search()
        q = get_question(debug)
        if q:
            if q.id not in old_question:
                old_question.append(q.id)
                if not debug:
                    baidu_browser.open("http://baidu.com/s?wd={}".format(quote(q.desc)))
                    #  google_browser.open("http://www.google.com/search?q={}".format(quote(q.desc)))
                s.search_question(q.desc, q.option_list)

        else:
            pass
        time.sleep(1)


if __name__ == '__main__':
    try:
        run_helper()
    except Exception as error:
        print("ERROR")
        print(error)
