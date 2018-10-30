from flask import Flask, render_template, request, jsonify, make_response
import requests
import json
import re
import logging
log_fmt = '%(asctime)s %(levelname)s %(name)s :%(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_fmt)

app = Flask(__name__)

BASE_URL = "http://ja.wikipedia.org/w/api.php"


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    """
    初期表示
    :return: index.html
    """
    # 初期表示
    return render_template('index.html')


@app.route('/link', methods=['POST'])
def display_link():
    """
    リンクノード表示（ajax呼び出し想定）
    :return: チャート表示用jsonデータ
    """

    app.logger.info('--- Start [display_link] ---')

    max_nodes = int(request.form['max-nodes'])
    keyword = request.form['keyword']

    app.logger.info('max_nodes: {}'.format(max_nodes))
    app.logger.info('keyword: {}'.format(keyword))

    if keyword == '':
        return make_response(jsonify({"error": "キーワードを入力してください。"}))

    # wikipediaから記事全文を取得
    res_code, res_body = get_full_article(keyword)

    if res_code != 200:
        app.logger.error("APIレスポンスコード: {}".format(res_code))
        return make_response(jsonify({"error": "システムエラー発生しました。"}))

    # 本文を取得する
    content = get_content(res_body)

    if content is None:
        return make_response(jsonify({"error": "お探しのwikipediaページは存在しません。"}))

    # 本文からリンク文字列の一覧を取得する
    word_list = get_word_list(content)

    # リンク文字列の出現回数を取得する
    word_count_dict = get_word_count(content, word_list)

    # 出現回数を0～1に正規化
    word_count_dict = normalize(word_count_dict)

    # 重みの昇順に並び替え
    word_count_dict = sort_dict(word_count_dict)

    # max_nodesでフィルタリング
    word_count_dict = filter_by_disp_count(word_count_dict, max_nodes)

    # リンク文字列の記事の基本情報を取得する
    res_code, res_body = get_article_info(word_count_dict.keys())

    if res_code != 200:
        app.logger.error("APIレスポンスコード: {}".format(res_code))
        return make_response(jsonify({"error": "システムエラー発生しました。"}))

    # 単語と記事サイズのディクショナリを作成する
    word_size_dict = get_word_size(res_body)

    # word_size_dictを正規化する
    word_size_dict = normalize(word_size_dict)

    # チャート描画用のデータを生成する
    chart_data = build_link_chart_data(keyword, word_count_dict, word_size_dict)

    app.logger.info('--- End [display_link] ---')

    return make_response(jsonify(chart_data))


@app.route('/category', methods=['POST'])
def display_category():
    """
    カテゴリツリー表示（ajax呼び出し想定）
    :return: チャート表示用jsonデータ
    """

    app.logger.info('--- Start [display_category] ---')

    keyword = request.form['keyword']

    # wikipediaのカテゴリを取得
    res_code, res_body = get_categories(keyword)

    if res_code != 200:
        app.logger.error("APIレスポンスコード: {}".format(res_code))
        return make_response(jsonify({"error": "システムエラー発生しました。"}))

    categories = get_category_list(res_body)

    category_member_dict = get_category_members(categories)

    chart_data = build_category_chart_data(keyword, category_member_dict)

    app.logger.info('--- End [display_category] ---')

    return make_response(jsonify(chart_data))


def get_full_article(keyword):
    """
    wikipediaの記事全文を取得する
    :param keyword: 検索ワード
    :return: APIレスポンス
    """
    url_params = {
        "format": "json",
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": keyword
    }

    return execute_api(url_params)


def get_article_info(word_list):
    """
    wikipediaの記事の基本情報を取得する
    :param word_list: 検索ワード
    :return: APIレスポンス
    """

    url_params = {
        "format": "json",
        "action": "query",
        "prop": "info",
        "titles": format_titles(word_list)
    }

    return execute_api(url_params)


def get_word_size(res_body):
    """
    レスポンスボディから単語ごとの記事サイズを取得する
    :param res_body:
    :return: 単語と記事サイズのディクショナリ
    """
    pages = res_body['query']['pages']
    page_list = pages.values()

    article_size_dict = {}
    for page in page_list:
        if 'title' in page.keys() and 'length' in page.keys():
            article_size_dict[page["title"]] = page["length"]

    return article_size_dict


def format_titles(word_list):
    """
    単語のリストをtitlesのフォーマットに変換する
    :param word_list: 単語のリスト
    :return: titles文字列
    """
    titles = ""
    for word in word_list:
        titles += word
        titles += '|'

    return titles.rstrip('|')


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
        return None


def get_word_list(content):
    """
    本文からリンク文字列のリストを抽出する
    :param content: 本文
    :return: リンク文字列の一覧
    """
    pattern = "\[\[.+?\]\]"
    matched = re.findall(pattern, content)
    return [x.strip('[[').strip(']]') for x in matched]


def build_link_chart_data(key_word, word_count_dict, word_size_dict):
    """
    リンクノードチャート表示用のデータを生成する
    :param key_word: 検索ワード
    :param word_count_dict: リンク文字列と出現回数のディクショナリ
    :param word_size_dict: リンク文字列と記事サイズのディクショナリ
    :return: チャート表示用データ
    """
    nodes = [{"id": key_word, "order": 0, "size": 1}]
    nodes.extend([{"id": word, "order": 1, "size": word_size_dict.get(word, 0)} for word in word_count_dict.keys()])

    # リンクの生成
    links = [{"source": key_word, "target": word, "distance": 1 - count} for word, count in word_count_dict.items()]

    return {"nodes": nodes, "links": links}


def get_word_count(content, word_list):
    """
    content内にword_listが出現する回数を求める
    :param content: 本文
    :param word_list: 対象の単語
    :return: {対象の単語, 出現回数}
    """

    word_count_dict = {}

    # 出現数をカウントする
    for word in word_list:
        word_count_dict[word] = content.count(word)

    return word_count_dict


def normalize(word_dict):
    """
    辞書の値を0～1に正規化する
    :param word_dict:
    :return:
    """

    weight_min = min(word_dict.values())
    weight_max = max(word_dict.values())

    norm_word_dict = {}
    for word, weight in word_dict.items():
        if(weight_max - weight_min) != 0:
            norm_word_dict[word] = float(weight - weight_min) / (weight_max - weight_min)
        else:
            norm_word_dict[word] = 1

    return norm_word_dict


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


def get_categories(keyword):
    """
        wikipediaのカテゴリを取得する
        :param keyword: 検索ワード
        :return: APIレスポンス
        """
    url_params = {
        "format": "json",
        "action": "query",
        "prop": "categories",
        "titles": keyword
    }

    return execute_api(url_params)


def get_category_list(res_body):
    """
    APIレスポンスボディからカテゴリリストを取得する
    :param res_body: APIレスポンスボディ
    :return: 本文
    """
    page = list(res_body['query']['pages'].values())[0]
    categories_node = page['categories']
    categories = [x['title'].strip('Category:') for x in categories_node]

    # 削除対象のカテゴリ（完全一致）
    del_categories = [
        'ISBNマジックリンクを使用しているページ',
        'Webarchiveテンプレートのウェイバックリンク',
        'リンクのみの節がある記事',
        '告知事項があるページ',
        '曖昧さ回避の必要なリンクのあるページ',
        '改名提案'
    ]

    # 削除対象のカテゴリ（部分一致）
    del_partial_categories = [
        '出典を必要とする記事',
        '出典を必要とする記述のある記事',
        '日本語版記事がリダイレクトの仮リンクを含む記事',
        '国際化が求められている項目',
        '外部リンクがリンク切れになっている記事',
        '独自研究の除去が必要な節のある記事',
        '識別子が指定されている記事',
        'マイクロフォーマットがある記事',
        '独自研究の除去が必要な記事'
    ]

    # 部分一致カテゴリの完全一致名を調べる
    for category in categories:
        for del_partial_category in del_partial_categories:
            if category.find(del_partial_category) >= 0:
                del_categories.append(category)

    # 削除対象のカテゴリを取り除く
    for del_category in del_categories:
        if del_category in categories:
            categories.remove(del_category)

    return categories


def build_category_chart_data(keyword, category_article_dict):
    """
    カテゴリツリーチャート表示用のデータを生成する
    :param keyword: 検索キーワード
    :param category_article_dict: カテゴリと記事一覧のディクショナリ
    :return:
    """
    categories = []
    for category, articles in category_article_dict.items():
        category_articles = [{"name": x} for x in articles]
        categories.append({"name": category, "children": category_articles})
    chart_data = {'name': keyword, "children": categories}

    return chart_data


def get_category_members(categories):
    """
    Wikipediaのカテゴリ記事一覧を取得する
    :param categories:
    :return:
    """

    url_params = {
        "format": "json",
        "action": "query",
        "list": "categorymembers"
    }

    category_member_dict = {}
    for category in categories:
        url_params["cmtitle"] = "Category:" + category
        res_code, res_body = execute_api(url_params)

        articles = get_category_member_dict(res_body)
        category_member_dict[category] = articles

    return category_member_dict


def get_category_member_dict(res_body):
    """
    APIレスポンスボディからカテゴリ記事リストを取得する
    :param res_body: APIレスポンスボディ
    :return: 本文
    """
    categorymembers_node = list(res_body['query']['categorymembers'])
    articles = [x['title'] for x in categorymembers_node if x['ns'] == 0]

    return articles


def execute_api(url_params):
    """
    wikipedia apiを呼び出す
    :param url_params:
    :return: response
    """
    app.logger.debug("base_url: {}".format(BASE_URL))
    app.logger.debug("url_params: {}".format(url_params))

    res = requests.get(BASE_URL, params=url_params)
    res_code = res.status_code
    res_body = json.loads(res.text)

    app.logger.debug("res_code: {}".format(res_code))
    app.logger.debug("res_body: {}".format(res_body))

    return res_code, res_body


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=80)
