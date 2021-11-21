import re
import requests
import json
import os
import pdfkit
from bs4 import BeautifulSoup
from urllib.parse import quote
from time import sleep
import random
import datetime

config_pdf = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe') #配置wkhtmltopdf


# 检验是否含有中文字符
def get_chinese_head(strs):
    n = len(strs)
    for i in range(n):
        if '\u4e00' <= strs[i] <= '\u9fa5':
            return i
    return -1


def get_data(url, headers, before=None, after=None):
    """
    before 默认为None，否则请填入内容，格式为：'2021-06-31 21:00'，所有小于等于该时间的才会被获取
    after 默认为None，否则请填入内容，格式为：'2021-05-27 20:00'，所有大于等于该时间的才会被获取
    """
    global htmls, num

    i = 0
    while i < 10:
        rsp = requests.get(url, headers=headers)
        if rsp.json().get("succeeded") == False:
            sleep(0.01)
            print("访问失败，重来一遍...")
            rsp = requests.get(url, headers=headers)
            i += 1
        else:
            break

    with open('temp_content.json', 'w', encoding='utf-8') as f:  # 将返回数据写入 temp_content.json 方便查看
        f.write(json.dumps(rsp.json(), indent=2, ensure_ascii=False))

    with open('temp_content.json', encoding='utf-8') as f:
        all_contents = rsp.json()
        contents = all_contents.get('resp_data').get('topics')
        if contents is not None:
            for topic in contents:
                create_time = topic.get("create_time", "")
                if create_time != "":
                    create_time = create_time[:16].replace("T", " ")
                    create_time_time = datetime.datetime.strptime(create_time, '%Y-%m-%d %H:%M')
                    if after is not None:
                        after_time = datetime.datetime.strptime(after, '%Y-%m-%d %H:%M')
                        if after_time > create_time_time: continue
                    if before is not None:
                        before_time = datetime.datetime.strptime(before, '%Y-%m-%d %H:%M')
                        if create_time_time > before_time: continue

                content = topic.get('question', topic.get('talk'))
                try:
                    text = content.get('text')
                except:
                    continue
                # text = text.replace('\n', '</br>')
                ids = get_chinese_head(text)  # 找到标题开头
                text = text[ids:]
                if text != "":
                    pos = text.find("<")
                    title = str(num) + " " + text[:(pos)]
                else:
                    title = str(num) + "Error: 找不到内容"
                # print(title)
                if content.get('images'):
                    soup = BeautifulSoup(html_template, 'html.parser')
                    for img in content.get('images'):
                        url = img.get('large').get('url')
                        img_tag = soup.new_tag('img', src=url)
                        soup.body.append(img_tag)
                        html_img = str(soup)
                        html = html_img.format(title=title, text=text, create_time=create_time)
                else:
                    html = html_template.format(title=title, text=text, create_time=create_time)

                if topic.get('show_comments'):
                    ls = topic.get('show_comments')
                    answer = ""
                    _num = 0
                    k = 0
                    if len(ls) > 0:
                        for l in ls:
                            if 'parent_comment_id' in l.keys():
                                k += 1
                                name = "---- C{}.{}".format(_num, k) + l.get('owner')['name'] + ": "
                            else:
                                _num += 1
                                k = 0
                                name = "C{} ".format(_num) + l.get('owner')['name'] + ": "
                            answer += name
                            answer += l.get('text')
                            answer += "</br>"

                    html = html_template.format(title=title, text=answer, create_time=create_time)
                    # soup = BeautifulSoup(html, 'html.parser')
                    # answer_tag = soup.new_tag('p')
                    # answer_tag.string = answer
                    # soup.body.append(answer_tag)
                    # html_answer = str(soup)
                    # html = html_answer.format(title=title, text=text, create_time=create_time)

                htmls.append(html)

                num += 1
        else:
            print("*" * 16, "访问失败", "*" * 16)
            print("失败url:", url)
            print(all_contents)
            print(rsp.status_code)
            print("*" * 40)

    next_page = rsp.json().get('resp_data').get('topics')

    if next_page:
        create_time = next_page[-1].get('create_time')
        if create_time[20:23] == "000":
            end_time = create_time[:20] + "999" + create_time[23:]
        else:
            res = int(create_time[20:23]) - 1
            end_time = create_time[:20] + str(res).zfill(3) + create_time[23:]  # zfill 函数补足结果前面的零，始终为3位数
        end_time = quote(end_time)
        if len(end_time) == 33:
            end_time = end_time[:24] + '0' + end_time[24:]
        next_url = start_url + '&end_time=' + end_time
        print("next_url:", next_url)
        sleep(random.randint(1, 5) / 50)
        get_data(next_url, headers, before, after)

    return htmls


def make_pdf(htmls, pdf_filepath="E:\\project\\zsxq_to_pdf-master\\zsxq_to_pdf-master\\book.pdf"):
    html_files = []
    for index, html in enumerate(htmls):
        file = str(index) + ".html"
        html_files.append(file)
        with open(file, "w", encoding="utf-8") as f:
            f.write(html)

    options = {
        "user-style-sheet": "default.css",
        "page-size": "Letter",
        "margin-top": "0.75in",
        "margin-right": "0.75in",
        "margin-bottom": "0.75in",
        "margin-left": "0.75in",
        "encoding": "UTF-8",
        "custom-header": [("Accept-Encoding", "gzip")],
        "cookie": [
            ("cookie-name1", "cookie-value1"), ("cookie-name2", "cookie-value2")
        ],
        "outline-depth": 10,
    }
    try:
        print("生成PDF文件中，请耐心等待...")
        if os.path.exists(pdf_filepath): os.remove(pdf_filepath)
        print(html_files)
        pdfkit.from_file(html_files, pdf_filepath, options=options, configuration=config_pdf)
    except Exception as e:
        print("生成pdf报错")
        print(e)

    for i in html_files:
        os.remove(i)

    print("已制作电子书在当前目录！")


if __name__ == '__main__':
    # 这个模板是默认的，无需修改
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
    <h1>{title}</h1>
    <p>{create_time}</p>
    <p>{text}</p>
    </body>
    </html>
    """

    # 请先登录你有权限查看的星球的账号，进入该星球页面
    # 请使用谷歌浏览器刷新页面，在 Network 面板的抓包内容中找到 topics?... 这样的请求，返回的是 json 内容
    # 将这个包的 cookie 部分复制到 headers 部分的 Cookie 一栏
    # 将这个请求的 url，域名为 api.zsxq.com 开头的，复制到下面 start_url 的部分
    headers = {
        'Cookie': '_uab_collina=xxxxx; _uab_collina=xxxxx; sensorsdata2015jssdkcross=xxxxxxxx; zsxq_access_token=xxxxx; abtest_env=xxxxx',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.65 Safari/537.36'
    }
    start_url = 'https://api.zsxq.com/v2/groups/xxxxxxxxxxxxxxx/topics?scope=all&count=20' #根据需要替换url

    # 只取大于等于 after ，小于等于 before 的日期时间的文章，可以省略这俩参数，获取所有的历史文章
    # 下面这里我演示的是一段时间的拆分获取 pdf，可以批量生成多个，用于内容跨度时间长，内容非常多的星球，你可以自己看着改
    time_period = [
        ("2021-11-01 00:00", "2021-11-30 23:59"),
        ("2021-04-01 00:00", "2021-06-30 23:59"),
        ("2021-01-01 00:00", "2021-03-31 23:59"),
        ("2020-10-01 00:00", "2020-12-31 23:59"),
        ("2020-07-01 00:00", "2020-09-30 23:59"),
        ("2020-04-01 00:00", "2020-06-30 23:59"),
        ("2020-01-01 00:00", "2020-03-31 23:59"),
        ("2019-10-01 00:00", "2019-12-31 23:59"),
        ("2019-07-01 00:00", "2019-09-30 23:59"),
        ("2019-04-01 00:00", "2019-06-30 23:59"),
        ("2019-01-01 00:00", "2019-03-31 23:59"),
        ("2018-10-01 00:00", "2018-12-31 23:59"),
        ("2018-07-01 00:00", "2018-09-30 23:59"),
        ("2018-04-01 00:00", "2018-06-30 23:59"),
    ]
    # for period in time_period:
    pdf_filepath = "你的知识星球%s-%s.pdf" % (
    time_period[1][0][:10].replace("-", ""), time_period[1][1][:10].replace("-", ""))

    htmls = []
    num = 1
    print(start_url, headers)
    print(pdf_filepath)
    ht = get_data(start_url, headers)
    print("ht: ", ht)
    make_pdf(ht, pdf_filepath=pdf_filepath)

    # 如果你想获取该星球的所有内容，请用这几句代码，但当内容较多的时候，生成 pdf 会极慢
    # htmls = []
    # num = 1
    # make_pdf(get_data(start_url, headers))
