# -*- coding: utf-8 -*-
"""
app_new.py —— 独立完整版后端(不改动 app.py / 模板 / OTB.py)
本文件带逐行详细注释,用于学习。逻辑和之前给你的版本完全一样。
用法: python app_new.py   (与 app.py 同端口,不要同时跑)
相比原 app.py 的改动:
  1. 补齐了模板里表单提交的三个接口:
       POST /checkin/activity   活动签到(校验签到码,写签到记录)
       POST /checkin/duty       值班签到/签退(注意:模板实际提交的字段是
                                check_in / check_out 按钮,不是注释里写的 type=in/out)
       POST /change_password    修改密码
  2. 登录时写入 Flask session,签到接口靠 session 知道"是谁在签到"
  3. /index 改为从数据库加载真实的 值班状态 / 签到记录 / 当前活动
  4. 启动时自动建表(IF NOT EXISTS,幂等): users、activities、checkins
  5. 删掉了原来 GET /checkin/duty 那段死代码(渲染假"值班中"页面,没人链接到它)
  6. 新增活动管理: POST /activity/add 发布活动(activities 表加了 type 列存活动类型),
     /index 会把全部活动列表交给首页的"活动管理"页签显示
  7. 新增账号管理: POST /account/add 添加账号(可指定权限), POST /account/permission
     修改账号权限, /index 会把全部账号列表交给首页的"账号管理"页签显示
  8. 新增图文发布: POST /post/add 发布图文(封面图支持文件上传,存进 image 文件夹),
     POST /post/delete 删除图文(连封面图片文件一起删),
     /index 会把全部图文交给首页的"开源中心"页签显示(管理员端和用户端都显示)
"""
# ==================== 先记住一个坑:SQL 里的 % ====================
# psycopg2 用 %s 当占位符。它执行 SQL 时会从头到尾扫描 % 号:
#   %s        -> 取参数列表里的下一个参数
#   %%        -> 输出一个普通的 % 字符
#   其它 %x   -> 也当成占位符去取参数
# 所以 SQL 里只要出现"裸的 %"(最典型就是 like 'duty_%'),参数就会不够取,
# 直接抛 IndexError: tuple index out of range —— 报错信息完全看不出跟 % 有关。
# 两种正确写法:
#   1) 用 in 代替 like:      kind in ('duty_in','duty_out')
#   2) 双写转义:             kind like 'duty_%%'   (传参时才会转义)
# 注意:如果这条 SQL 一个参数都不传(execute 第二个参数是空),% 不会被解析,
#       反而不会报错 —— 这也是这个 bug 时有时无、特别难查的原因。
# ==================== 第一部分:导入工具 ====================
# 先认识几个核心概念,后面会反复用到:
#   路由(route): 就是"网址 → 函数"的对应关系。
#      比如 @app.route('/login') 写在 login 函数上面,意思是:
#      "有人访问 http://xxx/login 时,就调用 login 这个函数来处理"
#   session: 可以理解成服务端发的"临时工牌"。
#      登录成功后发一张,之后每次签到后台一看工牌就知道你是谁。
#      工牌存在浏览器的 Cookie 里,关掉浏览器就作废。
import os
# os 用来读环境变量(比如 SECRET_KEY),不懂可以先跳过

from flask import Flask, render_template, request, url_for, redirect, session
# Flask:创建网站应用
# render_template: 把模板(html)渲染成网页发给浏览器,顺便往里填变量
# request: 接收浏览器发来的数据(表单内容、网址参数等)
# url_for: 根据函数名生成网址(比如 url_for('index') 就是 "/index")
# redirect: 让浏览器跳转到另一个网址
# session: 上面说的"工牌"

from flask import send_from_directory
# send_from_directory: 把图片等文件发给浏览器(头像就是用它发的)

from werkzeug.security import check_password_hash, generate_password_hash
# 密码"哈希": 把密码加密成一串乱码再存进数据库。
# 好处: 数据库被人偷了也看不到明文密码。
# generate_password_hash: 加密(注册时用)
# check_password_hash: 核对(登录时用)

from werkzeug.utils import secure_filename
# secure_filename: 把上传的文件名"消毒"(去掉路径符号和奇怪字符,防止被塞恶意路径)

from datetime import datetime
# datetime: 拿当前时间(比如给上传的封面文件名加时间戳,防止重名互相覆盖)

from OTB import Query, Execute
# 你自己写的 OTB.py,里面封装了数据库操作:
#   Query("sql", (参数))   -> 查数据,返回"一行一行"的结果列表
#   Execute("sql", (参数)) -> 增删改,返回影响了多少行
# ==================== 第二部分:创建应用 ====================
app = Flask(__name__, template_folder='template')
# 创建 Flask 应用。template_folder='template' 告诉它:
# "我的网页模板放在 template 文件夹里"
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
# session 工牌需要一把"钥匙"来加密签名,防止别人伪造工牌。
# 这里优先读环境变量 SECRET_KEY,读不到就用后面的固定值。
# 正式部署时一定要换成随机字符串,开发期先用固定的没关系。
# ==================== 第三部分:建账本(建表) ====================

def init_db():
    """启动时调用一次:确保数据库里有这些表,没有就建,有就跳过。"""
    # 表 = 数据库里的"账本",每一行是一条记录,每一列是一个字段。
    Execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            serial PRIMARY KEY,
            sid           varchar(50) UNIQUE NOT NULL,
            username      varchar(100) NOT NULL,
            password_hash varchar(255) NOT NULL,
            permission    varchar(20)
        )
    """)
    # users = 用户账本,存注册的用户:
    #   sid           : 学号,UNIQUE = 不允许重复(注册时靠它查重)
    #   username      : 用户名
    #   password_hash : 加密后的密码(绝不存明文)
    #   permission    : 权限,后续用来区分管理员(现在只建列,不加数据)
    Execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permission varchar(20)")
    # 老数据库升级专用:之前已建过的 users 表没有 permission 列,补一条 ALTER。
    # 同样幂等:列已存在就跳过,不会报错。新列没有默认值,老用户都是 NULL。
    Execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id    serial PRIMARY KEY,
            code  varchar(50) UNIQUE NOT NULL,
            title varchar(200) NOT NULL,
            type  varchar(50),
            time  varchar(100),
            place varchar(200)
        )
    """)
    # activities = 活动账本,存"有哪些活动、签到码是什么":
    #   id    : 自动编号,每插一条自动 +1(serial = 自增)
    #   code  : 签到码,UNIQUE = 不允许重复
    #   title : 活动名称
    #   type  : 活动类型(社团内部 / 校外活动 / 聚餐 / 外出交流)
    #   time  : 活动时间(先用文本存,方便直接显示)
    #   place : 活动地点
    # IF NOT EXISTS = "如果还不存在才建",所以重复启动不会报错
    Execute("ALTER TABLE activities ADD COLUMN IF NOT EXISTS type varchar(50)")
    # 老数据库升级专用:CREATE TABLE IF NOT EXISTS 只对"还不存在的表"生效,
    # 之前已经建过的 activities 表没有 type 列,所以再补一条 ALTER。
    # ALTER ... IF NOT EXISTS 同样幂等:列已存在就跳过,不会报错。
    Execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id         serial PRIMARY KEY,
            sid        varchar(50) NOT NULL,
            kind       varchar(20) NOT NULL,  -- activity / duty_in / duty_out
            title      varchar(200),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    # checkins = 签到账本,每签到一次就插一行:
    #   sid        : 是谁签的(学号)
    #   kind       : 签到类型,三种取值:
    #                 activity = 活动签到
    #                 duty_in  = 值班签到(上班)
    #                 duty_out  = 值班签退(下班)
    #   title      : 这条记录的标题(活动名 / "值班签到" / "值班签退")
    #   created_at : 签到时间,DEFAULT now() = 不填就自动记当前时间
    Execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id         serial PRIMARY KEY,
            title      varchar(200) NOT NULL,
            summary    text,
            cover      varchar(300),
            link       varchar(300),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    # posts = 图文账本:管理员在"图文发布"页签发的图文,展示在开源中心:
    #   title      : 标题
    #   summary    : 简介(一段文字,可不填)
    #   cover      : 封面图地址(上传后存成 /image/xxx.jpg 这种)
    #   link       : 点击卡片跳转的网址(可不填)
    #   created_at : 发布时间,DEFAULT now() = 不填就自动记当前时间
# ==================== 第四部分:两个小工具函数 ====================
def fmt_time(dt):
    """把数据库返回的时间格式化成 '2026-10-20 14:30' 这种好看的形式"""
    return dt.strftime('%Y-%m-%d %H:%M')
def current_user():
    """看工牌:返回当前登录的人,没登录返回 None"""
    sid = session.get('sid')
    # session.get('sid') = "工牌上写的学号是什么"
    if not sid:
        return None
    return {'sid': sid, 'username': session.get('username', ''),'permission':session.get('permission','')}
# ==================== 第五部分:页面路由 ====================
# 下面每个函数上面都有 @app.route(...),含义:
#   @app.route('/xxx')                    -> 只处理 GET(打开网页)
#   @app.route('/xxx', methods=["POST"])  -> 只处理 POST(提交表单)
#   @app.route('/xxx', methods=["POST","GET"]) -> 两种都处理

@app.route('/image/<path:filename>')
def image_file(filename):
    # 头像图片的网址,比如 /image/touxiang.jpg
    # <path:filename> = "网址里 /image/ 后面的部分",自动传给 filename 参数
    return send_from_directory('image', filename)
    # 去 image 文件夹里找到这个文件发给浏览器


@app.route('/login', methods=["POST", "GET"])
def login():
    # 打开登录页(GET) 和 提交登录表单(POST) 都走这个函数

    if request.method == "GET":
        # 用户只是打开登录页,直接把页面给他
        return render_template('login.html')

    # ---- 下面是 POST:用户填了表单点"登录" ----
    sid = request.form.get('Id')
    password = request.form.get('password')
    # request.form.get('xxx') = "表单里 name=xxx 那个输入框填了什么"
    # 对照 login.html: 登录表单的学号框 name="Id",密码框 name="password"

    rows = Query("select * from users where sid=%s", (sid,))
    # 去 users 表查这个学号。%s 是"占位符",后面的 (sid,) 会填进去。
    # 为什么用占位符而不是直接拼字符串?防止 SQL 注入(有人输入恶意内容破坏数据库)

    if not rows:
        # 查不到这个人 -> 提示去注册(注意:这里不能报错,要友好提示)
        error = "该学号未注册，请先注册"
        return render_template('login.html', error=error, active_tab='login')
        # render_template 的第二个参数起,都是"传给网页的变量",
        # login.html 里有 {% if error %} 会把这句话显示成红条

    if check_password_hash(rows[0]["password_hash"], password):
        # 数据库里存的是加密后的密码,所以要"核对"而不是"直接比较"
        # rows[0] = 查到的第一行,["password_hash"] = 那一行的密码列

        # ---- 登录成功 ----
        session['sid'] = sid
        session['username'] = rows[0]["username"]
        session['permission']=rows[0]["permission"]
        # 发工牌:把学号、用户名、权限都写进 session,后面签到/改密/账号管理全靠它认人
        return redirect(url_for("index", username=rows[0]["username"], sid=sid))
        # redirect = 让浏览器跳转。
        # url_for("index", username=..., sid=...) = 生成
        #   "/index?username=张三&sid=123"  这样的网址
        # 跳过去后首页就能显示"张三"的名字和学号

    # 走到这里说明密码不对
    error = "学号或密码错误"
    return render_template('login.html', error=error, active_tab='login')


@app.route('/register', methods=["POST"])
def register():
    # 注册表单(login.html 里的第二个表单)提交到这里

    sid = request.form.get('Id')
    username = request.form.get('username_1')
    password = request.form.get('password')
    # 对照 login.html 注册表单:学号 name="Id",用户名 name="username_1",
    # 密码 name="password"(三个框的名字必须和这里对得上)

    if not sid or not username or not password:
        # 有框没填 -> 提醒,并切回注册页签(active_tab='register')
        error = "请填写完整的注册信息"
        return render_template('login.html', error=error, active_tab='register')
    rows = Query("select * from users where sid=%s", (sid,))
    if rows:
        # 学号已存在 -> 不重复注册
        error = "该学号已注册，请直接登录"
        return render_template('login.html', error=error, active_tab='register')
    password_hash = generate_password_hash(password)
    # 把密码加密,存库的必须是加密后的串,绝不能存明文
    Execute("insert into users(sid, username, password_hash) values(%s,%s,%s)",
            (sid, username, password_hash))
    # 往 users 表插一行新用户
    return render_template('login.html', ok="注册成功，请登录", active_tab='login')
    # ok 变量会让 login.html 显示绿色成功提示
@app.route('/index')
def index():
    # 首页:把 用户信息 / 值班状态 / 签到记录 / 当前活动 都准备好,交给模板显示
    # 先认人:优先看工牌(session);如果没登录,退回看网址参数
    # (从 /login 跳过来时网址上带着 ?username=xx&sid=xx)
    user = current_user()
    if user is None:
        user = {'username': request.args.get('username', ''),
                'sid': request.args.get('sid', '')}
    sid = user['sid']
    user['avatar'] = "/image/touxiang.jpg"
    # 头像地址。以 / 开头,模板里会直接当完整地址用
    # ---- 今日值班状态:去签到账本里找"今天最后一条值班记录" ----
    duty_status = '未签到'
    if sid:
        row = Query("""
            select kind from checkins
            where sid=%s and kind in ('duty_in', 'duty_out')
              and created_at::date = current_date
            order by id desc limit 1
        """, (sid,))
        # 拆开看这条 SQL:
        #   sid=%s                        -> 只看这个人的
        #   kind in ('duty_in','duty_out') -> 只看值班记录(两种都算)
        #       为什么不用 like 'duty_%'? 因为 SQL 里一出现裸的 % ,psycopg2
        #       就会把它当成"第二个占位符"去参数里取,参数只有一个 -> IndexError。
        #       真要用 like,得写成 'duty_%%'(双写转义)。这里用 in 更直白。
        #   created_at::date = current_date -> 只看今天的(把时间截断到"日期"再比)
        #   order by id desc              -> 按编号从新到旧排
        #   limit 1                       -> 只要最新一条
        if row:
            # 最新一条是"上班"就是值班中,是"下班"就是已签退
            duty_status = '值班中' if row[0]['kind'] == 'duty_in' else '已签退'
    # ---- 签到记录:普通用户只看自己的,管理员看所有人的(每条带用户名) ----
    records = []
    if sid:
        if user.get('permission') == 'admin':
            # 管理员:看所有人的签到记录(包括自己的),所以不按 sid 过滤。
            # left join users 表:把每条签到是谁签的(用户名)一起查出来。
            #   left join 的好处:就算这条记录对应的人已注销、users 表里查不到,
            #   签到记录本身也不会消失,只是用户名会是空。
            rows = Query("""
                select c.kind, c.title, c.created_at, u.username
                from checkins c
                left join users u on u.sid = c.sid
                order by c.id desc limit 50
            """)
            # 这里取最近 50 条,想多看就把 50 改大
        else:
            # 普通用户:只看自己的最近 20 条
            rows = Query("""
                select kind, title, created_at from checkins
                where sid=%s order by id desc limit 20
            """, (sid,))
        for r in rows:
            # 把 kind 翻译成模板认识的 type 和标题
            # (模板里靠 r.type 判断显示"活动"还是"值班"标签)
            if r['kind'] == 'activity':
                rtype, title = 'activity', r['title'] or '活动签到'
            elif r['kind'] == 'duty_in':
                rtype, title = 'duty', '值班签到'
            else:
                rtype, title = 'duty', '值班签退'
            item = {'type': rtype, 'title': title,
                    'time': fmt_time(r['created_at'])}
            if 'username' in r:
                # 只有管理员那条 SQL 查了 username 列,普通用户查的没有。
                # 查不到人(已注销)时用户名是空,显示"已注销用户"代替
                item['username'] = r['username'] or '已注销用户'
            records.append(item)
    # ---- 当前活动:取活动账本里最新发布的一条 ----
    activity = None
    rows = Query("select title, time, place from activities order by id desc limit 1")
    if rows:
        activity = {'title': rows[0]['title'], 'time': rows[0]['time'] or '',
                    'place': rows[0]['place'] or ''}
    # ---- 活动管理列表:全部活动,最新发布在前 ----
    activities = []
    for r in Query("select id, code, title, type, time from activities order by id desc"):
        activities.append({'id': r['id'], 'code': r['code'], 'title': r['title'],
                           'type': r['type'] or '未分类', 'time': r['time'] or ''})
    # ---- 账号管理列表:全部账号,按注册先后排 ----
    accounts = []
    for r in Query("select sid, username, permission from users order by id"):
        accounts.append({'sid': r['sid'], 'username': r['username'],
                         'permission': r['permission']})
    # ---- 开源中心列表:全部已发布图文,最新在前 ----
    posts = []
    for r in Query("select id, title, summary, cover, link, created_at from posts order by id desc"):
        posts.append({'id': r['id'], 'title': r['title'], 'summary': r['summary'] or '',
                      'cover': r['cover'] or '', 'link': r['link'] or '',
                      'date': fmt_time(r['created_at'])})
    # 签到成功后是带着 ?ok=xxx 或 ?error=xxx 跳回来的,取出来给模板显示提示条
    ok = request.args.get('ok', '')
    error = request.args.get('error', '')
    if user.get('permission')=='admin':
        return render_template('index.html',
                               user=user,  # 账户中心显示
                               duty={'status': duty_status},  # 值班状态
                               activity=activity,  # 当前活动面板
                               activities=activities,  # 活动管理列表
                               accounts=accounts,  # 账号管理列表
                               records=records,  # 签到记录表格
                               posts=posts,  # 开源中心图文列表
                               ok=ok, error=error)
    return render_template('user_index.html',
                           user=user,  # 账户中心显示
                           duty={'status': duty_status},  # 值班状态
                           activity=activity,  # 当前活动面板
                           records=records,  # 签到记录表格
                           posts=posts,  # 开源中心图文列表
                           ok=ok, error=error)
                                            # 提示条
# ==================== 第六部分:签到接口(这次新补的核心) ====================
# 注意:这两个函数只处理 POST,不接受打开网页。
# 它们干完活不返回网页,而是 redirect 跳回首页(带上 ok/error 提示)。
@app.route('/checkin/activity', methods=["POST"])
def checkin_activity():
    # 活动签到:用户输入签到码,点"签 到"提交到这里
    user = current_user()
    if user is None:
        # 没工牌(没登录) -> 轰回登录页
        return redirect(url_for('login'))
    code = request.form.get('code', '').strip()
    # 对照 index.html:签到码输入框 name="code"。strip() 去掉首尾空格
    if not code:
        return redirect(url_for('index', error='请输入签到码'))
        # 跳回首页,网址变成 /index?error=请输入签到码,首页显示红条提示
    rows = Query("select id, title from activities where code=%s", (code,))
    # 拿签到码去活动账本里找,找到就说明码是真实有效的
    if not rows:
        return redirect(url_for('index', error='签到码无效'))
    Execute("insert into checkins(sid, kind, title) values(%s, %s, %s)",
            (user['sid'], 'activity', rows[0]['title']))
    # 记一笔:谁 + 什么类型(活动) + 哪个活动。时间自动记当前时间
    return redirect(url_for('index', ok='活动签到成功：' + rows[0]['title']))
@app.route('/checkin/duty', methods=["GET", "POST"])
def checkin_duty():
    # 值班签到/签退。GET 只是兜底(防止有人直接打开这个网址报错),直接回首页
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    # 模板里两个按钮:name="check_in" value="in" 和 name="check_out" value="out"
    # 浏览器只会把"被点的那一个按钮"提交过来,所以看哪个有值就知道点了哪个
    # (注意:这和模板顶部注释写的 type=in/out 不一致,以实际 HTML 为准)
    # ---- 分支一:点了"签到(开始值班)" ----
    if request.form.get('check_in'):
        # 先查今天最后一条值班记录,防止重复签到
        row = Query("""
            select kind from checkins
            where sid=%s and kind in ('duty_in', 'duty_out')
              and created_at::date = current_date
            order by id desc limit 1
        """, (user['sid'],))
        if row and row[0]['kind'] == 'duty_in':
            # 今天已经"上班"且还没"下班",再点签到就是重复
            return redirect(url_for('index', error='今日已在值班中，请勿重复签到'))
        Execute("insert into checkins(sid, kind, title) values(%s, %s, %s)",
                (user['sid'], 'duty_in', '值班签到'))
        return redirect(url_for('index', ok='值班签到成功'))
    # ---- 分支二:点了"签退(结束值班)" ----
    if request.form.get('check_out'):
        row = Query("""
            select kind from checkins
            where sid=%s and kind in ('duty_in', 'duty_out')
              and created_at::date = current_date
            order by id desc limit 1
        """, (user['sid'],))
        if not row or row[0]['kind'] != 'duty_in':
            # 今天还没有"上班"记录(或已经签退过了),不能签退
            return redirect(url_for('index', error='今日还没有签到，无法签退'))
        Execute("insert into checkins(sid, kind, title) values(%s, %s, %s)",
                (user['sid'], 'duty_out', '值班签退'))
        return redirect(url_for('index', ok='已签退，辛苦了'))
    # 两个分支都没进 -> 说明是 GET 打开网页,跳回首页即可
    return redirect(url_for('index'))
# ==================== 第七部分:活动管理(新增) ====================
@app.route('/activity/add', methods=["POST"])
def activity_add():
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    # 首页"活动管理"页签里,"新增活动"表单提交到这里。
    # 表单四个字段: title(活动名称) / code(签到码) / type(活动类型) / time(活动日期)
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    title = request.form.get('title', '').strip()
    code = request.form.get('code', '').strip()
    atype = request.form.get('type', '').strip()
    atime = request.form.get('time', '').strip()
    # 四个输入框的 name 要和 index.html 活动管理表单对得上
    if not title or not code or not atype or not atime:
        # _anchor='manage' = 跳回首页时网址带 #manage,页面自动切到"活动管理"页签
        return redirect(url_for('index', error='请填写完整的活动信息', _anchor='manage'))
    rows = Query("select id from activities where code=%s", (code,))
    if rows:
        # 签到码列是 UNIQUE 的,重复的码会让活动签到分不清是哪个活动,先查重给友好提示
        return redirect(url_for('index', error='该签到码已被使用，请换一个', _anchor='manage'))
    Execute("insert into activities(code, title, type, time) values(%s, %s, %s, %s)",
            (code, title, atype, atime))
    # place(活动地点)这个表单没有,先不填,表里那列就是 NULL
    return redirect(url_for('index', ok='活动发布成功：' + title, _anchor='manage'))
# ==================== 第八部分:修改密码 ====================
@app.route('/change_password', methods=["POST"])
def change_password():
    # index.html 里"修改密码"表单的三个框:
    #   name="old_password" / "new_password" / "confirm"
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    old = request.form.get('old_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm', '')
    # 第一步:核对旧密码(数据库里是加密的,用 check_password_hash 核对)
    rows = Query("select password_hash from users where sid=%s", (user['sid'],))
    if not rows or not check_password_hash(rows[0]['password_hash'], old):
        return redirect(url_for('index', error='原密码错误'))
    # 第二步:两次新密码要一致
    if new != confirm:
        return redirect(url_for('index', error='两次输入的新密码不一致'))
    # 第三步:长度检查(和注册时"至少 6 位"的要求一致)
    if len(new) < 6:
        return redirect(url_for('index', error='新密码至少 6 位'))
    # 都通过 -> 加密后更新数据库
    Execute("update users set password_hash=%s where sid=%s",
            (generate_password_hash(new), user['sid']))
    return redirect(url_for('index', ok='密码修改成功'))
@app.route('/activity/delete',methods=["POST"])
def activity_delete():
    # 和 activity_add 一样,先拦"不是管理员"的请求
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    aid = request.form.get('id', '')
    Execute("delete from activities where id=%s", (aid,))
    return redirect(url_for('index', _anchor='manage'))
# ==================== 第九部分:账号管理(新增) ====================
# 首页"账号管理"页签的两个表单提交到这里。
# 先记一个没做的点:现在任何登录的人都能加账号/改权限。
# 以后想限制"只有管理员能用"时,在这两个函数里各加一句:
#   if session.get('permission') != 'admin':
#       return redirect(url_for('index', error='没有权限', _anchor='accounts'))
@app.route('/account/add', methods=["POST"])
def account_add():
    # 首页"账号管理"页签里,"新增账号"表单提交到这里。
    # 表单四个字段: sid(学号) / username(用户名) / password(初始密码) / permission(权限)
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    sid = request.form.get('sid', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    permission = request.form.get('permission', 'user').strip()
    # 四个输入框的 name 要和 index.html 账号管理表单对得上
    if not sid or not username or not password:
        return redirect(url_for('index', error='请填写完整的账号信息', _anchor='accounts'))
    if len(password) < 6:
        return redirect(url_for('index', error='初始密码至少 6 位', _anchor='accounts'))
    rows = Query("select id from users where sid=%s", (sid,))
    if rows:
        # 学号列是 UNIQUE 的,重复的学号会分不清谁是谁,先查重给友好提示
        return redirect(url_for('index', error='该学号已存在，不能重复添加', _anchor='accounts'))
    if permission not in ('user', 'admin'):
        # 前端下拉框只给这两个选项,这里兜底:乱传的值一律按"普通成员"处理
        permission = 'user'
    Execute("insert into users(sid, username, password_hash, permission) values(%s, %s, %s, %s)",
            (sid, username, generate_password_hash(password), permission))
    # 往 users 表插一行新账号。密码必须加密后入库(和注册一样),权限直接存 permission 列
    return redirect(url_for('index', ok='账号添加成功：' + username, _anchor='accounts'))
@app.route('/account/permission', methods=["POST"])
def account_permission():
    # 首页"账号管理"页签里,每行"修改权限"表单提交到这里。
    # 表单两个字段: sid(改谁的,藏在隐藏输入框里) / permission(改成什么)
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    sid = request.form.get('sid', '').strip()
    permission = request.form.get('permission', '').strip()
    if not sid or permission not in ('user', 'admin'):
        # 和添加账号一样兜底:不是这两个值的一律不认
        return redirect(url_for('index', error='无效的权限设置', _anchor='accounts'))
    Execute("update users set permission=%s where sid=%s", (permission, sid))
    # 改 users 表那一行的 permission 列。sid 是 UNIQUE 的,最多只会改到一行
    return redirect(url_for('index', ok='权限修改成功：' + sid, _anchor='accounts'))
# ==================== 第十部分:图文发布(新增) ====================
# 管理员在"图文发布"页签发图文,发完展示在开源中心(管理端和用户端都看得到)。
# 和其他管理接口一样,以后要限制"只有管理员能发"时,在函数开头加:
#   if session.get('permission') != 'admin':
#       return redirect(url_for('index', error='没有权限', _anchor='posts'))
@app.route('/post/add', methods=["POST"])
def post_add():
    # 首页"图文发布"页签里的表单提交到这里。
    # 表单字段: title(标题) / summary(简介) / cover(封面图,文件上传) / link(可选链接)
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    title = request.form.get('title', '').strip()
    summary = request.form.get('summary', '').strip()
    link = request.form.get('link', '').strip()
    if not title:
        # 标题是必填的,没填就带红条回"图文发布"页签
        return redirect(url_for('index', error='请填写标题', _anchor='posts'))
    cover = ''
    up = request.files.get('cover')
    # request.files = 表单里"上传的文件"。表单没传文件时 up.filename 是空的
    if up and up.filename:
        # 有文件 -> 存进 image 文件夹。文件名前面加时间戳,防止两个人传同名图互相覆盖
        fname = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + secure_filename(up.filename)
        up.save(os.path.join('image', fname))
        # secure_filename 会去掉文件名里的路径符号,防止恶意文件名写到别的目录去
        cover = '/image/' + fname
        # 存好后把访问地址记进数据库。以 / 开头,模板会直接当完整地址用
    Execute("insert into posts(title, summary, cover, link) values(%s, %s, %s, %s)",
            (title, summary, cover, link))
    # 发布时间不用填,表里 DEFAULT now() 自动记当前时间
    return redirect(url_for('index', ok='图文发布成功：' + title, _anchor='posts'))
@app.route('/post/delete', methods=["POST"])
def post_delete():
    # 首页"图文发布"页签里,每行垃圾桶按钮提交到这里。
    # 表单一个字段: id(删哪篇,藏在隐藏输入框里)
    # 和 post_add 一样,先拦"不是管理员"的请求
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    pid = request.form.get('id', '')
    rows = Query("select cover from posts where id=%s", (pid,))
    # 删数据库记录之前,先把它的封面地址查出来,等会连图片文件一起删
    Execute("delete from posts where id=%s", (pid,))
    # 删数据库里的记录
    if rows and rows[0]['cover'] and rows[0]['cover'].startswith('/image/'):
        fpath = os.path.join('image', rows[0]['cover'].replace('/image/', '', 1))
        # cover 里存的是网址形式 /image/xxx.jpg,换成磁盘上的真实路径 image/xxx.jpg
        if os.path.isfile(fpath):
            os.remove(fpath)
            # 顺手把上传的封面图片文件也删掉,不然它会变成"孤儿文件"一直占着文件夹
    return redirect(url_for('index', _anchor='posts'))
@app.route('/account/delete',methods=["POST"])
def account_delete():
    # 和其他账号管理接口一样,先拦"不是管理员"的请求
    if session.get('permission') != 'admin':
        return redirect(url_for('index', error='没有权限'))
    user = current_user()
    if user is None:
        # 没登录连工牌都没有,先轰回登录页(不检查会因 session['sid'] 不存在而报 500)
        return redirect(url_for('login'))
    sid = request.form.get('sid', '').strip()
    if sid == session['sid']:
        # 跳回首页时提示要放在 error 参数里(/index 只认 error 和 ok,别的参数名显示不出来)
        return redirect(url_for('index', error='不能删除自己', _anchor='accounts'))
    Execute("delete from users where sid=%s", (sid,))
    return redirect(url_for('index', _anchor='accounts'))

# ==================== 第十一部分:程序入口 ====================
if __name__ == '__main__':
    # 只有直接运行 python app_new.py 时才会执行这里
    # (如果被别人 import 导入,__name__ 不等于 '__main__',就不会启动网站)
    init_db()
    # 启动前先确保所有账本(表)存在
    app.run(debug=True, host="0.0.0.0", port=5000)
    # 启动网站,监听 5000 端口:
    #   debug=True      -> 代码一改自动重启,出错时显示详细调试页面(开发用,上线要关)
    #   host="0.0.0.0"  -> 允许局域网内其他设备访问(比如手机)
    #   浏览器访问: http://127.0.0.1:5000/login

