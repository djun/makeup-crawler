# coding=utf-8

# gevent & wsgi
from gevent import monkey, pywsgi

monkey.patch_all()

# python preset
import traceback as tb
import os
import platform
import re
import sqlite3
from operator import itemgetter
from urllib import parse

# flask
from flask import Flask, request, render_template

# ML
# import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier

# my utils
from Utils import get_logger

# version info
create_date = '2018-12-26'
update_date = '2018-12-26'
app_ver = '0.1'


def color_value_to_rgb(c):
    c = c[c.find("#") + 1:]
    r, g, b = c[0:2], c[2:4], c[4:6]
    r, g, b = int(r, 16), int(g, 16), int(b, 16)
    return r, g, b


def rgb_to_color_value(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)


if __name__ == "__main__":
    logger = get_logger("mls_web")

    pid = os.getpid()
    info = '------[{}] MLS-Web-Server {}, to {}, version {}. By DJun------'.format(pid, create_date, update_date,
                                                                                   app_ver)
    logger.info(info)

    is_win = platform.system().lower() == 'windows'
    logger.info('[{}] System is Windows: {}'.format(pid, str(is_win)))

    # mutex
    if is_win:
        import win32event, win32api  # , pywintypes

        ERROR_ALREADY_EXISTS = 183
        my_mutex = "mlsweb_server"
        logger.debug('[{}] my_mutex={}'.format(pid, my_mutex))
        mutex_handler = win32event.CreateMutex(None, False, my_mutex)  # pywintypes.FALSE
        if win32api.GetLastError() == ERROR_ALREADY_EXISTS:
            logger.info('[{}] Application already running! Quitting...'.format(pid))
            exit(0)
        logger.info('[{}] CreateMutex executed successfully!'.format(pid))

    # db - sqlite3
    sql_conn = sqlite3.connect("makeup.db")
    logger.info(msg="[MLS_WEB] DB connected!")

    # sklearn - knn
    # 查询数据
    c = sql_conn.cursor()
    c.execute(
        "select c_img_color, prod_id from makeup_products; "
    )
    data = c.fetchall()
    c.close()
    # 处理颜色字段
    new_data = []
    for color, id in data:
        if color.startswith("#"):
            r, g, b = color_value_to_rgb(color)
            new_data.append((r, g, b, id))
    # print(repr(new_data))

    # 进行knn模型训练，训练好后备用
    df = pd.DataFrame(new_data)
    knn = KNeighborsClassifier()
    knn.fit(df.iloc[:, :3], df.iloc[:, -1:])
    logger.info(msg="[MLS_WEB] ML finished!")


    # 获取搜索结果
    def get_search_result(kw):
        result = []
        c = None
        try:
            c = sql_conn.cursor()
            r, g, b = color_value_to_rgb(kw)
            knn_result = knn.kneighbors([(r, g, b)], 5, False)[0]
            knn_result = [str(int(i + 1)) for i in knn_result]  # TODO 蜜汁刚好取“i+1”才能与原表中的数据ID进行匹配，待解决
            logger.info(msg="[MLS_WEB] color: {}, got knn result: {}".format(kw, repr(knn_result)))
            # db_result_cols = None
            db_result_cols = ['ID', '主图', '标题', '介绍', '色号', '编码', '售价', '色样', '色值']
            for ni, i in enumerate(knn_result):
                # 查单条数据
                c.execute(
                    "select * from makeup_products where prod_id = {} limit 1".format(i)
                )
                db_result = c.fetchall()

                # 处理表头
                # db_result_cols = [i[0] for i in c.description] if db_result_cols is None else db_result_cols
                if not result:
                    result.append(db_result_cols)

                # 处理内容
                row = db_result[0]
                # 没有二次处理
                # result.append(row)
                # 二次处理
                new_row = []
                for nc, col in enumerate(row):
                    # 调试输出
                    if isinstance(col, str) and col.startswith("http"):
                        new_row.append("<img src={} style='width:90%; height:auto;' />".format(col))
                    else:
                        new_row.append(col)
                    logger.info(msg="[MLS_WEB] [{}] {}: {}".format(ni, db_result_cols[nc], col))
                result.append(new_row)
        except Exception as e:
            result = None
            logger.error(msg="[MLS_WEB] " + repr(e))
            logger.debug(msg="------Traceback------\n" + tb.format_exc())
        finally:
            if c is not None:
                c.close()

        return result


    # flask
    flask_app = Flask(__name__)


    @flask_app.route('/', methods=['GET'])
    def index():
        return info


    @flask_app.route('/search', methods=['GET'])
    def search():
        result = None
        if request.method == 'GET':
            try:
                remote_addr = request.remote_addr
                args = request.args
                kw = args.get("kw")
                logger.info(
                    "[MLS_WEB] received kw: {}; from {}".format(repr(kw), repr(remote_addr)))

                if kw:
                    kw = parse.unquote(kw).replace("'", "''")

                    search_result = get_search_result(kw)
                    data_list = [
                        {
                            "content": search_result,
                        }
                    ]
                    result = render_template('tmpl_search.html',
                                             title="口红色号查询 ;)",
                                             ver=app_ver, update_date=update_date,
                                             data=data_list)
            except Exception as e:
                result = None
                logger.error(msg="[MLS_WEB] " + repr(e))
                logger.debug(msg="------Traceback------\n" + tb.format_exc())

        if result is None:
            result = render_template('tmpl_search_null.html',
                                     ver=app_ver, update_date=update_date)
        return result


    # 测试获取预测结果
    # test_result = get_search_result("#DE4A3C")
    # print(test_result)
    # 测试url获取数据（复制粘贴到浏览器地址栏并访问）
    # url: http://127.0.0.1:9992/search?kw=%2523B03C79

    # server
    server = pywsgi.WSGIServer(('0.0.0.0', 9992), flask_app)  # wsgi
    # server = pywsgi.WSGIServer(('127.0.0.1', 9992), flask_app)  # wsgi localhost debug
    server.serve_forever()
    # flask_app.run(host='0.0.0.0', port=9992, debug=True)  # flask默认运行方式，带debug开关
