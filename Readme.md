# TicketHunter 票务监控系统

## 项目简介
TicketHunter是一个智能票务监控和分析系统，专门用于追踪和分析小红书平台上的票务信息。该系统能够自动检测、分析和管理演出票务相关信息，为用户提供实时的票务监控服务。

## 主要功能
- 🎫 智能票务识别：使用通义千问AI模型自动识别和分析票务信息
- 🔍 实时搜索：支持关键词搜索票务信息
- 📊 数据展示：直观展示票务数据和搜索结果
- 🔄 实时更新：使用SSE（Server-Sent Events）实现实时数据推送
- 🛡️ 安全防护：内置访问频率限制和错误处理机制
- 💾 数据持久化：使用SQLite数据库存储历史数据

## 技术栈
- 后端：Flask
- 数据库：SQLite
- AI模型：通义千问API
- 前端：Bootstrap + jQuery
- 实时通信：Server-Sent Events (SSE)

## 环境要求
- Python 3.8+
- 现代浏览器（支持SSE）
- Windows/Linux/MacOS

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/YiCheng996/tickethunter.git
cd tickethunter
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置API密钥
修改`config.py`中的配置信息：
```python
class Config:
    # 通义千问API配置
    DASHSCOPE_API_KEY = 'your_api_key'
       
    # 小红书配置
    XIAOHONGSHU_COOKIE = 'your_cookie'
    XIAOHONGSHU_COOKIE_UPDATE_TIME = '2024-02-11'  # Cookie更新时间
    XIAOHONGSHU_COOKIE_EXPIRE_DAYS = 7  # Cookie有效期
```

### 4. 启动应用
```bash
python app.py
```

### 5. 访问系统
启动成功后，访问：http://localhost:5000

## 目录结构
```
tickethunter/
├── app.py              # Flask主应用
├── config.py           # 配置文件
├── database.py         # 数据库模型
├── requirements.txt    # 项目依赖
├── templates/          # 前端模板
│   └── index.html     # 主页面
└── log/               # 日志目录
    └── tickethunter.log
```

## 功能说明

### 1. 搜索功能
- 支持关键词搜索
- 实时显示搜索进度
- 自动分析票务信息

### 2. 任务管理
- 查看任务状态
- 停止运行中的任务
- 删除历史任务

### 3. 数据展示
- 票务信息表格展示
- 支持查看原文链接
- 按时间排序

### 4. 实时更新
- SSE实时推送
- 自动更新任务状态
- 实时显示新票务信息

## 常见问题

### 1. API调用失败
- 检查API密钥是否正确配置
- 确认API密钥额度是否充足
- 查看日志文件获取详细错误信息

### 2. Cookie过期
- 更新config.py中的Cookie信息
- 修改Cookie更新时间
- 注意Cookie有效期设置

### 3. 搜索无结果
- 确认关键词是否准确
- 检查网络连接状态
- 查看后台日志排查原因

## 开发指南

### 日志系统
- 日志文件位置：`log/tickethunter.log`
- 使用rotating handler防止日志文件过大
- 同时输出到控制台和文件

### 错误处理
- API调用错误自动重试
- 数据库操作事务管理
- SSE连接自动重连

### 数据安全
- 防SQL注入
- 请求频率限制
- 敏感信息加密存储

## 许可证
MIT License

## 联系方式
如有问题或建议，请提交Issue或Pull Request
