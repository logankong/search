import time
import json
import webbrowser
import re
from urllib.parse import quote, urlparse
from collections import namedtuple
import requests
import lxml.html
from lxml.html.clean import Cleaner
import multiprocessing
import jieba


Question = namedtuple('Question', ['id', 'desc', 'option_list'])

SearchEngine = namedtuple('Engine', ['name', 'api', 'charset'])

search_engine = [
    SearchEngine(name='BAIDU', api='http://www.baidu.com/s?wd={}', charset='utf-8'),
    # SearchEngine(name='SOGOU', api='http://www.sogou.com/web?query={}', charset='utf-8'),
    SearchEngine(name='BDZD', api='https://zhidao.baidu.com/search?word={}', charset='gbk'),
    # SearchEngine(name='BING', api='http://cn.bing.com/search?q={}', charset='utf-8'),
    # SearchEngine(name='GOOGLE', api='https://www.google.com.hk/search?newwindow=1&hl=zh-CN&q={}', charset='utf-8'),
]

category_list = ['summary', 'option']
# category_list = ['summary']

old_question = []

cleaner = Cleaner(allow_tags=[''], remove_unknown_tags=False)

headers = {
    'Host': 'msg.api.chongdingdahui.com',
    'User-Agent': 'LiveTrivia/1.0.4 (com.chongdingdahui.app; build:0.1.7; iOS 11.2.2) Alamofire/4.6.0',
    'X-Live-App-Version': '1.0.4',
    'Content-Type': 'application/json',
    'X-Live-Device-Identifier': 'AC654DF3-402D-40B3-BF20-19D8A5B57793',
    # 'X-Live-Session-Token': '1.3071218.845633.ZtC.d650c387f4c187ce54b2ea432bfa4f51',
    'X-Live-Session-Token': '1.3071218.2811521.lao.5dc60efb955f70eb1e981ceb422e0eae',
    'X-Live-Device-Type': 'ios',
    'X-Live-OS-Version': 'Version 11.2.2 (Build 15C202)',
}

search_header = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
    "Cache-Control": "no-cache"
}

fake_json = {
    "data": {
        "event": {
            # "desc": '“敖包相会”中的“敖包”是什么？',
            # "options": "['蒙古包', '石堆', '河流']",
            "desc": '以下哪项不是板块构造学说里的板块之一？',
            "options": "['南极洲板块', '大西洋板块', '印度洋板块']",
            # "desc": '小说《月亮和六便士》的故事背景来源于？',
            # "options": "['保罗•高更', '毛姆', '莫奈']",
            "questionId": 1112,
            # //div[@class="c-abstract"]
            # nlp
        },
    }
}

remove_mark = '\'|\"|<|>|《|》|\[|\]|\{|\}|\(|\)'


def worker(flag, engine_name, option_num, engine, search_header, opt, jieba_str, answer, query):
    option_opt1_num = []
    # print(opt)
    for opt1 in opt:
        res = requests.get(engine.api.format(quote(query)), timeout=5, headers=search_header)
        res.encoding = engine.charset
        res = res.text

        html = lxml.html.document_fromstring(res)[0]
        if engine.name == 'BAIDU':
            content_left = html.xpath('//div[@id="content_left"]')
            # content_left = html.xpath('//div[@id="content_left"]')
        if engine.name == 'SOGOU':
            content_left = html.xpath('//*[@id="main"]')
        if engine.name == 'BING':
            content_left = html.xpath('//*[@id="b_results"]')
        if engine.name == 'BDZD':
            content_left = html.xpath('//*[@id="page-main"]/div/div/div/div[2]')

        if content_left:
            content = lxml.html.tostring(content_left[0], encoding=engine.charset,
                                         method="html", pretty_print=True).decode(engine.charset)
            cleaned_text = cleaner.clean_html(content)
            cleaned_text = ' '.join(cleaned_text.strip().split())
            option_opt1_num.append(cleaned_text.count(opt1))
    option_opt_num = sum(option_opt1_num)
    option_num[jieba_str] = option_opt_num
    engine_name[engine.name] = option_num
    # print(os.getpid())
    answer[flag] = engine_name


def search_answer(question):
    answer = {}
    jieba.initialize()
    # qdesc_jieba = jieba.cut(question.desc)
    # qdesc = ' '.join(qdesc_jieba)
    # query = qdesc
    query = question.desc
    manager = multiprocessing.Manager()
    answer = manager.dict()

    # 人名和空格分词，其它不分
    # list_jieba = ['电影', '诗', '动画', '人名', '书']
    list_jieba = ['电影', '诗', '动画', '人名', '书']
    flag_jieba = True
    for jieba1 in list_jieba:
        if jieba1 in question.desc:
            flag_jieba = False
            break

    jobs = []
    for flag in category_list:
        engine_name = manager.dict()
        for engine in search_engine:
            search_header['Host'] = urlparse(engine.api).netloc
            option_num = manager.dict()
            for opt in question.option_list:
                if flag == 'option':
                    query = question.desc + ' ' + opt

                flag_number = bool(re.search(r'\d', opt))

                if '·' not in opt and len(opt) > 4 and not flag_number and flag_jieba:
                    opt = jieba.cut(opt)
                    jieba_opt = ','.join(opt)
                    opt = jieba_opt.split(',')
                    jieba_str = ''.join(opt)
                    for i in range(opt.count(' ')):
                        opt.remove(' ')
                else:
                    jieba_str = opt
                    opt = opt.split(',')

                p = multiprocessing.Process(target=worker, args=(flag, engine_name, option_num, engine, search_header, opt, jieba_str, answer, query))
                p.start()
                jobs.append(p)
    for proc in jobs:
        proc.join()

    return answer


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
            desc = desc[desc.find('.') + 1:desc.find('?')]
            option_list = eval(res_dict['data']['event']['options'])
            option_list = [re.sub(remove_mark, '', o).strip() for o in option_list]
            return Question(id=question_id, desc=desc, option_list=option_list)
        else:
            return None
    except Exception as e:
        print(e)


def run_helper():
    # debug = True
    debug = False

    while True:
        q = get_question(debug)

        if q:
            if q.id not in old_question:
                old_question.append(q.id)
                # jieba.initialize()
                # qdesc_jieba = jieba.cut(q.desc)
                # qdesc = ' '.join(qdesc_jieba)
                webbrowser.open("http://www.sogou.com/web?query={}".format(quote(q.desc)))
                answers = search_answer(q)

                q_list_jieba = ['不', '无关', '没出现', '不包含', '没有', '不是', '不属于', '不包括', '不曾', '不与']
                q_flag_jieba = True
                for q_jieba1 in q_list_jieba:
                    if q_jieba1 in q.desc:
                        q_flag_jieba = False
                        break

                new_answer = {}
                new_engine_name = {}
                print(q.desc)
                print(q.option_list)
                with open('chongdingdahui.log', 'a') as f:
                    f.write('-------------------------' + '\n')
                    f.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + '\n')
                    f.write(q.desc + '\n')
                    f.write(','.join(q.option_list) + '\n')
                    for k, v in answers.items():
                        for key, value in v.items():
                            new_engine_name[key] = value.copy()
                            new_answer[k] = new_engine_name.copy()
                    jsonsObj = json.dumps(new_answer, ensure_ascii=False)
                    f.write(jsonsObj + '\n')

                fina_answer = {}
                for keys in new_answer.keys():
                    answer = new_answer[keys]
                    result = {}
                    for option in q.option_list:
                        init_total = 0
                        for key in answer.keys():
                            if isinstance(answer[key][option], str):
                                answer[key][option] = 0
                            init_total += answer[key][option]
                            # print('{}: {}: {}'.format(key, option, answer[key][option]))
                        average = init_total / len(search_engine)
                        result[option] = average

                    # if '没' in q.desc or '没出现' in q.desc or '不包含' in q.desc or '没有' in q.desc or '不是' in q.desc or '不属于' in q.desc or '不包括' in q.desc or '不曾' in q.desc:
                    if q_flag_jieba:
                        fina_answer[keys] = sorted(result.items(), key=lambda x: x[1], reverse=True)
                    else:
                        fina_answer[keys] = sorted(result.items(), key=lambda x: x[1])

                if fina_answer['summary'][0][0] == fina_answer['option'][0][0]:
                    for value in fina_answer['summary']:
                        print('{}: {}'.format(value[0], value[1]))
                else:
                    for category_key, category_value in fina_answer.items():
                        if category_key == 'option' and ("以下" in q.desc or "下面" in q.desc):
                            print(category_key + '【主】---------------------------')
                        elif category_key == 'option':
                            print(category_key)
                        if category_key == 'summary' and ("以下" not in q.desc and "下面" not in q.desc):
                            print(category_key + '【主】---------------------------')
                        elif category_key == 'summary':
                            print(category_key)
                        for value in category_value:
                            print('{}: {}'.format(value[0], value[1]))
                with open('chongdingdahui.log', 'a') as f:
                    f.write(str(fina_answer) + '\n')
        else:
            pass

        if debug:
            exit()
        time.sleep(2)


if __name__ == '__main__':
    run_helper()
