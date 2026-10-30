# 科成开源社 · 社团签到系统

一个基于 Flask + OpenTenBase 的社团内部签到管理网站。支持活动签到、值班签到/签退、签到记录查询、账号与权限管理、开源中心图文发布。

---

## 一、项目是做什么的

| 模块 | 说明 |
|---|---|
| 登录 / 注册 | 学号 + 密码登录，密码用哈希存储（不存明文） |
| 活动签到 | 输入活动签到码完成签到，签到码由管理员在后台创建 |
| 值班签到 | 一天内「签到（上班）」→「签退（下班）」，防重复 |
| 签到记录 | 活动和值班记录合并展示，按时间倒序 |
| 账号中心 | 查看个人信息、修改密码 |
| 活动管理 | 管理员创建 / 删除活动及签到码（仅管理员可见） |
| 账号管理 | 管理员添加账号、调整权限（仅管理员可见） |
| 开源中心 | 图文展示页，管理员可发布 / 删除图文（带封面上传） |

管理员登录后看到的是 `index.html`（功能完整版），普通用户看到 `user_index.html`（没有管理页签）。

---

## 二、技术栈

| 层 | 选型 | 版本（本机实测） |
|---|---|---|
| 后端框架 | Flask | 3.1.3 |
| WSGI / 工具库 | Werkzeug | 3.1.8 |
| 模板引擎 | Jinja2 | 3.1.6 |
| 数据库驱动 | psycopg2-binary | 2.9.13 |
| 数据库 | OpenTenBase（PG 协议兼容） | CN 端口 30004 |
| 前端 | 原生 HTML / CSS / JS（无框架） | — |

---

## 三、环境清单：跑起来需要准备什么

### 3.1 必备条件

1. **Python 3.9 及以上**（推荐 3.12 ~ 3.14；本机环境为 3.14.7）
2. **两个 Python 包**：`Flask`、`psycopg2-binary`
3. **一台能连上的 OpenTenBase 数据库**（可以装在 VMware 虚拟机里）
4. 任意现代浏览器（Chrome / Edge / Firefox）

### 3.2 数据库是最大的前提

本项目**不是** SQLite，没有内置数据库，必须有一个可用的 OpenTenBase 实例。要求：

- 集群已启动（GTM + CN + DN 都在跑）
- 宿主机（Windows）能访问到虚拟机的 **CN 节点 30004 端口**
- `pg_hba.conf` 已放行宿主机的网段，例如：`host all all 192.168.22.0/24 md5`

> ⚠️ 只连 **CN（协调节点）的 30004**。不要连 GTM（20001）或 DN（40006/40007），直连 DN 只能看到一部分分片数据，会出现「数据明明存了却查不到」的假象。

### 3.3 本机已验证的环境（可对照）

```
Python   : 3.14.7
解释器   : D:\work\01_Python\00_envs\01_flask_py314\python.exe
Flask    : 3.1.3
Werkzeug : 3.1.8
Jinja2   : 3.1.6
psycopg2-binary : 2.9.13
```

---

## 四、目录结构

```
club_checkin/
├── app_new.py              主程序：全部路由 + 自动建表（唯一需要运行的文件）
├── OTB.py                  数据库封装：连接配置 + Query() / Execute()
├── requirements.txt        Python 依赖清单
├── README.md               本文档
├── template/               页面模板（Jinja2）
│   ├── login.html          登录 / 注册页
│   ├── index.html          管理员首页（含活动管理、账号管理、图文发布）
│   └── user_index.html     普通用户首页（只有签到相关页签）
├── static/                 静态资源（Flask 默认目录，URL 前缀 /static）
│   ├── css/                login.css / index.css / user_index.css
│   └── js/                 login.js / index.js / user_index.js
└── image/                  图片目录（头像、logo、上传的图文封面）
    ├── logo.png            网站图标（favicon）
    └── touxiang.jpg        默认头像
```

---

## 五、从零跑起来的完整步骤

### 第 1 步：启动数据库（虚拟机内）

确认 OpenTenBase 集群已在运行，并确认 IP：

```bash
ip a                    # 查看虚拟机 IP，记下来，例如 192.168.22.130
```

> 如果集群没启动，用 `pgxc_ctl` 执行 `start all`（具体以你的部署配置为准）。

在 Windows 上先验证端口通不通：

```bash
ping 192.168.22.130
```

### 第 2 步：创建 Python 虚拟环境

在 PyCharm 里：`Settings → Project → Python Interpreter → Add Interpreter → Add Local Interpreter → Virtualenv Environment → New`。

或者命令行：

```bash
cd E:\club_checkin
python -m venv .venv
.venv\Scripts\activate
```

### 第 3 步：安装依赖

```bash
pip install -r requirements.txt
```

等价于：

```bash
pip install Flask==3.1.3 psycopg2-binary==2.9.13
```

> 装 `psycopg2-binary` 而不是 `psycopg2`。前者是预编译包，Windows 上不需要装 Visual C++ 编译器；后者大概率编译失败。

### 第 4 步：确认数据库连接参数

打开 `OTB.py`，检查 `DB` 字典：

```python
DB = {
    "host": "192.168.22.130",   # 虚拟机 IP，换电脑/换网络后要改
    "port": 30004,              # CN 协调节点端口，不要改
    "user": "opentenbase",      # 部署时的数据库用户
    "password": "123456",       # 部署时设的密码
    "dbname": "postgres",       # 默认库
}
```

先单独测一下能不能连通（可选，但强烈建议）：

```bash
python -c "from OTB import Query; print(Query('select version()'))"
```

能打印出版本号，说明数据库这关过了。

### 第 5 步：启动网站

**必须在项目根目录（`E:\club_checkin`）下启动**，原因见第七节。

PyCharm 里直接右键 `app_new.py` → Run。

或者命令行：

```bash
cd E:\club_checkin
python app_new.py
```

看到 `Running on http://127.0.0.1:5000` 就成功了。

浏览器访问：<http://127.0.0.1:5000/login>

> 表结构不用手工建。程序启动时会执行 `init_db()`，自动创建 `users`、`activities`、`checkins`、`posts` 四张表（`IF NOT EXISTS`，重复启动不会报错，也不会清空数据）。

### 第 6 步：创建第一个管理员（关键，容易漏）

**系统不会自动生成管理员账号。** 新注册的用户 `permission` 是空的，只能看到普通用户界面。第一个管理员需要手工在数据库里指定一次。

1. 先打开网站正常注册一个账号（例如学号 `202402030512`）
2. 在虚拟机里用 psql 连进去执行：

```bash
psql -h 127.0.0.1 -p 30004 -U opentenbase -d postgres
```

```sql
UPDATE users SET permission = 'admin' WHERE sid = '202402030512';
```

3. 退出登录、重新登录一次（权限是在登录时写进 session 的，必须重新登录才生效）

之后就能在页面上用「账号管理」给其他人分配管理员权限，不用再动数据库了。

---

## 六、数据库表说明（程序自动创建）

### users —— 用户表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | serial PK | 自增主键 |
| sid | varchar(50) UNIQUE | 学号，登录账号，不允许重复 |
| username | varchar(100) | 用户名 |
| password_hash | varchar(255) | 密码哈希（scrypt），不存明文 |
| permission | varchar(20) | `admin` = 管理员，`user` / NULL = 普通用户 |

### activities —— 活动表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | serial PK | 自增主键 |
| code | varchar(50) UNIQUE | 活动签到码，不允许重复 |
| title | varchar(200) | 活动名称 |
| type | varchar(50) | 活动类型（社团内部 / 校外活动 / 聚餐 / 外出交流） |
| time | varchar(100) | 活动时间（文本，方便直接显示） |
| place | varchar(200) | 活动地点 |

### checkins —— 签到记录表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | serial PK | 自增主键 |
| sid | varchar(50) | 签到人学号 |
| kind | varchar(20) | `activity` 活动签到 / `duty_in` 值班签到 / `duty_out` 值班签退 |
| title | varchar(200) | 记录标题（活动名 / 值班签到 / 值班签退） |
| created_at | timestamptz | 签到时间，默认当前时间 |

> 活动和值班共用一张表，靠 `kind` 区分。好处是「签到记录」页一次查询就能同时展示两类记录。

### posts —— 开源中心图文表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | serial PK | 自增主键 |
| title | varchar(200) | 标题 |
| summary | text | 简介 |
| cover | varchar(300) | 封面图地址，形如 `/image/20261027193000_xxx.jpg` |
| link | varchar(300) | 点击跳转链接（可选） |
| created_at | timestamptz | 发布时间，默认当前时间 |

---

## 七、三个必须知道的运行约束

### 1. 必须在项目根目录启动

代码里有相对路径 `os.path.join('image', fname)`（上传封面时用）。如果在别的目录下执行 `python E:\club_checkin\app_new.py`，图片会被存到那个目录下的 `image` 文件夹，导致页面上图片 404。

### 2. 端口 5000，局域网可访问

```python
app.run(debug=True, host="0.0.0.0", port=5000)
```

- `host="0.0.0.0"` 表示同一局域网内的手机也能访问：`http://<电脑IP>:5000`
- 第一次手机访问不通，通常是 **Windows 防火墙**拦了 Python，允许一下即可
- 端口被占用时（`Address already in use`），把 5000 改成 5001 等其它值

### 3. debug=True 只能用于开发

上线/长期运行要改成 `debug=False`，否则出错页面会暴露源码和内部信息。同时 `app.secret_key` 也要换成真正的随机值：

```python
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
```

生产环境通过环境变量传入：`set SECRET_KEY=一串足够长的随机字符`。

---

## 八、路由与接口清单

### 页面

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/login` | 登录页 / 提交登录 |
| POST | `/register` | 注册 |
| GET | `/index` | 首页（按权限渲染管理员版或用户版） |
| GET | `/image/<path:filename>` | 图片访问（头像、logo、图文封面） |
| GET | `/static/<path>` | 静态资源（CSS / JS，Flask 自动提供） |

### 签到

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/checkin/activity` | 活动签到（校验签到码） |
| POST | `/checkin/duty` | 值班签到 / 签退（按钮名区分） |
| POST | `/change_password` | 修改密码 |

### 管理（均需管理员权限）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/activity/add` | 新建活动 + 生成签到码 |
| POST | `/activity/delete` | 删除活动 |
| POST | `/account/add` | 添加账号（可指定权限） |
| POST | `/account/permission` | 修改指定账号权限 |
| POST | `/post/add` | 发布图文（含封面上传） |
| POST | `/post/delete` | 删除图文（同时删除封面文件） |

---

## 九、常见问题排查

| 现象 / 报错 | 原因 | 怎么解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | 依赖装到了别的解释器 | PyCharm 里确认 `Settings → Python Interpreter` 选的就是装了包的那个环境 |
| `ModuleNotFoundError: No module named 'psycopg2'` | 同上 | `pip install psycopg2-binary` |
| `connection refused` | 端口写错或集群没启动 | 确认是 **30004**；虚拟机里确认 CN 在运行 |
| `could not connect ... timeout` | 虚拟机没开机 / 不在同一网段 / 防火墙 | `ping` 虚拟机；确认 VMware 网络模式（NAT） |
| `no pg_hba.conf entry for host "..."` | 数据库只放行了本机 | 虚拟机里给 `pg_hba.conf` 加 `host all all 192.168.22.0/24 md5`，然后 reload |
| `FATAL: role "xxx" does not exist` | 用了不存在的数据库用户 | 改成部署时的用户（本机是 `opentenbase`），Linux 上没有 `root` 库用户 |
| `relation "users" does not exist` | 连到了别的库，或 `init_db()` 没跑 | 确认 `dbname` 是 `postgres`；确认程序从 `app_new.py` 启动（会执行建表） |
| `IndexError: tuple index out of range` | SQL 里出现了落单的 `%` | 见下方「SQL 里的 % 陷阱」 |
| 签到成功提示了，但记录里没有 | 少了 `commit()` | `OTB.py` 的 `Execute()` 里必须有 `conn.commit()` |
| 页面能开，但样式全丢 | `/static/` 目录缺失或路径不对 | 确认 `static/css`、`static/js` 存在；`app_new.py` 不要改 `static_folder` |
| 上传的封面图 404 | 启动目录不对 | 回到项目根目录启动 |
| 改密码后登不上 | 密码要求至少 6 位，且两次要一致 | 按提示重试 |

### SQL 里的 `%` 陷阱（本项目踩过一次）

用 `Query()` / `Execute()` 传参数时，SQL 里**只能出现 `%s` 占位符**。想写「字面量百分号」必须写成 `%%`，否则 psycopg2 会把它当成额外占位符，报 `IndexError: tuple index out of range` —— 这个报错完全看不出和 `%` 有关，极难排查。

```python
# ✗ 错：'duty_%' 里的 % 会被当占位符
Query("select * from checkins where sid=%s and kind like 'duty_%'", (sid,))

# ✓ 对：用 in 列举，彻底不碰 %
Query("select * from checkins where sid=%s and kind in ('duty_in','duty_out')", (sid,))

# ✓ 也可以：把模式当参数传
Query("select * from checkins where title like %s", ('%开场%',))
```

---

## 十、安全与待改进（了解即可）

当前是**校园内部工具**的定位，以下问题在校内几十人使用可以接受，但如果要对外部署，需要处理：

1. **`OTB.py` 里明文写着数据库密码** —— 应改为读环境变量
2. **`app.secret_key` 有默认值** —— 生产环境必须换成随机串
3. **`debug=True`** —— 上线要关掉
4. **每次请求新建数据库连接** —— 几十人无压力；将来慢了再换连接池（`psycopg2.pool`），只需改 `OTB.py`
5. **删除活动/图文没有二次确认** —— 前端可以加个 `confirm()`

---

## 十一、快速自查清单

部署到新机器时，按这个顺序确认，一步一验证：

- [ ] Python 版本 ≥ 3.9
- [ ] `pip install -r requirements.txt` 成功
- [ ] `python -c "from OTB import Query; print(Query('select 1'))"` 能出结果
- [ ] 在项目根目录执行 `python app_new.py`
- [ ] 浏览器打开 `http://127.0.0.1:5000/login` 页面正常、样式正常
- [ ] 注册一个账号能登录进首页
- [ ] 数据库里 `UPDATE users SET permission='admin'` 后重新登录，能看到「活动管理 / 账号管理 / 图文发布」
- [ ] 手机连同一 WiFi 访问 `http://<电脑IP>:5000` 能打开
