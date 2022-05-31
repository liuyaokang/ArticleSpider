# -*- coding: utf-8 -*-
from datetime import datetime
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from items import LagouJobItemLoader, LagouJobItem
from ArticleSpider.utils.common import get_md5
import undetected_chromedriver as uc
from pydispatch import dispatcher
from scrapy import signals
from scrapy import Spider
from scrapy.linkextractors import LinkExtractor
from scrapy.http import HtmlResponse
from scrapy.http import Request
import zipfile
import string

proxyHost = "http-dyn.abuyun.com"
proxyPort = "9020"

# 代理隧道验证信息
proxyUser = "HTDHNF44E2IJM42D"
proxyPass = "76469CCE617B8058"

def create_proxy_auth_extension(proxy_host, proxy_port,
                                proxy_username, proxy_password,
                                scheme='http', plugin_path=None):
    if plugin_path is None:
        plugin_path = r'./{}_{}@http-pro.abuyun.com_9020.zip'.format(proxy_username, proxy_password)

    manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Abuyun Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """

    background_js = string.Template(
        """
        var config = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "${scheme}",
                    host: "${host}",
                    port: parseInt(${port})
                },
                bypassList: ["foobar.com"]
            }
          };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "${username}",
                    password: "${password}"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
        );
        """
    ).substitute(
        host=proxy_host,
        port=proxy_port,
        username=proxy_username,
        password=proxy_password,
        scheme=scheme,
    )

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path


proxy_auth_plugin_path = create_proxy_auth_extension(
    proxy_host=proxyHost,
    proxy_port=proxyPort,
    proxy_username=proxyUser,
    proxy_password=proxyPass)

class LagouSpider(Spider):
    name = 'lagou'
    allowed_domains = ['www.lagou.com']
    start_urls = ['https://www.lagou.com/']

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.sub_category_urls = None
        proxy_auth_plugin_path = create_proxy_auth_extension(
            proxy_host=proxyHost,
            proxy_port=proxyPort,
            proxy_username=proxyUser,
            proxy_password=proxyPass)

        option = uc.ChromeOptions()
        option.add_argument("--start-maximized")
        option.add_extension(proxy_auth_plugin_path)

        self.browser = uc.Chrome(chrome_options=option)
        self.link_extractor = LinkExtractor()
        super(LagouSpider, self).__init__()
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        # 当爬虫退出的时候关闭chrome
        print("spider closed")
        self.browser.quit()

    def parse_list(self, response, **kwargs):
        #解析工作列表页
        job_urls = response.css(".con_list_item.default_list .list_item_top .p_top a::attr(href)").extract()
        for job_url in job_urls:
            yield Request(job_url, callback=self.parse_job)
        #解析下一页
        next_urls = response.xpath("//a[contains(text(),'下一页')]").extract()
        for next_url in next_urls:
            yield Request(next_url, callback=self.parse_list)

    def start_requests(self):
        for start_url in self.start_urls:
            self.browser.get(start_url)
            import time
            time.sleep(3)
            response = HtmlResponse(url=self.browser.current_url, body=self.browser.page_source, encoding="utf-8")
            sub_category_urls = response.css(".mainNavs .menu_box .menu_sub.dn dl dd a::attr(href)").extract()

            for sub_category_url in sub_category_urls[3:]:
                yield Request(sub_category_url, dont_filter=True, callback=self.parse_list)
                return


    def parse_job(self, response):
        #解析拉勾网的职位
        item_loader = LagouJobItemLoader(item=LagouJobItem(), response=response)
        item_loader.add_css("title", ".position-head-wrap-name::text")
        item_loader.add_value("url", response.url)
        item_loader.add_value("url_object_id", get_md5(response.url))
        item_loader.add_css("salary", ".job_request .salary::text")
        item_loader.add_xpath("job_city", "//*[@class='job_request']//span[2]/text()")
        item_loader.add_xpath("work_years", "//*[@class='job_request']//span[3]/text()")
        item_loader.add_xpath("degree_need", "//*[@class='job_request']//span[4]/text()")
        item_loader.add_xpath("job_type", "//*[@class='job_request']//span[5]/text()")

        item_loader.add_css("tags", '.position-label li::text')
        item_loader.add_css("publish_time", ".publish_time::text")
        item_loader.add_css("job_advantage", ".job-advantage p::text")
        item_loader.add_css("job_desc", ".job_bt div")
        item_loader.add_css("job_addr", ".work_addr")
        item_loader.add_css("company_name", "#job_company dt a img::attr(alt)")
        item_loader.add_css("company_url", "#job_company dt a::attr(href)")
        item_loader.add_value("crawl_time", datetime.now())

        job_item = item_loader.load_item()

        return job_item
