from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as Ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
import os
import random
import cv2
import numpy as np
import undetected_chromedriver.v2 as uc


class Code():
    '''
    滑动验证码破解
    '''

    def __init__(self, slider_ele=None, background_ele=None, count=1, save_image=False):
        '''

        :param slider_ele:
        :param background_ele:
        :param count:  验证重试次数
        :param save_image:  是否保存验证中产生的图片， 默认 不保存
        '''

        self.count = count
        self.save_images = save_image
        self.slider_ele = slider_ele
        self.background_ele = background_ele

    def get_slide_locus(self, distance):
        #计算出一个滑动轨迹
        distance += 8
        v = 0
        m = 0.3
        # 保存0.3内的位移
        tracks = []
        current = 0
        mid = distance * 4 / 5
        while current <= distance:
            if current < mid:
                a = 2
            else:
                a = -3
            v0 = v
            s = v0 * m + 0.5 * a * (m ** 2)
            current += s
            tracks.append(round(s))
            v = v0 + a * m
        # 由于计算机计算的误差，导致模拟人类行为时，会出现分布移动总和大于真实距离，这里就把这个差添加到tracks中，也就是最后进行一步左移。
        # tracks.append(-(sum(tracks) - distance * 0.5))
        # tracks.append(10)
        return tracks

    def slide_verification(self, driver, slide_element, distance):
        '''

        :param driver: driver对象
        :param slide_element: 滑块元祖
        :type   webelement
        :param distance: 滑动距离
        :type: int
        :return:
        '''
        # 获取滑动前页面的url网址
        start_url = driver.current_url
        print('滑动距离是: ', distance)
        # 根据滑动的距离生成滑动轨迹
        locus = self.get_slide_locus(distance)

        print('生成的滑动轨迹为:{},轨迹的距离之和为{}'.format(locus, distance))

        # 按下鼠标左键
        ActionChains(driver).click_and_hold(slide_element).perform()

        time.sleep(0.5)

        # 遍历轨迹进行滑动
        for loc in locus:
            time.sleep(0.01)
            # 此处记得修改scrapy的源码 selenium\webdriver\common\actions\pointer_input.py中将DEFAULT_MOVE_DURATION改为50，否则滑动很慢
            ActionChains(driver).move_by_offset(loc, random.randint(-5, 5)).perform()
            ActionChains(driver).context_click(slide_element)

        # 释放鼠标
        ActionChains(driver).release(on_element=slide_element).perform()

        # # 判断是否通过验证，未通过下重新验证
        # time.sleep(2)
        # # 滑动之后的yurl链接
        # end_url = driver.current_url

        # if start_url == end_url and self.count > 0:
        #     print('第{}次验证失败，开启重试'.format(6 - self.count))
        #     self.count -= 1
        #     self.slide_verification(driver, slide_element, distance)

    def onload_save_img(self, url, filename="image.png"):
        '''
        下载图片并保存
        :param url: 图片网址
        :param filename: 图片名称
        :return:
        '''
        try:
            response = requests.get(url)
        except Exception as e:
            print('图片下载失败')
            raise e
        else:
            with open(filename, 'wb') as f:
                f.write(response.content)

    def get_element_slide_distance(self, slider_ele, background_ele, correct=0):
        '''
        根据传入滑块， 和背景的节点， 计算滑块的距离
        :param slider_ele: 滑块节点参数
        :param background_ele:  背景图的节点
        :param correct:
        :return:
        '''
        # 获取验证码的图片
        slider_url = slider_ele.get_attribute('src')
        background_url = background_ele.get_attribute('src')

        # 下载验证码链接
        slider = 'slider.jpg'
        background = 'background.jpg'

        self.onload_save_img(slider_url, slider)

        self.onload_save_img(background_url, background)

        # 进行灰度图片, 转化为numpy 中的数组类型数据
        slider_pic = cv2.imread(slider, 0)
        background_pic = cv2.imread(background, 0)

        # 获取缺口数组的形状
        width, height = slider_pic.shape[::-1]

        # 将处理之后的图片另存
        slider01 = 'slider01.jpg'
        slider02 = 'slider02.jpg'
        background01 = 'background01.jpg'

        cv2.imwrite(slider01, slider_pic)
        cv2.imwrite(background01, background_pic)

        # 读取另存的滑块
        slider_pic = cv2.imread(slider01)

        # 进行色彩转化
        slider_pic = cv2.cvtColor(slider_pic, cv2.COLOR_BGR2GRAY)

        # 获取色差的绝对值
        slider_pic = abs(255 - slider_pic)
        # 保存图片
        cv2.imwrite(slider02, slider_pic)
        # 读取滑块
        slider_pic = cv2.imread(slider02)

        # 读取背景图
        background_pic = cv2.imread(background01)

        # 展示图片
        # cv2.imshow('gray1', slider_pic)  # gray1，gray2是窗口名称
        # cv2.imshow('gray2', background_pic)
        #
        # # 释放资源
        # cv2.waitKey(0)  # 按任意键退出图片展示
        # cv2.destroyAllWindows()
        time.sleep(3)

        # 必脚两张图的重叠部分
        result = cv2.matchTemplate(slider_pic, background_pic, cv2.TM_CCOEFF_NORMED)

        # 通过数组运算，获取图片缺口位置
        top, left = np.unravel_index(result.argmax(), result.shape)

        # 背景图缺口坐标
        print('当前滑块缺口位置', (left, top, left + width, top + height))

        # 判读是否需求保存识别过程中的截图文件
        if self.save_images:
            loc = [(left + correct, top + correct), (left + width - correct, top + height - correct)]
            self.image_crop(background, loc)

        else:
            # 删除临时文件
            os.remove(slider01)
            os.remove(slider02)
            os.remove(background01)
            os.remove(background)
            os.remove(slider)
            # print('删除')
            # os.remove(slider)
        # 返回需要移动的位置距离
        return left

    def image_crop(self, image, loc):
        cv2.rectangle(image, loc[0], loc[1], (7, 249, 151), 2)
        cv2.imshow('Show', image)
        # cv2.imshow('Show2', slider_pic)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


class Login(object):
    def __init__(self, user, password, retry):
        self.browser = uc.Chrome() #还有一个坑， chrome()实例化的时候会去自动下载chromedriver和chrome版本一致- 最新的版本
        self.wait = WebDriverWait(self.browser, 20)
        self.url = 'https://www.zhihu.com/signin'
        self.sli = Code()
        self.user = user
        self.password = password
        self.retry = retry  # 重试次数

    def login_baidu(self):
        # 请求网址
        self.browser.get(self.url)
        login_element = self.browser.find_element_by_xpath(
            '//*[@id="root"]/div/main/div/div/div/div[1]/div/form/div[1]/div[2]')
        self.browser.execute_script("arguments[0].click();", login_element)

        # 输入账号
        username = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-account input'))
        )
        username.send_keys(self.user)
        # 输入密码
        password = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-password input'))
        )
        password.send_keys(self.password)

        # 登录框
        submit = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
        )

        time.sleep(3)
        submit.click()
        time.sleep(3)

        k = 1
        # while True:
        while k < self.retry:
            # 获取滑动前页面的url网址
            # 1. 获取原图
            bg_img = self.wait.until(
                Ec.presence_of_element_located((By.CSS_SELECTOR, '.yidun_bgimg .yidun_bg-img'))
            )
            background_url = bg_img.get_attribute('src')
            backgroup = "background.jpg"
            self.sli.onload_save_img(background_url, backgroup)

            # 获取验证码滑动距离
            baidu = BaiDuLogin("d0SWmXg9td3463yr5Up3RYhG", "VlqbdG99Wal8Wb6zH4DkFgwLQt2ey9cF")
            distance = baidu.recongnize(baidu.get_access_token(), backgroup)
            print('滑动距离是', distance)

            # 2. 乘缩放比例， -去  滑块前面的距离  下面给介绍
            distance = distance - 4
            print('实际滑动距离是', distance)

            # 滑块对象
            element = self.browser.find_element_by_css_selector(
                '.yidun_slider')
            # 滑动函数
            self.sli.slide_verification(self.browser, element, distance)

            # 滑动之后的url链接
            time.sleep(5)
            # 登录框
            try:
                submit = self.wait.until(
                    Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
                )
                submit.click()
                time.sleep(3)
            except:
                pass

            end_url = self.browser.current_url
            print(end_url)

            if end_url == "https://www.zhihu.com/":
                return self.get_cookies()
            else:
                time.sleep(3)
                k += 1

        return None

    def login(self):
        # 请求网址
        self.browser.get(self.url)
        login_element = self.browser.find_element_by_xpath(
            '//*[@id="root"]/div/main/div/div/div/div[1]/div/form/div[1]/div[2]')
        self.browser.execute_script("arguments[0].click();", login_element)

        # 输入账号
        username = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-account input'))
        )
        username.send_keys(self.user)
        # 输入密码
        password = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-password input'))
        )
        password.send_keys(self.password)


        # 登录框
        submit = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
        )

        time.sleep(3)
        submit.click()
        time.sleep(3)

        k = 1
        # while True:
        while k < self.retry:
            # 获取滑动前页面的url网址
            # 1. 获取原图
            bg_img = self.wait.until(
                Ec.presence_of_element_located((By.CSS_SELECTOR, '.yidun_bgimg .yidun_bg-img'))
            )
            # 获取滑块链接
            # front_img = self.wait.until(
            #     Ec.presence_of_element_located(
            #         (By.CSS_SELECTOR, "#cdn2")))
            front_img = self.wait.until(
                Ec.presence_of_element_located((By.CSS_SELECTOR, '.yidun_bgimg .yidun_jigsaw'))
            )

            # 获取验证码滑动距离
            distance = self.sli.get_element_slide_distance(front_img, bg_img)
            print('滑动距离是', distance)

            # 2. 乘缩放比例， -去  滑块前面的距离  下面给介绍
            distance = distance - 4
            print('实际滑动距离是', distance)

            # 滑块对象
            element = self.browser.find_element_by_css_selector(
                '.yidun_slider')
            # 滑动函数
            self.sli.slide_verification(self.browser, element, distance)

            # 滑动之后的url链接
            time.sleep(5)
            # 登录框
            try:
                submit = self.wait.until(
                    Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
                )
                submit.click()
                time.sleep(3)
            except:
                pass

            end_url = self.browser.current_url
            print(end_url)

            if end_url == "https://www.zhihu.com/":
                return self.get_cookies()
            else:
                time.sleep(3)
                k += 1

        return None

    def get_cookies(self):
        '''
        登录成功后 保存账号的cookies
        :return:
        '''
        cookies = self.browser.get_cookies()
        self.cookies = ''
        for cookie in cookies:
            self.cookies += '{}={};'.format(cookie.get('name'), cookie.get('value'))
        return cookies

    def __del__(self):
        self.browser.close()
        print('界面关闭')
        # self.display.stop()

class BaiDuLogin():
    def __init__(self, ak, sk):
        self.ak = ak
        self.sk = sk

    def get_access_token(self):
        import requests

        # client_id 为官网获取的AK， client_secret 为官网获取的SK
        host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={}&client_secret={}'.format(self.ak, self.sk)
        response = requests.get(host)
        if response.status_code == 200:
            return response.json()["access_token"]
        return None

    def recongnize(self, access_token, image_file):
        import base64
        import json

        '''
        easydl物体检测
        '''

        request_url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/detection/zhihu"

        with open(image_file, 'rb') as f:
            base64_data = base64.b64encode(f.read())
            s = base64_data.decode('UTF8')

        params = {"image": s}
        params = json.dumps(params)
        request_url = request_url + "?access_token=" + access_token
        headers = {'Content-Type': 'application/json'}
        response = requests.post(request_url, headers=headers, data=params)
        re_json = response.json()
        if "results" not in re_json:
            return None
        if len(response.json()["results"]) == 0:
            return None
        if "location" not in response.json()["results"][0]:
            return None
        return response.json()["results"][0]["location"]["left"]

if __name__ == "__main__":
    #opencv识别滑动验证码可能失败， 机器学习识别概率很高
    l = Login("18782902020", "admin23", 6)
    cookie = l.login_baidu()

    # baidu = BaiDuLogin("d0SWmXg9td3463yr5Up3RYhG", "VlqbdG99Wal8Wb6zH4DkFgwLQt2ey9cF")
    # print(baidu.recongnize(baidu.get_access_token(), "slide.jpg"))
