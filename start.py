import os
import sys
import subprocess
import time
import platform
import socket
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('tickethunter.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logger.error("Python版本必须 >= 3.8")
        sys.exit(1)
    logger.info(f"Python版本检查通过: {sys.version}")

def check_redis():
    """检查Redis服务是否运行"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        logger.info("Redis连接成功")
        return True
    except:
        logger.error("Redis服务未启动，请先启动Redis服务")
        return False

def check_mysql():
    """检查MySQL连接"""
    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        conn.close()
        logger.info("MySQL连接成功")
        return True
    except Exception as e:
        logger.error(f"MySQL连接失败: {str(e)}")
        return False

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_redis():
    """启动Redis服务"""
    if platform.system() == 'Windows':
        try:
            subprocess.Popen(['redis-server'], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE)
            time.sleep(2)  # 等待Redis启动
            logger.info("Redis服务已启动")
        except Exception as e:
            logger.error(f"Redis启动失败: {str(e)}")
    else:
        logger.info("请手动确保Redis服务已启动")

def start_celery():
    """启动Celery工作进程"""
    if platform.system() == 'Windows':
        celery_cmd = 'celery -A app.celery worker --pool=solo --loglevel=info'
    else:
        celery_cmd = 'celery -A app.celery worker --loglevel=info'
    
    try:
        subprocess.Popen(celery_cmd.split(), 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        logger.info("Celery工作进程已启动")
    except Exception as e:
        logger.error(f"Celery启动失败: {str(e)}")

def start_flask():
    """启动Flask应用"""
    if not is_port_in_use(5000):
        try:
            subprocess.Popen([sys.executable, 'app.py'],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            logger.info("Flask应用已启动")
        except Exception as e:
            logger.error(f"Flask应用启动失败: {str(e)}")
    else:
        logger.error("端口5000已被占用，请检查是否有其他服务正在运行")

def check_api_key():
    """检查API密钥是否已配置"""
    try:
        with open('ticket_analyzer.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'Your API Key' in content:
                logger.warning("请先在ticket_analyzer.py中配置通义千问API密钥")
                return False
    except Exception as e:
        logger.error(f"API密钥检查失败: {str(e)}")
        return False
    return True

def main():
    """主函数"""
    logger.info("开始启动TicketHunter服务...")
    
    # 环境检查
    check_python_version()
    
    # 检查API密钥
    if not check_api_key():
        sys.exit(1)
    
    # 检查并启动Redis
    if not check_redis():
        start_redis()
        time.sleep(2)  # 等待Redis完全启动
        if not check_redis():
            sys.exit(1)
    
    # 检查MySQL
    if not check_mysql():
        sys.exit(1)
    
    # 启动服务
    start_celery()
    time.sleep(2)  # 等待Celery启动
    start_flask()
    
    logger.info("""
    TicketHunter服务已启动完成！
    =================================
    - Web界面: http://localhost:5000
    - Celery工作进程: 已启动
    - Redis服务: 运行中
    - MySQL数据库: 已连接
    =================================
    按Ctrl+C可以停止服务
    """)

if __name__ == "__main__":
    try:
        main()
        # 保持脚本运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("正在停止服务...")
        sys.exit(0) 