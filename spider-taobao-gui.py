"""
⚠️免责声明 (Disclaimer)：
1.本项目（spider_taobao_goods）及其中包含的所有代码，仅供个人学习、技术研究和交流使用，严禁用于任何商业用途或非法盈利活动。

2.爬虫抓取的所有数据（包括但不限于商品信息、价格等）版权均归原平台（淘宝）及相关权利人所有。本项目不存储、不拥有、不主张任何数据的所有权。

3.使用者在使用本代码时，必须遵守目标网站的 robots.txt 协议、相关服务条款以及国家法律法规。请务必控制抓取频率，不得对目标网站服务器造成任何恶意攻击或过度负载。

4.任何个人或组织因使用、复制、修改或传播本代码而产生的任何直接或间接的法律责任及后果，均由使用者自行承担，本项目作者概不负责。
"""

"""
淘宝商品爬虫 - 图形界面版（GUI）

功能：
  1. 弹窗输入：关键词、最大抓取页数、全新 cookies 字符串
  2. 保存方式二选一：
     - MongoDB：手动填写数据库名、集合名
     - CSV：自动命名「淘宝{关键词}商品.csv」
  3. cookies 相关错误以红色文字输出到窗口

运行：python spider-taobao-gui.py
"""
import os
import re
import csv
import json
import time
import queue
import hashlib
import threading
import requests
from urllib.parse import quote
from jsonpath import jsonpath

import tkinter as tk
from tkinter import scrolledtext

try:
    import pymongo
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False


# ================= 基础配置 =================
APP_KEY = "12574478"
API = "mtop.relationrecommend.wirelessrecommend.recommend"
VERSION = "2.0"
URL = f"https://h5api.m.taobao.com/h5/{API}/{VERSION}/"
PAGE_SIZE = 48
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))   # CSV 保存到脚本所在目录

headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "referer": "https://uland.taobao.com/sem/tbsearch?tab=all",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
}


# ================= 日志队列（跨线程安全） =================
LOG_QUEUE = queue.Queue()


def log(msg, color="black"):
    """把日志放进队列，由主线程的轮询函数统一写到窗口。"""
    LOG_QUEUE.put((msg, color))


# ================= cookie 解析 =================
def parse_cookies(cookie_str):
    """把 cookie 字符串转成 dict。支持浏览器格式 k1=v1; k2=v2 或 JSON 格式。"""
    cookie_str = cookie_str.strip()
    if not cookie_str:
        return {}

    # 兼容 JSON 格式（{"a":"b", ...}）
    if cookie_str.startswith("{"):
        try:
            return json.loads(cookie_str)
        except Exception:
            return {}

    cookies = {}
    # 浏览器 Cookie 请求头格式，用第一个 = 切分（值里可能还有 =）
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


# ================= 构造请求 data =================
def build_data(keyword, page, total_page, total_results, cna):
    """构造 mtop 的 data 字段。page / totalPage / totalResults 是分页关键参数。"""
    search_params = {
        "device": "HMA-AL00", "isBeta": "false", "grayHair": "false", "from": "nt_history",
        "brand": "HUAWEI", "info": "wifi", "index": "4", "rainbow": "", "schemaType": "auction",
        "elderHome": "false", "isEnterSrpSearch": "true", "newSearch": "false", "network": "wifi",
        "subtype": "", "hasPreposeFilter": "false", "prepositionVersion": "v2", "client_os": "Android",
        "gpsEnabled": "false", "searchDoorFrom": "srp", "debug_rerankNewOpenCard": "false",
        "homePageVersion": "v7", "searchElderHomeOpen": "false", "search_action": "initiative",
        "sugg": "_4_1", "sversion": "13.6", "style": "list", "ttid": "600000@taobao_pc_10.7.0",
        "needTabs": "true", "areaCode": "CN", "vm": "nw", "countryNum": "156", "m": "pc_sem",
        "page": str(page), "n": PAGE_SIZE, "q": quote(keyword), "qSource": "url",
        "pageSource": "tbpc.pc_sem_alimama/a.201867-main.d2_first.3ab72a89wOAj5i",
        "tab": "all", "pageSize": PAGE_SIZE, "totalPage": total_page, "totalResults": total_results,
        "sourceS": "0", "sort": "_coefp", "bcoffset": "", "ntoffset": "", "filterTag": "",
        "service": "", "prop": "", "loc": "", "start_price": None, "end_price": None,
        "startPrice": None, "endPrice": None, "itemIds": None, "p4pIds": None, "categoryp": "",
        "myCNA": cna, "clk1": "173d6ef2a0801e66dee077501b3849e5",
        "refpid": "mm_26632258_3504122_32538762",
    }
    data = {"appId": "43356", "params": json.dumps(search_params, separators=(',', ':'))}
    return json.dumps(data, separators=(',', ':'))


# ================= 生成签名 =================
def make_sign(token, t, data_str):
    """sign = md5(token & t & appKey & data)"""
    raw = f"{token}&{t}&{APP_KEY}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ================= 发起一次请求 =================
def fetch_page(session, keyword, page, total_page, total_results):
    token = session.cookies.get("_m_h5_tk")
    if not token:
        raise RuntimeError("cookie 里缺少 _m_h5_tk，请重新复制完整 cookie")
    # 签名用的 token 是 _m_h5_tk 的前半段（下划线之前），不是整个值
    token = token.split("_")[0]

    t = int(time.time() * 1000)
    data_str = build_data(keyword, page, total_page, total_results, session.cookies.get("cna", ""))
    params = {
        "jsv": "2.7.2",
        "appKey": APP_KEY,
        "t": str(t),
        "sign": make_sign(token, t, data_str),
        "api": API,
        "v": VERSION,
        "type": "jsonp",
        "dataType": "jsonp",
        "callback": "mtopjsonp3",
        "data": data_str,
    }
    resp = session.get(URL, params=params, timeout=20)
    return resp.text


# ================= 解析响应 =================
def parse_response(text):
    """把 jsonp 抠出来转 dict，检查 ret 是否成功；失败抛异常（供上层红色输出）。"""
    m = re.search(r'mtopjsonp3\((.*)\)\s*$', text, re.S)
    if not m:
        raise RuntimeError(f"响应格式异常：{text[:150]}")
    goods_json = json.loads(m.group(1))

    ret = goods_json.get("ret", [])
    ret_msg = ret[0] if ret else ""
    if "SUCCESS" not in ret_msg:
        if "TOKEN" in ret_msg:
            raise RuntimeError("token 已过期（FAIL_SYS_TOKEN_EXOIRED），请重新复制最新 cookie")
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
    """从单条商品节点取出标题/价格/销量/店铺/地址。"""
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


# ================= 数据保存 =================
def sanitize_filename(name):
    """去掉文件名里非法的字符。"""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name


def save_csv(keyword, goods):
    filename = sanitize_filename(f"淘宝{keyword}商品.csv")
    path = os.path.join(SAVE_DIR, filename)
    # utf-8-sig 带 BOM，Excel 打开不乱码
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["标题", "价格", "下单人数", "店铺名称", "店铺地址"])
        for g in goods:
            writer.writerow([g["title"], g["price"], g["sales"], g["shop"], g["address"]])
    return path


def save_mongodb(db_name, coll_name, goods):
    if not HAS_PYMONGO:
        raise RuntimeError("未安装 pymongo，请先 pip install pymongo")
    # serverSelectionTimeoutMS 让「MongoDB 没启动」时快速报错，而不是卡死
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")   # 触发连接，连不上会抛异常
        coll = client[db_name][coll_name]
        docs = [dict(g) for g in goods]
        if docs:
            coll.insert_many(docs)
        return len(docs)
    finally:
        client.close()   # 关闭连接和后台线程，避免程序结束后还残留


# ================= 爬取主流程（在工作线程里跑） =================
def crawl_worker(keyword, max_page, cookie_str, save_mode, db_name, coll_name, on_done):
    success = False
    try:
        cookies = parse_cookies(cookie_str)
        if not cookies:
            log("❌ cookie 字符串为空或无法解析", "red")
            return
        if "_m_h5_tk" not in cookies:
            log("❌ cookie 里缺少 _m_h5_tk（可能复制不完整或已失效），请重新复制完整 cookie", "red")
            return
        log("✅ cookie 解析成功", "green")

        session = requests.Session()
        session.headers.update(headers)
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=".taobao.com")

        all_goods = []
        page = 1
        total_page = 0      # 总页数，从第一页响应里拿
        total_results = 0   # 总结果数，从第一页响应里拿

        while page <= max_page:
            log(f"正在抓取第 {page} 页 ...")
            text = fetch_page(session, keyword, page, total_page, total_results)
            goods_json = parse_response(text)

            tr = recursive_find(goods_json, "totalResults")
            tp = recursive_find(goods_json, "totalPage")
            if tr is not None:
                total_results = int(tr)
            if tp is not None:
                total_page = int(tp)

            items = jsonpath(goods_json, '$.data.itemsArray')
            goods_list = items[0] if items else []
            if not goods_list:
                log("⚠️ 本页没有商品数据，停止翻页", "red")
                break

            for g in goods_list:
                all_goods.append(parse_goods(g))
            log(f"    第 {page} 页抓到 {len(goods_list)} 条，累计 {len(all_goods)} 条", "green")

            if total_page and page >= total_page:
                break
            page += 1

        if not all_goods:
            log("⚠️ 没有抓到任何数据", "red")
            return

        if save_mode == "csv":
            path = save_csv(keyword, all_goods)
            log(f"✅ 已保存 CSV：{path}", "green")
        else:
            cnt = save_mongodb(db_name, coll_name, all_goods)
            log(f"✅ 已保存 MongoDB：库「{db_name}」集合「{coll_name}」，共 {cnt} 条", "green")

        log(f"🎉 全部完成，共抓取 {len(all_goods)} 条商品", "green")
        success = True

    except Exception as e:
        log(f"❌ {e}", "red")
    finally:
        on_done(success)


# ================= 图形界面 =================
class TaobaoApp:
    def __init__(self, root):
        self.root = root
        self.keyword_var = tk.StringVar()
        self.page_var = tk.StringVar(value="1")
        self.save_mode = tk.StringVar(value="csv")
        self.db_name_var = tk.StringVar()
        self.coll_name_var = tk.StringVar()
        self._build_ui()
        self.root.after(100, self._poll_log)

    def _build_ui(self):
        self.root.title("淘宝商品爬虫")
        self.root.geometry("700x760")
        self.root.minsize(620, 700)
        pad = dict(padx=8, pady=4)

        # 免责声明（顶部醒目位置）
        tk.Label(
            self.root,
            text="免责声明：该脚本仅供爬虫数据科学研究学习，请用户自行获取相关网站的数据采集授权",
            fg="#c0392b",                       # 深红字
            bg="#fdecea",                       # 浅红底
            font=("Microsoft YaHei", 10, "bold"),
            wraplength=640,
            justify="center",
            padx=10, pady=6,
        ).grid(row=0, column=0, columnspan=2, sticky="we", padx=8, pady=(8, 6))

        # 关键词
        tk.Label(self.root, text="关键词：").grid(row=1, column=0, sticky="e", **pad)
        tk.Entry(self.root, textvariable=self.keyword_var, width=42).grid(row=1, column=1, sticky="w", **pad)

        # 页数
        tk.Label(self.root, text="最大抓取页数：").grid(row=2, column=0, sticky="e", **pad)
        tk.Entry(self.root, textvariable=self.page_var, width=10).grid(row=2, column=1, sticky="w", **pad)

        # cookies
        tk.Label(self.root, text="Cookies 字符串：").grid(row=3, column=0, sticky="ne", **pad)
        self.cookie_text = scrolledtext.ScrolledText(self.root, height=6, width=62)
        self.cookie_text.grid(row=3, column=1, sticky="we", **pad)
        tk.Label(self.root, text="格式：k1=v1; k2=v2; ...（浏览器 Cookie 请求头或 document.cookie）",
                 fg="#888888").grid(row=4, column=1, sticky="w", padx=8)

        # 保存方式
        tk.Label(self.root, text="保存方式：").grid(row=5, column=0, sticky="e", **pad)
        mode_frame = tk.Frame(self.root)
        mode_frame.grid(row=5, column=1, sticky="w", **pad)
        tk.Radiobutton(mode_frame, text="CSV（自动命名）", variable=self.save_mode,
                       value="csv", command=self._on_mode_change).pack(side="left")
        tk.Radiobutton(mode_frame, text="MongoDB", variable=self.save_mode,
                       value="mongodb", command=self._on_mode_change).pack(side="left", padx=(14, 0))

        # MongoDB 库名 / 集合名
        tk.Label(self.root, text="MongoDB 数据库名：").grid(row=6, column=0, sticky="e", **pad)
        self.db_name_entry = tk.Entry(self.root, textvariable=self.db_name_var, width=24)
        self.db_name_entry.grid(row=6, column=1, sticky="w", **pad)

        tk.Label(self.root, text="集合名：").grid(row=7, column=0, sticky="e", **pad)
        self.coll_name_entry = tk.Entry(self.root, textvariable=self.coll_name_var, width=24)
        self.coll_name_entry.grid(row=7, column=1, sticky="w", **pad)

        # 开始按钮
        self.start_btn = tk.Button(self.root, text="开始抓取", command=self._start, height=2)
        self.start_btn.grid(row=8, column=0, columnspan=2, sticky="we", padx=20, pady=8)

        # 日志输出
        self.log_text = scrolledtext.ScrolledText(self.root, height=14, width=88, state="disabled")
        self.log_text.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 10))
        self.log_text.tag_config("red", foreground="red")
        self.log_text.tag_config("green", foreground="#1a7f37")

        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(9, weight=1)

        self._on_mode_change()

    def _on_mode_change(self):
        """切换保存方式时，启用/禁用 MongoDB 的库名、集合名输入框。"""
        state = "normal" if self.save_mode.get() == "mongodb" else "disabled"
        self.db_name_entry.config(state=state)
        self.coll_name_entry.config(state=state)

    def _start(self):
        keyword = self.keyword_var.get().strip()
        page_text = self.page_var.get().strip()
        cookie_str = self.cookie_text.get("1.0", "end").strip()
        save_mode = self.save_mode.get()
        db_name = self.db_name_var.get().strip()
        coll_name = self.coll_name_var.get().strip()

        # 输入校验，错误统一红色输出
        if not keyword:
            log("❌ 请输入关键词", "red")
            return
        try:
            max_page = int(page_text)
            if max_page <= 0:
                raise ValueError
        except ValueError:
            log("❌ 最大抓取页数必须是正整数", "red")
            return
        if not cookie_str:
            log("❌ 请输入 cookies 字符串", "red")
            return
        if save_mode == "mongodb":
            if not HAS_PYMONGO:
                log("❌ 未安装 pymongo，请先 pip install pymongo", "red")
                return
            if not db_name or not coll_name:
                log("❌ MongoDB 模式需要填写数据库名和集合名", "red")
                return

        self.start_btn.config(state="disabled")
        log(f"开始抓取关键词「{keyword}」，最多 {max_page} 页，保存方式：{save_mode}", "green")
        threading.Thread(
            target=crawl_worker,
            args=(keyword, max_page, cookie_str, save_mode, db_name, coll_name, self._on_done),
            daemon=True,
        ).start()

    def _on_done(self, success):
        """爬取结束（在工作线程里被调用），切回主线程恢复按钮；成功则自动退出程序。"""
        self.root.after(0, lambda: self.start_btn.config(state="normal"))
        if success:
            log("程序将在 3 秒后自动退出", "green")
            # 成功后自动关闭窗口、结束进程；出错则保持窗口，方便改完重试
            self.root.after(3000, self.root.destroy)

    def _poll_log(self):
        """主线程定期把日志队列里的内容写到窗口。"""
        try:
            while True:
                msg, color = LOG_QUEUE.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n", color)
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)


def main():
    root = tk.Tk()
    TaobaoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
