# TicketHunter 票务监控系统

## 项目简介
TicketHunter是一个智能票务监控和分析系统，专门用于追踪和分析社交媒体平台上的票务信息。该系统能够自动检测、分析和管理演出票务相关信息，为用户提供实时的票务监控服务。

## 主要功能
- 🎫 智能票务识别：使用通义千问AI模型自动识别和分析票务信息
- 📊 数据可视化：直观展示票务数据和统计信息
- 🔍 实时监控：支持多平台票务信息实时追踪
- 🔔 自动提醒：设置关键词后自动推送相关票务信息
- 🛡️ 安全防护：内置访问频率限制和用户认证机制
- 💾 数据持久化：使用MySQL数据库存储历史数据

## 技术栈
- 后端：Flask + Celery
- 数据库：MySQL + Redis
- AI模型：通义千问API
- 前端：HTML + JavaScript
- 任务调度：APScheduler

## 环境要求
- Python 3.8+
- MySQL 5.7+
- Redis 6.0+
- Windows/Linux/MacOS

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/tickethunter.git
cd tickethunter
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置数据库
1. 在MySQL中创建数据库
```sql
CREATE DATABASE tickethunter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改`config.py`中的数据库配置
```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'tickethunter'
}
```

### 4. 配置API密钥
在`ticket_analyzer.py`中设置通义千问API密钥：
```python
dashscope.api_key = "your_api_key"
```

### 5. 一键启动
```bash
python start.py
```
启动脚本会自动：
- ✅ 检查环境依赖
- ✅ 验证API密钥配置
- ✅ 启动Redis服务（Windows）
- ✅ 启动Celery工作进程
- ✅ 启动Flask应用
- ✅ 提供详细的启动日志

### 6. 访问系统
启动成功后，访问：http://localhost:5000

## 目录结构
```
tickethunter/
├── app.py              # Flask主应用
├── config.py           # 配置文件
├── monitor.py          # 监控模块
├── ticket_analyzer.py  # 票务分析模块
├── start.py           # 一键启动脚本
├── requirements.txt    # 项目依赖
├── templates/         # 前端模板
└── static/           # 静态资源
```

## 常见问题

### 1. Redis启动失败
- Windows: 确保Redis已正确安装并添加到环境变量
- Linux/Mac: 使用包管理器安装并启动Redis服务
```bash
# Ubuntu/Debian
sudo service redis-server start

# MacOS
brew services start redis
```

### 2. Celery启动问题
- Windows环境需要使用`--pool=solo`参数
- 确保Redis服务正在运行
- 检查项目路径是否正确

### 3. MySQL连接失败
- 检查MySQL服务是否运行
- 验证数据库用户名和密码
- 确保数据库已创建且字符集正确

### 4. API密钥配置
- 在通义千问官网申请API密钥
- 正确配置在`ticket_analyzer.py`中
- 注意保护API密钥安全

## 开发指南
1. 代码规范
   - 遵循PEP 8规范
   - 使用Black进行代码格式化
   - 运行Flake8进行代码检查

2. 测试
   - 使用pytest编写单元测试
   - 运行测试：`pytest tests/`

3. 日志
   - 日志文件位置：`tickethunter.log`
   - 使用rotating handler防止日志文件过大
   - 同时输出到控制台和文件

## 许可证
MIT License

## 联系方式
如有问题或建议，请提交Issue或Pull Request
