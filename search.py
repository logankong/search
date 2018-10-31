import re
from urllib.parse import quote
import time
from difflib import SequenceMatcher

import requests
import lxml.html
from lxml.html.clean import Cleaner
from colored import fg, attr
from tabulate import tabulate
import jieba

jieba.initialize()

cleaner = Cleaner(allow_tags=[''], remove_unknown_tags=False)

spacer_list = ['•', '·']


def get_response(url, headers, timeout, **kwargs):
    try:
        res = requests.get(url, headers=headers, timeout=timeout, **kwargs).content
        return res
    except Exception as e:
        print(e)


class Search:
    def __init__(self):
        self.headers = {
            'Host': 'www.baidu.com',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
        }

        self.baidu_url = "http://www.baidu.com/s?wd={}"
        self.timeout = 5

    @staticmethod
    def clean_html(doc, charset='utf-8'):
        doc = lxml.html.tostring(doc, encoding=charset, method="html").decode("utf-8")
        cleaned_text = cleaner.clean_html(doc)
        cleaned_text = ' '.join(cleaned_text.strip().split())
        cleaned_text = re.sub("更多关于.*?的问题", "", cleaned_text)
        return cleaned_text

    def get_baidu_res(self, question_str):
        question_str = quote(question_str)
        res = get_response(self.baidu_url.format(question_str), self.headers, self.timeout)
        return res

    def get_baike_res(self, url):
        self.headers['Host'] = 'baike.baidu.com'
        res = get_response(url, self.headers, self.timeout)
        return res

    @staticmethod
    def find_baike(res):
        doc = lxml.html.document_fromstring(res)
        baike_a_list = doc.xpath('//div[contains(@mu, "baike.baidu.com")]')
        if baike_a_list:
            first_baike = baike_a_list[0]
            # name = first_baike.xpath('//a[contains(text(), "_百度百科")]')[0].text_content()
            name = first_baike.xpath('//a[contains(text(), "_百度百科")]')
            if name:
                name = name[0].text_content()
            url = first_baike.get('mu')
            return name, url
        else:
            return None, None

    def analysis_html(self, res, is_baike=False):
        doc = lxml.html.document_fromstring(res)[0]
        if not is_baike:
            # abstract_list = doc.xpath('//div[@class="c-abstract"]')
            abstract_list = doc.xpath('//div[@id="content_left"]')

            if abstract_list:
                return ''.join(self.clean_html(a) for a in abstract_list)
            else:
                return None

        else:
            content = doc.xpath('//div[@class="main-content"]')

            if content:
                return ''.join(self.clean_html(content[0]))
            else:
                return None

    @staticmethod
    def check_spacer(opt):
        for spacer in spacer_list:
            if spacer in opt:
                return True

    @staticmethod
    def replace_spacer(opt):
        spacer = '\•|\·'
        return re.sub(spacer, '.', opt)

    def get_opt_context(self, opt, result):
        if self.check_spacer(opt):
            opt = self.replace_spacer(opt)

        pattern = "\w*?" + opt + "\w*?"

        try:
            context = set(re.findall(pattern, result))
            context = ', '.join(list(context)[:10]).strip()
            context = re.sub(opt, fg(1) + opt + attr(0), context)
        except:
            context = None

        if context:
            return context
        else:
            return None

    def result_count(self, result, opt):
        count = 0

        if result:
            if self.check_spacer(opt):
                re_opt = self.replace_spacer(opt)
                count += len(re.findall(re_opt, result))
            else:
                count += result.count(opt)
        else:
            count = None

        if count == 0 and len(opt) > 3:
            # 如果没有匹配，进行分词搜索
            try:
                spacer = '\•|\·'
                seg_list = jieba.cut(opt)
                seg_opt = '\w*?'.join(seg_list)
                seg_opt = re.sub(spacer, '', seg_opt)

                # seg_opt = opt[0:2] + '\w*?' + opt[-1]
                count = len(re.findall(seg_opt, result))
                if count == 0:
                    # 如果结果仍然为零，进行字符串比对
                    count = SequenceMatcher(None, opt, result).ratio()
                    count = "{0:.5f}%".format(count * 100)
                    count = fg(3) + str(count) + attr(0)
                else:
                    count = fg(2) + str(count) + attr(0)
            except Exception:
                count = fg(1) + "0" + attr(0)

        opt_context = self.get_opt_context(opt, result)

        return count, opt_context

    @staticmethod
    def count_baidu_em(res):
        doc = lxml.html.document_fromstring(res)[0]
        em_list = doc.xpath('//em')
        return len(em_list)

    @staticmethod
    def baidu_search_related(em1, em2):
        try:
            return "{0:.0f}%".format(em2 / em1 * 100)
        except:
            return None

    def ask_baidu(self, question, opt_list):
        baidu_res = self.get_baidu_res(question)
        baidu_result = self.analysis_html(baidu_res)
        baike_name, baike_url = self.find_baike(baidu_res)
        baidu_em_count = self.count_baidu_em(baidu_res)

        print("%s题目直接搜索...%s" % (fg(4), attr(0)))
        baidu_result_count_list = []
        baidu_result_context_list = []
        for opt in opt_list:
            count, context = self.result_count(baidu_result, opt)
            baidu_result_count_list.append(count)
            baidu_result_context_list.append(context)
        print(tabulate(zip(opt_list, baidu_result_count_list, baidu_result_context_list), tablefmt="grid"))

        print("%s题目 + 选项搜索...%s" % (fg(5), attr(0)))
        baidu_opt_result_count_list = []
        baidu_search_related_count_list = []
        baidu_opt_result_context_list = []
        for opt in opt_list:
            baidu_opt_res = self.get_baidu_res(question + " " + opt)
            baidu_opt_result = self.analysis_html(baidu_opt_res)
            baidu_opt_em_count = self.count_baidu_em(baidu_opt_res)
            count, context = self.result_count(baidu_opt_result, opt)
            baidu_opt_result_count_list.append(count)
            baidu_opt_result_context_list.append(context)
            baidu_search_related_count_list.append(self.baidu_search_related(baidu_em_count, baidu_opt_em_count))

        print(tabulate(
            zip(opt_list, baidu_opt_result_count_list, baidu_search_related_count_list, baidu_opt_result_context_list),
            tablefmt="grid"))

        if baike_name:
            baike_result_count_list = []
            baike_result_context_list = []
            print("{}发现 {}{}".format(fg(1), baike_name, attr(0)))
            baike_res = self.get_baike_res(baike_url)
            baike_result = self.analysis_html(baike_res, is_baike=True)

            for opt in opt_list:
                count, context = self.result_count(baike_result, opt)
                baike_result_count_list.append(count)
                baike_result_context_list.append(context)
            print(tabulate(zip(opt_list, baike_result_count_list, baike_result_context_list), tablefmt="grid"))

    def search_question(self, question, opt_list):

        print(question)
        print(opt_list)

        if question[-1] in ['?', '!', '.', ';', '？', '！', '。', '；']:
            question = question[:-1]

        self.ask_baidu(question, opt_list)

        key_pattern = re.compile('“(.*)”|「(.*)」|《(.*)》')
        re_key_word = re.findall(key_pattern, question)

        if re_key_word:
            key_word = list(filter(None, re_key_word[-1]))[0]

            print("发现关键词 {}".format(fg(9) + key_word + attr(0)))

            self.ask_baidu(key_word, opt_list)


if __name__ == '__main__':
    s = Search()
    # question = "以下哪种动物没出现在海南四大名菜中？"
    # opt_list = ['鸡', '鸭', '鱼']
    # question = "小说《月亮和六便士》的故事背景来源于?"
    # opt_list = ['保罗•高更', '毛姆', '莫奈']
    # question = '亚洲现存最古老的藏书阁是？'
    # opt_list = ['浙江宁波天一阁', '泰国玉佛寺藏经阁', '印度拉扎图书馆']
    # question = "下面三句涉及梨花的诗句中，哪一句的梨花指的是真实的梨花？"
    # opt_list = ['千树万树梨花开', '梨花一枝春带雨', '梨花淡白柳深青']
    # question = '以下哪项不是板块构造学说里的板块之一？'
    # opt_list = ['南极洲板块', '大西洋板块', '印度洋板块']
    # question = '电影《超能陆战队》中机器人大白的标志是？'
    # opt_list = ['◑ˍ◐', '￣o￣', '●—●']
    # question = '中国曾多次赠送给布鲁塞尔的「撒尿小男孩」铜像衣服，但没送过以下哪类服饰?'
    # opt_list = ['宇航员服', '汉服', '马褂']
    # question = '太阳是一颗？'
    # opt_list = ['红巨星', '白矮星', '黄矮星']
    # question = '以下哪个不是歌名?'
    # opt_list = ['听海', '法海', '看海']
    question = '中国传统五声音阶中，“羽”按声母发音部位划分属于?'
    opt_list = ['唇音', '牙音', '喉音']
    # question = '《红楼梦》里“机关算尽太聪明，反误了卿卿性命”说的是？'
    # opt_list = ['王夫人', '王熙凤', '薛宝钗']
    s.search_question(question, opt_list)

    # questions_list = ['丘吉尔是哪个国家的前首相?',
    #                   '2005年的今天，韩国宣布首都的中文名改为“首尔”，之前叫做？',
    #                   '《灌篮高手》中，除了白色款，湘北和陵南的队服主色调分别是？',
    #                   '《红楼梦》里“机关算尽太聪明，反误了卿卿性命”说的是？',
    #                   '“敖包相会”中的“敖包”是什么？',
    #                   '以下哪项不是板块构造学说里的板块之一？',
    #                   '小说《月亮和六便士》的故事背景来源于？',
    #                   '神户牛肉专指在以下哪种牛身上切的肉？',
    #                   '以下美国地点里，赫鲁晓夫，勃列日涅夫，戈尔巴乔夫三任苏联领导人都曾到访过的是？',
    #                   '亚洲现存最古老的藏书阁是？',
    #                   '简•奥斯汀代表作《傲慢与偏见》之前名字是？',
    #                   '根据现有的国境划分，以下哪个国家在领土上并不与意大利接壤？']
    #
    # opt_lists = [['苏联', '美国', '英国'],
    #              ['平壤', '汉城', '高丽'],
    #              ['红+蓝', '黑+白', '粉+黄'],
    #              ['王夫人', '王熙凤', '薛宝钗'],
    #              ['蒙古包', '石堆', '河流'],
    #              ['南极洲板块', '大西洋板块', '印度洋板块'],
    #              ['保罗•高更', '毛姆', '莫奈'],
    #              ['见岛牛', '但马牛', '大额牛'],
    #              ['戴维营', '好莱坞', '迪士尼乐园'],
    #              ['浙江宁波天一阁', '泰国玉佛寺藏经阁', '印度拉扎图书馆'],
    #              ['最初的印象', '理性与感性', '最初的梦象'],
    #              ['瑞士', '奥地利', '德国']]
    #
    # # questions_list = ['最早的语音识别器是什么形态的？',
    # #                   'AlphaGo没有战胜过以下哪位选手?',
    # #                   '以下哪部电影中出现了超级计算机“红后”？',
    # #                   '荣耀V10手机通过智能识别，不会让陌生人查看锁屏界面的什么内容?',
    # #                   '全球首款人工智能手机芯片是?']
    # # #
    # # opt_lists = [['玩具狗', '机器人', '小苹果'],
    # #              ['柯洁', '周睿羊', '许银川'],
    # #              ['星际迷航', '生化危机6', '进化危机'],
    # #              ['时间', '日期', '未读微信消息'],
    # #              ['麒麟950芯片', '麒麟960芯片', '麒麟970AI芯片']]
    # # #
    # s = Search()
    # o = zip(questions_list, opt_lists)
    # for question, opt_list in zip(questions_list, opt_lists):
    #     s.search_question(question, opt_list)
    #     time.sleep(1)
