import os
import json
import sqlite3
from _io import BytesIO

import requests
from lxml import html
from PIL import Image

# 解决requests以及urllib3日志太杂的问题
import logging

logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("requests.packages.urllib3").setLevel(logging.ERROR)

# 唇膏、唇釉、唇油、唇颊霜
urls = [
    ("https://www.yslbeautycn.com/makeup-lipstick", "lipstick.html"),
    ("https://www.yslbeautycn.com/makeup-lip-vernis", "lip_vernis.html"),
    ("https://www.yslbeautycn.com/makeup-lipoil", "lipoil.html"),
    ("https://www.yslbeautycn.com/makeup-kiss_brush", "kiss_brush.html"),
]


def get_data_from_web(url, html_filename):
    # 从网络获取，写入到文件
    req = requests.get(url, verify=False)
    req.encoding = "utf-8"
    with open(html_filename, mode="w", encoding="utf-8") as fp:
        fp.write(req.text)
    src = req.text

    return src


def get_data_from_file(html_filename):
    # 或，从已保存的文件中获取
    with open(html_filename, mode="r", encoding="utf-8") as fp:
        src = fp.read()

    return src


def parse_data(src):
    # HTML解析
    et = html.fromstring(src)

    # 整理数据
    product_items_list = et.xpath("//div[@class='list-product']//div[@class='plp-slide']")
    final_list = []
    for i in product_items_list:
        data = {}

        data["img_box_src"] = i.xpath(".//div[@class='img-box']//img/@lazysrc")
        data["img_box_src"] = data["img_box_src"][0] if data["img_box_src"] else ""
        data["goods_tit"] = i.xpath(".//p[@class='goods-tit']/a/text()")
        data["goods_tit"] = data["goods_tit"][0] if data["goods_tit"] else ""
        data["goods_introudce"] = i.xpath(".//p[@class='goods-introudce']/a/text()")
        data["goods_introudce"] = data["goods_introudce"][0] if data["goods_introudce"] else ""

        goods_classify = i.xpath(".//div[@class='goods-classify']//span")
        gc_list = data["goods_classify"] = []
        for gc in goods_classify:
            dgc = {}

            dgc["title"] = gc.xpath("./img/@title")
            dgc["title"] = dgc["title"][0] if dgc["title"] else ""
            dgc["title"] = dgc["title"].replace('\xa0', ' ')
            dgc["code"] = gc.xpath("./@data-code")
            dgc["code"] = dgc["code"][0] if dgc["code"] else ""
            dgc["saleprice"] = gc.xpath("./@data-saleprice")
            dgc["saleprice"] = dgc["saleprice"][0] if dgc["saleprice"] else ""
            dgc["img_src"] = gc.xpath("./img/@src")
            dgc["img_src"] = dgc["img_src"][0] if dgc["img_src"] else ""

            # 解析SKU颜色值
            if dgc["img_src"]:
                req_img = requests.get(dgc["img_src"], verify=False)
                img_data = req_img.content
                bio = BytesIO()
                bio.write(img_data)
                bio.seek(0)
                pimg = Image.open(bio)  # 读入PIL图像
                pimg.thumbnail((1, 1))  # 转换为1x1像素的图片
                r, g, b = pimg.getcolors(pimg.size[0] * pimg.size[1])[0][1]  # 形式：[(1, (223, 218, 212))]
                dgc["img_color"] = '#%02x%02x%02x' % (r, g, b)
                pimg.close()
                bio.close()
            else:
                dgc["img_color"] = ""

            gc_list.append(dgc)

        final_list.append(data)

    return final_list


def debug_print(final_list):
    # 调试输出
    for ni, i in enumerate(final_list):
        print(ni)
        for k, v in i.items():
            print("    {}: {}".format(k, repr(v)))


def dump_to_json_file(final_list):
    # 写入json
    jdata = json.dumps(final_list, ensure_ascii=False, indent=True, sort_keys=True)
    with open("makeup.json", mode="w", encoding="utf-8") as fp:
        fp.write(jdata)


def load_from_json_file():
    # 读取json
    with open("makeup.json", mode="r", encoding="utf-8") as fp:
        jdata = json.load(fp)
        return jdata


def save_to_sqlite_db_file(final_list):
    # 写入sqlite文件
    sql_conn = sqlite3.connect("makeup.db")
    c = sql_conn.cursor()
    try:
        # 删表
        c.execute("drop table makeup_products; ")
    except:
        pass
    try:
        # 建表
        c.execute(
            "create table makeup_products ("
            "  prod_id integer PRIMARY KEY autoincrement,"
            "  img_box_src char(1000),"
            "  goods_tit char(1000),"
            "  goods_introudce char(1000),"
            "  c_title char(1000),"
            "  c_code char(1000),"
            "  c_saleprice char(1000),"
            "  c_img_src char(1000),"
            "  c_img_color char(1000)"
            "); "
        )
    except:
        pass
    # 写入表数据
    for ni, i in enumerate(final_list):
        img_box_src = i["img_box_src"]
        goods_tit = i["goods_tit"]
        goods_introudce = i["goods_introudce"]
        goods_classify = i["goods_classify"]
        for gc in goods_classify:
            title = gc["title"]
            code = gc["code"]
            saleprice = gc["saleprice"]
            img_src = gc["img_src"]
            img_color = gc["img_color"]

            c.execute(
                "insert into makeup_products (img_box_src, goods_tit, goods_introudce, c_title, c_code, c_saleprice, c_img_src, c_img_color)"
                "values (?, ?, ?, ?, ?, ?, ?, ?); "
                , (img_box_src, goods_tit, goods_introudce, title, code, saleprice, img_src, img_color))

        # 写入一款产品commit一次
        sql_conn.commit()

    sql_conn.close()


if __name__ == "__main__":
    # # 加载数据-网络
    # final_list = []
    # for url, html_filename in urls:
    #     if os.path.isfile(html_filename):
    #         src = get_data_from_file(html_filename)  # html文件
    #     else:
    #         src = get_data_from_web(url, html_filename)  # web
    #     final_list += parse_data(src)  # HTML -> 数据对象
    # # 调试输出
    # debug_print(final_list)
    # # 保存数据
    # dump_to_json_file(final_list)
    # save_to_sqlite_db_file(final_list)

    # 加载数据-本地
    final_list = load_from_json_file()  # json -> 数据对象
    print(len(final_list))
    # 附加：去重
    new_final_list = []
    goods_tit_set = set()
    for i in final_list:
        gt = i.get("goods_tit").strip()
        if gt in goods_tit_set:
            continue
        goods_tit_set.add(gt)
        new_final_list.append(i)
    print(len(new_final_list))
    final_list = new_final_list
    # 调试输出
    debug_print(final_list)
    # 保存数据
    save_to_sqlite_db_file(final_list)
