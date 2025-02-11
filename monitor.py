import time
import threading
import schedule
from datetime import datetime
import mysql.connector
from coze_workflow_demo import MYSQL_CONFIG
import requests
import json
from ticket_analyzer import analyze_ticket_content

class TicketMonitor:
    def __init__(self):
        self.create_monitor_table()
        
    def create_monitor_table(self):
        """创建监控任务表"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 创建监控任务表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS monitor_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                keyword VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                is_active BOOLEAN DEFAULT TRUE,
                last_run DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_keyword (keyword),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_sql)
            
            # 创建监控历史记录表
            create_history_table_sql = """
            CREATE TABLE IF NOT EXISTS monitor_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT,
                note_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES monitor_tasks(id),
                FOREIGN KEY (note_id) REFERENCES xhs_notes(note_id),
                UNIQUE KEY unique_task_note (task_id, note_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_history_table_sql)
            conn.commit()
            
        except Exception as e:
            print(f"创建监控表时出错: {str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def add_task(self, keyword):
        """添加监控任务"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            sql = """
            INSERT INTO monitor_tasks (keyword) 
            VALUES (%s)
            """
            cursor.execute(sql, (keyword,))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"添加监控任务失败: {str(e)}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_active_tasks(self):
        """获取所有活动的监控任务"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        try:
            sql = "SELECT * FROM monitor_tasks WHERE is_active = TRUE"
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def check_note_history(self, task_id, note_id):
        """检查笔记是否已经处理过"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            sql = """
            SELECT COUNT(*) FROM monitor_history 
            WHERE task_id = %s AND note_id = %s
            """
            cursor.execute(sql, (task_id, note_id))
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            cursor.close()
            conn.close()
    
    def add_note_history(self, task_id, note_id):
        """添加处理记录"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            sql = """
            INSERT INTO monitor_history (task_id, note_id)
            VALUES (%s, %s)
            """
            cursor.execute(sql, (task_id, note_id))
            conn.commit()
        except Exception as e:
            print(f"添加历史记录失败: {str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def update_task_time(self, task_id):
        """更新任务最后执行时间"""
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        try:
            sql = """
            UPDATE monitor_tasks 
            SET last_run = NOW() 
            WHERE id = %s
            """
            cursor.execute(sql, (task_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    
    def execute_task(self, task):
        """执行单个监控任务"""
        print(f"\n执行监控任务 - 关键词: {task['keyword']}")
        
        # 调用COZE API
        url = "https://api.coze.cn/v1/workflow/run"
        headers = {
            "Authorization": "Bearer pat_rpq7IBxqlMNQuGDWLuiks6kC5Z87kvu2nX2pPAT6CFLa3zmD28YDvxr5Mi7OyB1E",
            "Content-Type": "application/json"
        }
        data = {
            "workflow_id": "7433327654700875786",
            "is_async": False,
            "parameters": {
                "BOT_USER_INPUT": task['keyword']
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()
            
            # 解析笔记数据
            content_data = json.loads(response_data['data'])
            notes_data = json.loads(content_data['data'])
            
            for note_item in notes_data:
                note_data = note_item['data']['note']
                note_id = note_data.get('note_id')
                
                # 检查是否已处理过
                if not self.check_note_history(task['id'], note_id):
                    note_desc = note_data.get('note_desc', '')
                    
                    # 使用通义千问分析内容
                    ticket_info = analyze_ticket_content(note_desc)
                    if ticket_info['is_ticket_resale']:
                        # 保存分析结果到数据库
                        conn = mysql.connector.connect(**MYSQL_CONFIG)
                        try:
                            from ticket_analyzer import save_ticket_info
                            save_ticket_info(conn, note_id, ticket_info)
                        finally:
                            conn.close()
                    
                    # 添加到历史记录
                    self.add_note_history(task['id'], note_id)
            
            # 更新任务执行时间
            self.update_task_time(task['id'])
            
        except Exception as e:
            print(f"执行监控任务失败: {str(e)}")
    
    def run_monitor(self):
        """执行所有监控任务"""
        tasks = self.get_active_tasks()
        for task in tasks:
            self.execute_task(task)
    
    def start_scheduler(self):
        """启动定时任务"""
        schedule.every(15).minutes.do(self.run_monitor)
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def start(self):
        """启动监控服务"""
        print("启动票务监控服务...")
        # 在新线程中运行调度器
        threading.Thread(target=self.start_scheduler, daemon=True).start() 