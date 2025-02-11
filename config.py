class Config:
    # 基础配置
    DEBUG = False
    SECRET_KEY = 'your_secret_key' #可不配置
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tickethunter.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 大模型API配置-通义
    DASHSCOPE_API_KEY = 'your_dashscope_api_key' #需要填写你的通义千问api
    # 小红书配置
    XIAOHONGSHU_COOKIE = 'your_cookie' #需要填写你的小红书cookie
    XIAOHONGSHU_COOKIE_UPDATE_TIME = '2025-02-11'
    XIAOHONGSHU_COOKIE_EXPIRE_DAYS = 7
    
    # 小红书API配置-COZE-无需修改
    COZE_API_KEY = 'pat_tFcI9ZoTl6AhvBGXoQnEfN7n5hA15KaTZqpkZkilaJNu9Lzk0pO7wg8j5wPjgni2'
    COZE_WORKFLOW_ID = '7470156811250090036'
    
    # 监控配置
    MONITOR_INTERVAL = 300  # 5分钟
    
    # 缓存配置
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # 限流配置
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'log/tickethunter.log'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = 1024 * 1024  # 1MB
    LOG_BACKUP_COUNT = 5

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tickethunter_dev.db'

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    MONITOR_INTERVAL = 600  # 10分钟 