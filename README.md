GeoData-Security-System (矢量数据溯源定责系统)
📖 项目简介
GeoData-Security-System 是一个针对矢量数据分发后，提供数据溯源与定责的综合性安全管理系统。在现代地理信息系统（GIS）中，高价值的矢量数据和栅格数据在分发、共享过程中面临着极大的泄露和盗用风险。本系统旨在通过数字水印技术（包括二维码生成、LSB嵌入、矢量数据空域频域水印等），将使用者的申请信息、身份标识等隐蔽地嵌入到分发的数据中。
当发生数据泄露时，管理部门只需将泄露的数据文件上传至系统，即可一键提取出内部隐藏的水印信息，从而精准定位泄露源头，实现对数据的“溯源定责”。
✨ 核心功能
👥 多角色权限控制体系
管理员端：负责整个系统的审核流转、人员管理、系统日志监控以及水印的生成与嵌入。具有数据的一审、二审权限。
员工端（用户端）：负责浏览系统内的数据资产，按需发起数据使用申请，并在审批通过后下载带有专属水印的安全数据。
🗺️ GIS 空间数据可视化
结合 OpenLayers 和 Three.js，在前端实现了地球级、2D/3D一体化的地理空间数据展示（支持 Shapefile 等常见矢量格式的在线预览）。
直观的数据列表和详情页面，支持对图层数据进行快速检索和查看。
📝 完善的数据审批工作流
员工提交数据使用申请，包含使用目的、使用时间等要素。
多级审批机制：系统设定了“管理员一审”和“管理员二审”两级审核机制，确保数据分发的合规性与安全性。
🛡️ 核心：数字水印嵌入与提取
水印生成：在审批流程中，系统能够将员工的申请信息与身份信息自动编码生成一张不可见的二维码（QR码）水印。
水印嵌入：将生成的专属水印无损或低损地嵌入到原始的矢量数据 (Shp/GeoJSON) 或栅格数据中。数据在后台自动打包为 .zip 格式供用户下载。
水印提取与溯源：提供独立的“水印提取”模块。上传被泄露的数据文件后，系统运行后台提取算法，自动解析并还原出包含责任人信息的二维码，完成定责。
📊 仪表盘与数据统计
采用 ECharts 实现数据可视化大屏，为管理员和员工提供直观的系统运行状态、申请统计、下载记录等图表展示。
🛠 技术栈
前端
核心框架: Vue 3 (Composition API) + Vite
状态管理与路由: Pinia + Vue Router
UI 组件库: Element Plus
地图与可视化: OpenLayers (ol), Three.js
图表与工具: ECharts, Axios, qrcode
后端
核心框架: Python 3 + Flask, Flask-RESTful
数据库与 ORM:
关系型数据库：MySQL & PostgreSQL
空间数据支持：GeoAlchemy2
ORM 操作：Flask-SQLAlchemy
身份认证: Flask-JWT-Extended, Flask-Bcrypt
GIS 处理: GeoPandas, Shapely, PyShp, pyproj
图像与水印算法: Pillow, watermark (结合自定义算法实现矢量/栅格水印)
📁 项目目录结构
code
Text
GeoData-Security-System/
├── C1165作品过程及成果截图/       # 项目运行截图（登录、仪表盘、审批、水印提取等）
├── C1165安装及配置文件/           # 环境配置说明、账号密码记录及相关部署说明
├── C1165相关数据/                 # 项目测试用的空间数据集
├── C1165开发源代码/               # 系统核心源码目录
│   ├── 项目前端/
│   │   └── testrealfrontol/     # Vue3 + Vite 前端工程
│   │       ├── src/
│   │       │   ├── api/         # 接口封装
│   │       │   ├── components/  # 公共及布局组件
│   │       │   ├── router/      # 路由配置
│   │       │   ├── stores/      # Pinia 状态管理
│   │       │   └── views/       # 页面视图模块
│   │       └── package.json
│   └── 项目后端/
│       └── testrealend/         # Flask 后端工程
│           ├── algorithm/       # 核心算法库（水印嵌入、提取、坐标转换等）
│           ├── common/          # 公共常量与工具类
│           ├── model/           # 数据库模型 (SQLAlchemy Models)
│           ├── resource/        # RESTful API 资源处理类
│           ├── requirements.txt # Python 依赖清单
│           └── app.py           # Flask 启动入口文件
├── C1165作品介绍文档.docx         # 作品详尽介绍
├── C1165作品设计文档.docx         # 总体架构设计与功能设计
├── C1165安装部署说明文档.docx     # 详细的部署与安装手册
└── C1165人员基本信息.txt          # 团队人员基本信息
🚀 本地运行与部署
请在运行前确保本机已安装 Node.js (v16+)、Python (3.10+)、MySQL 以及 PostgreSQL (含 PostGIS 插件)。
1. 数据库配置
根据 C1165安装及配置文件 中的数据库说明，在本地 MySQL 和 PostgreSQL 中创建对应的数据库（如 esri_test）。
在 C1165开发源代码/项目后端/testrealend/app.py 中，修改数据库连接配置：
code
Python
app.config['SQLALCHEMY_BINDS'] = {
    'mysql_db': 'mysql+mysqldb://root:你的密码@127.0.0.1/esri_test',
    'postgres_db': 'postgresql://postgres:你的密码@127.0.0.1/esri_test'
}
2. 启动后端 (Flask)
code
Bash
# 进入后端目录
cd C1165开发源代码/项目后端/testrealend

# 安装依赖
pip install -r requirements.txt

# 启动服务 (默认运行在 5000 端口)
python app.py
3. 启动前端 (Vue)
code
Bash
# 进入前端目录
cd C1165开发源代码/项目前端/testrealfrontol

# 安装依赖
npm install

# 启动开发服务器
npm run dev
4. 访问系统
在浏览器中打开前端控制台输出的本地地址（如 http://localhost:5173）。
测试账号：可查看 C1165安装及配置文件/账号和密码/ 下的文件获取管理员与员工测试账号。
📄 文档支持
本项目提供了详尽的官方文档，强烈建议在二次开发或部署前阅读：
C1165作品设计文档.docx: 深入理解水印算法原理与系统架构。
C1165作品介绍文档.docx: 快速浏览系统完整功能。
C1165安装部署说明文档.docx: 获取更细致的生产环境部署指导。
🤝 贡献与反馈
本项目为 C1165 开发团队成果。如果您在运行过程中遇到问题，请查阅相关文档，或提交 Issue。
