from flask import Flask, render_template, redirect, request, url_for, jsonify, make_response
import requests
import json
import re
import logging
log_fmt = '%(asctime)s %(levelname)s %(name)s :%(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

app = Flask(__name__)


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    """
    初期表示
    :return: index.html
    """
    # 初期表示
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """
    Searchボタン押下時（ajax呼び出し想定）
    :return: チャート表示用jsonデータ
    """
    disp_count = int(request.form['disp_count'])
    keyword = request.form['keyword']

    app.logger.info('disp_count: {}'.format(disp_count))
    app.logger.info('keyword: {}'.format(keyword))

    res_code, res_body = search_wiki(keyword)

    if res_code == 200:
        # 本文を取得する
        content = get_content(res_body)

        if content is None:
            return make_response(jsonify({"error": "お探しのwikipediaページは存在しません。"}))

        # 本文からリンク文字列の一覧を取得する
        word_list = get_word_list(content)

        # リンク文字列の重みを取得する
        word_weight_dict = get_word_weight(content, word_list)

        # 重みを0～1に正規化
        word_weight_dict = normalize_weight(word_weight_dict)

        # 重みの昇順に並び替え
        word_weight_dict = sort_dict(word_weight_dict)

        # disp_countでフィルタリング
        word_weight_dict = filter_by_disp_count(word_weight_dict, disp_count)

        # チャート描画用のデータを生成する
        chart_data = build_chart_data(keyword, word_weight_dict)

        return make_response(jsonify(chart_data))

    else:
        app.logger.error("APIレスポンスコード: {}".format(res_code))
        return make_response(jsonify({"error": "システムエラー発生しました。"}))


def search_wiki(keyword):
    """
    wikipediaを検索する
    :param keyword: 検索ワード
    :return: APIレスポンス
    """
    base_url = "http://ja.wikipedia.org/w/api.php"
    url_params = {
        "format": "json",
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": keyword
    }

    app.logger.debug("base_url: {}".format(base_url))
    app.logger.debug("url_params: {}".format(url_params))

    res = requests.get(base_url, params=url_params)
    res_code = res.status_code
    res_body = json.loads(res.text)

    app.logger.debug("res_code: {}".format(res_code))
    app.logger.debug("res_body: {}".format(res_body))

    return res_code, res_body


def get_content(res_body):
    """
    APIレスポンスボディから本文を取得する
    :param res_body: APIレスポンスボディ
    :return: 本文
    """
    pages = res_body['query']['pages']
    page_body = list(pages.values())[0]

    if 'revisions' in page_body.keys():
        content = page_body['revisions'][0]['*']
        return content
    else:
        None


def get_word_list(content):
    """
    本文からリンク文字列のリストを抽出する
    :param content: 本文
    :return: リンク文字列の一覧
    """
    pattern = "\[\[.+?\]\]"
    matched = re.findall(pattern, content)
    return [x.strip('[[').strip(']]') for x in matched]


def build_chart_data(key_word, word_weight_dict):
    """
    チャート表示用のデータを生成する
    :param key_word: 検索ワード
    :param word_weight_dict: リンク文字列と重みのディクショナリ
    :return: チャート表示用データ
    """
    nodes = [{"id": key_word, "order": 0, "weight": 1}]
    nodes.extend([{"id": word, "order": 1, "weight": weight} for word, weight in word_weight_dict.items()])

    # リンクの生成
    links = [{"source": key_word, "target": word, "weight": weight} for word, weight in word_weight_dict.items()]

    return {"nodes": nodes, "links": links}


def get_word_weight(content, word_list):
    """
    word_listに含まれる単語の重みを求める
    まずは重み＝出現数として実装
    :param content: 本文
    :param word_list: 対象の単語
    :return: {対象の単語, 重み}
    """

    word_weight_dict = {}

    # 出現数をカウントする
    for word in word_list:
        word_weight_dict[word] = float(content.count(word))
        # app.logger.debug("word count: {}, {}".format(word, word_weight_dict[word]))

    return word_weight_dict


def normalize_weight(word_weight_dict):
    """
    重みを0～1に正規化する
    :param word_weight_dict:
    :return:
    """

    weight_min = min(word_weight_dict.values())
    weight_max = max(word_weight_dict.values())

    norm_word_weight_dict = {}
    for word, weight in word_weight_dict.items():
        norm_word_weight_dict[word] = (weight - weight_min) / (weight_max - weight_min)
        # app.logger.debug("norm_weight: {}, {}".format(word, norm_word_weight_dict[word]))

    return norm_word_weight_dict


def sort_dict(word_weight_dict):
    """
    word_weight_dictを重みの降順でソートする
    :param word_weight_dict: 単語と重みのディクショナリ
    :return: ソートされたディクショナリ
    """

    sorted_word_weight_dict = {}
    for word, weight in sorted(word_weight_dict.items(), key=lambda x: -x[1]):
        sorted_word_weight_dict[word] = weight

    return sorted_word_weight_dict


def filter_by_disp_count(word_weight_dict, disp_count):
    """
    word_weight_dictをdisp_countでフィルタリングする
    :param word_weight_dict: 単語と重みのディクショナリ
    :param disp_count: 最大表示数
    :return: フィルタリングされたディクショナリ
    """
    filtered_word_weight_dict = {}
    for i, (word, weight) in enumerate(word_weight_dict.items()):
        filtered_word_weight_dict[word] = weight
        if i >= disp_count:
            break
    return filtered_word_weight_dict


if __name__ == '__main__':
    app.run(debug=True)
