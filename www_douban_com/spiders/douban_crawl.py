#!/usr/bin/env python 
# coding:utf-8
# @Time :11/24/18 10:45


import json
import sys
import time

import click

sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")

from lxml import html

from tqdm import tqdm

import requests

from common.logger import AppLogger
from configs.mongo_config import LocalMongoConfig
from common.mongo import MongDb
from www_douban_com.handler import DouBanInfoHandler

logger = AppLogger('douban.log').get_logger()


init_urls = [
            "https://www.douban.com/group/nanshanzufang/discussion?start={}",
            "https://www.douban.com/group/498004/discussion?start={}",
            "https://www.douban.com/group/106955/discussion?start={}",
            "https://www.douban.com/group/szsh/discussion?start={}",
            "https://www.douban.com/group/551176/discussion?start={}",
            "https://www.douban.com/group/SZhouse/discussion?start={}"
             ]


class DoubanCrawl(object):
    __START_URL = "https://www.douban.com/group/luohuzufang/discussion?start={}"

    __HOST = "www.douban.com"

    def __init__(self, page, log):
        self.__page = page
        self.log = log
        self.log.info("获得 {} 页之后的数据...".format(self.__page))
        self.mongo = MongDb(LocalMongoConfig.HOST,
                            LocalMongoConfig.PORT,
                            LocalMongoConfig.DB,
                            LocalMongoConfig.USER,
                            LocalMongoConfig.PASSWD,
                            log=self.log)
        self.table = "douban"
        self.request = self.__init_reqeust()
        self.douban_handler = DouBanInfoHandler()

    def __init_reqeust(self):
        headers = {
            "Host": self.__HOST,
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,ja;q=0.6",
        }
        self.request = requests.Session()
        self.request.headers = headers
        return self.request

    def __get_page_data(self, page_num=0, start_url=None):
        url = start_url.format(page_num) if start_url else self.__START_URL.format(page_num)
        resp = self.request.get(url)
        if resp is None:
            self.log.error("请求列表页出错...")
            return -1

        html_resp = html.fromstring(resp.text)

        # 遍历所有的帖子
        discussion_extract = html_resp.xpath('//div[@class="article"]//tr[@class=""]')

        item_list = []
        for per_discussion in discussion_extract:
            title = per_discussion.xpath('./td[@class="title"]/a/@title')[0]
            detail_url = per_discussion.xpath('./td[@class="title"]/a/@href')[0]
            author = per_discussion.xpath('./td[2]/a/text()')[0]
            author_url = per_discussion.xpath('./td[2]/a/@href')[0]
            comment_count_raw = per_discussion.xpath('./td[3]/text()')
            comment_count = comment_count_raw[0] if comment_count_raw else 0
            comment_date_raw = str(per_discussion.xpath('./td[4]/text()')[0])
            comment_date = "2018-" + comment_date_raw if not comment_date_raw.startswith("20") else comment_date_raw

            # titles.append(title)

            extract_info = self.douban_handler.clean_data(title)

            item = {
                "title": title,
                "detail_url": detail_url,
                "author": author,
                "author_url": author_url,
                "comment_count": comment_count,
                "comment_date": comment_date,
                "_in_time": time.strftime("%")
            }

            new_item = {**extract_info, **item}
            # print(new_item)
            item_list.append(new_item)
        self.mongo.insert_batch_data(self.table, item_list, key="detail_url")

    def start(self, *args, **kwargs):
        for url in init_urls:
            self.log.info("当前采集小组的链接是:{}".format(url))
            for i in tqdm(range(0, self.__page + 1)):
                self.log.info("当前即将采集第 {} 页".format(i))
                grab_list_page_status = self.__get_page_data(i * 25, url)
                if grab_list_page_status == -1:
                    self.log.info("当前采集列表页出错, 当前页面是第 {} 页".format(i))
                    continue
                self.log.info("当前页面采集完成: page = {}".format(i))
        self.log.info("成功退出采集程序...")


@click.command()
@click.option('--page',
              default=20,
              type=int,
              help=u'采集总页数')
def main(page):
    try:
        DoubanCrawl(page, logger).start()
    except Exception as e:
        logger.error("采集异常退出: ")
        logger.exception(e)


if __name__ == '__main__':
    main()
