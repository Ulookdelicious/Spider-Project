"""
⚠️免责声明 (Disclaimer)：
1.本项目（spider_taobao_goods）及其中包含的所有代码，仅供个人学习、技术研究和交流使用，严禁用于任何商业用途或非法盈利活动。

2.爬虫抓取的所有数据（包括但不限于商品信息、价格等）版权均归原平台（淘宝）及相关权利人所有。本项目不存储、不拥有、不主张任何数据的所有权。

3.使用者在使用本代码时，必须遵守目标网站的 robots.txt 协议、相关服务条款以及国家法律法规。请务必控制抓取频率，不得对目标网站服务器造成任何恶意攻击或过度负载。

4.任何个人或组织因使用、复制、修改或传播本代码而产生的任何直接或间接的法律责任及后果，均由使用者自行承担，本项目作者概不负责。
"""

import re
import time
import json
import hashlib
import requests
from urllib.parse import quote
from jsonpath import jsonpath

# ================= 基础配置 =================
APP_KEY = "12574478"
API = "mtop.relationrecommend.wirelessrecommend.recommend"
VERSION = "2.0"
URL = f"https://h5api.m.taobao.com/h5/{API}/{VERSION}/"

# 输入抓取关键词
key_word = input('请输入抓取数据的关键词：')
# 搜索关键词
KEYWORD = f"{key_word}"
# 每页条数（和 n 一致）
PAGE_SIZE = 48
# 最多抓几页，按需改
MAX_PAGE = int(input())

# 定义请求头
headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "referer": "https://uland.taobao.com/sem/tbsearch?keyword=%E7%94%B5%E8%84%91&q=%E7%94%B5%E8%84%91&tab=all",
    "sec-ch-ua": "\"Google Chrome\";v=\"155\", \"Chromium\";v=\"155\", \"Not(A:Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "script",
    "sec-fetch-mode": "no-cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
}

# 定义 cookies 信息
# 每次运行前从浏览器重新复制一份，重点保证 _m_h5_tk / _m_h5_tk_enc 是新的（有效期约2小时）
cookies = {
    "thw": "cn",
    "cna": "HFKhIkyGg3gCAXjry6wmuLdT",
    "tracknick": "tb997566565",
    "t": "65ca08a32c9510f489b505eddbb75541",
    "cookie2": "1df4c211903380ed3fea321bb439bd3b",
    "_tb_token_": "e0336a69e676e",
    "xlly_s": "1",
    "3PcFlag": "1792932220606",
    "unb": "2209395750598",
    "uc1": "existShop=false&pas=0&cookie16=UtASsssmPlP%2Ff1IHDsDaPRu%2BPw%3D%3D&cookie15=VFC%2FuZ9ayeYq2g%3D%3D&cookie21=U%2BGCWk%2F7oPIg&cookie14=UoYXLu14%2F7vXbg%3D%3D",
    "sn": "",
    "uc3": "vt3=F8dD1fKkQrc7SqFePhE%3D&id2=UUphw2ZQNNIarOaPWQ%3D%3D&lg2=UIHiLt3xD8xYTw%3D%3D&nk2=F5RMECiW5hLCHPE%3D",
    "csg": "e2e16c63",
    "lgc": "tb997566565",
    "cancelledSubSites": "empty",
    "cookie17": "UUphw2ZQNNIarOaPWQ%3D%3D",
    "dnk": "tb997566565",
    "skt": "504b69ac66750828",
    "existShop": "MTc5MjkzMjI4OA%3D%3D",
    "uc4": "id4=0%40U2grGNnTIzsADYHtpjPLSWkJ0Cx7Xfff&nk4=0%40FY4HVZqYclwBYFVZBcWLR6Oihsuyxg%3D%3D",
    "_cc_": "WqG3DMC9EA%3D%3D",
    "_l_g_": "Ug%3D%3D",
    "sg": "586",
    "_nk_": "tb997566565",
    "cookie1": "Ane%2B7geH%2FBaC0FI1ZGBZCsdU3SCPMukQGbO66%2Ftswr8%3D",
    "wk_cookie2": "167c0fccbaddc24cb27ecaf8c0b9163e",
    "wk_unb": "UUphw2ZQNNIarOaPWQ%3D%3D",
    "sgcookie": "E1001p1Esr3qUn%2BOug7soaFPQfjWxOAm9FAH%2FWBrjrNM3zqSIRR6u96WULr7Q1wlUQRAv58r65DZfXDWfEcRcmGgqRCjwKTRtIW%2F8VjHxEqGtBU%3D",
    "mtop_partitioned_detect": "1",
    "_m_h5_tk": "bf9eeb417c0e13b1873367fc068564cf_1793035562607",
    "_m_h5_tk_enc": "9a69e45f2bd4c8ee37ea54ac1a04db0f",
    "tfstk": "hIOKNMZUvQJxQ_3iW7jVc-5ltVmmJQb5PU8zPM1C-4CJXn67Zv5he_K1jBjH-6s7whjaZ4Sn8_BWVHgimj4xQq4FOww5d7g5Ca_Yox16Ue8FaPzgVxvsenYuQ7w5V311fa7fNu_7OVC1-ZC7OTNQClsNP_sWV9w_fZQ7NJ_5PRgOzGs5N_tW5VQlfg15N3T1uRBIM_apzqFOG9IXRGFv7CncdJ8hY7N5vwBLneOVBo_F5CAOnO4um1T2IH_OMXEVJdTAOadrl8IReB5OY9OrW8yPdNkIxVXCfSeayNImJY2zUODfWi0tW8yPdN7OmVAYU8Wih",
    "isg": "BBkZMd4Ll1cWq0sGz10RdGHOKAXzpg1YUhYySjvOlcC_QjnUg_YdKIdURAY0eqWQ"
}


# ================= 构造请求的 data 参数 =================
def build_data(keyword, page, total_page=0, total_results=0):
    """构造 mtop 的 data 字段。page / totalPage / totalResults 是分页关键参数。"""
    # 内层搜索参数（从浏览器真实请求里抓下来的结构）
    search_params = {
        "device": "HMA-AL00",
        "isBeta": "false",
        "grayHair": "false",
        "from": "nt_history",
        "brand": "HUAWEI",
        "info": "wifi",
        "index": "4",
        "rainbow": "",
        "schemaType": "auction",
        "elderHome": "false",
        "isEnterSrpSearch": "true",
        "newSearch": "false",
        "network": "wifi",
        "subtype": "",
        "hasPreposeFilter": "false",
        "prepositionVersion": "v2",
        "client_os": "Android",
        "gpsEnabled": "false",
        "searchDoorFrom": "srp",
        "debug_rerankNewOpenCard": "false",
        "homePageVersion": "v7",
        "searchElderHomeOpen": "false",
        "search_action": "initiative",
        "sugg": "_4_1",
        "sversion": "13.6",
        "style": "list",
        "ttid": "600000@taobao_pc_10.7.0",
        "needTabs": "true",
        "areaCode": "CN",
        "vm": "nw",
        "countryNum": "156",
        "m": "pc_sem",
        "page": str(page),               # 第几页
        "n": PAGE_SIZE,                  # 每页条数
        "q": quote(keyword),             # 关键词（URL 编码）
        "qSource": "url",
        "pageSource": "tbpc.pc_sem_alimama/a.201867-main.d2_first.3ab72a89wOAj5i",
        "tab": "all",
        "pageSize": PAGE_SIZE,
        "totalPage": total_page,         # 总页数（第一页响应里拿到）
        "totalResults": total_results,   # 总结果数（第一页响应里拿到）
        "sourceS": "0",
        "sort": "_coefp",
        "bcoffset": "",
        "ntoffset": "",
        "filterTag": "",
        "service": "",
        "prop": "",
        "loc": "",
        "start_price": None,
        "end_price": None,
        "startPrice": None,
        "endPrice": None,
        "itemIds": None,
        "p4pIds": None,
        "categoryp": "",
        "myCNA": cookies["cna"],
        "clk1": "173d6ef2a0801e66dee077501b3849e5",
        "refpid": "mm_26632258_3504122_32538762"
    }
    # 外层结构：appId + 内层参数序列化成的字符串
    data = {
        "appId": "43356",
        "params": json.dumps(search_params, separators=(',', ':'), ensure_ascii=False)
    }
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False)


# ================= 生成签名 =================
def make_sign(token, t, data_str):
    """sign = md5(token & t & appKey & data)"""
    """详情请查看淘宝数据抓取详细文件说明"""
    raw = f"{token}&{t}&{APP_KEY}&{data_str}"
    # 哈希md5加密
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ================= 发起一次请求 =================
def fetch_page(session, page, total_page, total_results):
    token = session.cookies.get("_m_h5_tk")
    if not token:
        raise RuntimeError("cookie里缺少_m_h5_tk，请重新从浏览器复制cookie")
    # 注意：签名用的token是_m_h5_tk 的前半段（下划线之前），不是整个值
    token = token.split("_")[0]

    # 1.时间戳必须是整数毫秒
    t = int(time.time() * 1000)
    # 2.签名最后一个参数是真实data，不是字符串 'data'，本人在前期调试时因数据类型报错
    data_str = build_data(KEYWORD, page, total_page, total_results)
    # 定义params参数
    params = {
        "jsv": "2.7.2",
        "appKey": APP_KEY,
        "t": str(t),
        "sign": make_sign(token, t, data_str),     # sign参数值为字符串通过md5加密算法返回的加密值
        "api": API,
        "v": VERSION,
        "type": "jsonp",
        "dataType": "jsonp",
        "callback": "mtopjsonp3",
        "data": data_str,
    }
    response = session.get(URL, params=params, timeout=20)

    # Session 会自动更新响应里带回来的新 cookie（比如刷新的 _m_h5_tk）
    new_token = session.cookies.get("_m_h5_tk")
    if new_token and new_token != token:
        print(f"[提示] 检测到 token 已自动更新，后续请求将使用新 token")

    return response.text


# ================= 解析响应 =================
def parse_response(text):
    """把 jsonp 字符串抠出来，转成 dict，并检查 ret 是否成功。"""
    m = re.search(r'mtopjsonp3\((.*)\)\s*$', text, re.S)
    if not m:
        raise RuntimeError(f"响应格式不对，无法解析：{text[:200]}")
    goods_json = json.loads(m.group(1))

    ret = goods_json.get("ret", [])
    ret_msg = ret[0] if ret else ""
    if "SUCCESS" not in ret_msg:
        if "TOKEN" in ret_msg:
            raise RuntimeError(f"token 过期了：{ret_msg}\n请重新从浏览器复制 cookie（重点 _m_h5_tk）")
        raise RuntimeError(f"接口返回错误：{ret_msg}")
    return goods_json


def recursive_find(obj, key):
    """在 dict/list 里递归找第一个匹配 key 的值（不知道确切路径时兜底用）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return v
            r = recursive_find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for it in obj:
            r = recursive_find(it, key)
            if r is not None:
                return r
    return None


def parse_goods(goods):
    """从单条商品节点里取出需要的字段。"""
    title = jsonpath(goods, '$.title')
    price = jsonpath(goods, '$.price')
    sales = jsonpath(goods, '$.realSales')
    shop = jsonpath(goods, '$.shopInfo.title')
    addr = jsonpath(goods, '$.procity')

    title = (title[0] if title else '').replace('<span class=H>', '').replace('</span>', '')
    return {
        "title": title,
        "price": price[0] if price else '',
        "sales": sales[0] if sales else '',
        "shop": shop[0] if shop else '',
        "address": addr[0] if addr else '',
    }


# ================= 主流程 =================
def main():
    session = requests.Session()
    session.headers.update(headers)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=".taobao.com")

    page = 1
    total_page = 0      # 总页数，从第一页响应里拿
    total_results = 0   # 总结果数，从第一页响应里拿
    all_goods = []

    while page <= MAX_PAGE:
        print(f"\n========== 第 {page} 页 ==========")
        text = fetch_page(session, page, total_page, total_results)
        goods_json = parse_response(text)

        # 你说的：第二页要用的 totalResults / totalPage，在第一页响应里就有
        tr = recursive_find(goods_json, "totalResults")
        tp = recursive_find(goods_json, "totalPage")
        if tr is not None:
            total_results = int(tr)   # 响应里是字符串，转成 int 传给下一页
        if tp is not None:
            total_page = int(tp)
        print(f"[分页] totalResults={total_results}, totalPage={total_page}")

        # 取商品列表
        items = jsonpath(goods_json, '$.data.itemsArray')
        goods_list = items[0] if items else []
        if not goods_list:
            print("本页没有商品数据，停止翻页")
            break

        # 循环遍历出每件商品的节点信息
        for goods in goods_list:
            info = parse_goods(goods)
            all_goods.append(info)
            print("商品标题：", info["title"])
            print("商品价格：", info["price"])
            print("下单人数：", info["sales"])
            print("店铺名称：", info["shop"])
            print("店铺地址：", info["address"])
            print("=" * 75)

        # 如果已经拿到总页数，且当前页已是最后一页，提前结束
        if total_page and page >= total_page:
            print(f"\n已抓完所有 {total_page} 页")
            break

        page += 1

    # 打印提示
    print(f"\n共抓到 {len(all_goods)} 条商品数据")


if __name__ == "__main__":
    main()
