# 关键词分析API

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于FastAPI的关键词分析系统，支持实时进度推送和大规模数据处理。

## ✨ 特性

- 🚀 高性能异步处理
- 📊 实时进度推送
- 💾 智能数据缓存
- 🔄 自动资源管理
- 📈 内存使用优化
- 🔍 关键词分析
  - 共现词分析
  - 搜索量计算
  - 竞争关系分析

## 🚀 快速开始

### 前置要求

- Python 3.8+
- MySQL 8.0+
- 8GB+ RAM
- query_list_3.csv 数据文件

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/keyword-analysis-api.git
cd keyword-analysis-api
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境
```bash
cp .env.example .env
# 编辑 .env 文件，设置数据库连接信息
```

5. 初始化数据库
```bash
mysql -u root -p < schema.sql
```

6. 放置数据文件
```bash
# 将 query_list_3.csv 文件放在项目根目录
```

7. 启动服务
```bash
python run.py
```

8. 访问测试页面
```
http://localhost:8000/static/test_ws.html
```

## 📁 项目结构

```
.
├── app/                 # 应用主目录
│   ├── api/            # API接口
│   ├── core/           # 核心配置
│   ├── models/         # 数据模型
│   ├── static/         # 静态文件
│   └── utils/          # 工具函数
├── logs/               # 日志文件
├── result/             # 分析结果
├── .env.example        # 环境变量示例
├── requirements.txt    # 项目依赖
└── schema.sql         # 数据库结构
```

## 📝 必要文件说明

- `query_list_3.csv`: 查询数据文件（需自行提供）
- `.env`: 环境配置文件（从.env.example创建）
- `logs/`: 日志目录（自动创建）
- `result/`: 结果目录（自动创建）

## 🔧 配置说明

主要配置项（在 .env 文件中设置）：
```env
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
API_V1_STR=/api/v1
PROJECT_NAME=Keyword Analysis API
```

## 📊 使用示例

1. 创建分析任务：
```bash
curl -X POST "http://localhost:8000/api/v1/keyword/analyze?keyword=测试关键词"
```

2. 启动分析：
```bash
curl -X POST "http://localhost:8000/api/v1/keyword/start-analysis/1"
```

3. 查看进度：
使用提供的测试页面 `test_ws.html` 监控分析进度

## 🔍 API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ⚠️ 注意事项

1. 数据文件要求
   - 必须提供 query_list_3.csv 文件
   - 确保文件编码为 UTF-8
   - 文件格式：包含 Keyword 和 Count 列

2. 内存要求
   - 建议系统内存 8GB 以上
   - 监控日志中的内存使用情况

3. 数据库配置
   - 确保 MySQL 配置适合大数据量处理
   - 建议设置适当的连接池大小

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- FastAPI
- SQLAlchemy
- pandas
- 其他开源项目

## 📧 联系方式

- 项目问题请提交 Issue
- 其他问题请联系：quensol@qq.com