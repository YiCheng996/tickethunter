import requests
import json
import mysql.connector
from datetime import datetime

# MySQL配置
MYSQL_CONFIG = {
    'host': 'rm-2zewskw4o96ls403meo.mysql.rds.aliyuncs.com',
    'user': 'root',
    'password': 'lth2010A',
    'database': 'xhs',
    'charset': 'utf8mb4'
}

def create_tables():
    """创建存储工作流结果和小红书笔记的数据表"""
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 设置数据库连接的字符集
    cursor.execute("SET NAMES utf8mb4")
    cursor.execute("SET CHARACTER SET utf8mb4")
    cursor.execute("SET character_set_connection=utf8mb4")
    
    # 工作流执行记录表
    workflow_table_sql = """
    CREATE TABLE IF NOT EXISTS workflow_executions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code INT,
        cost VARCHAR(50),
        debug_url VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        msg VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        token INT,
        raw_response JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    # 小红书笔记数据表
    notes_table_sql = """
    CREATE TABLE IF NOT EXISTS xhs_notes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        workflow_execution_id INT,
        note_id VARCHAR(50),
        author_id VARCHAR(50),
        author_nickname VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        author_avatar VARCHAR(255),
        author_homepage VARCHAR(255),
        title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        create_time DATETIME,
        update_time DATETIME,
        liked_count INT,
        collected_count INT,
        comment_count INT,
        share_count INT,
        note_url VARCHAR(255),
        images_json TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        tags_json TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
        raw_note_data JSON,  -- 新增字段，用于存储完整的笔记数据
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workflow_execution_id) REFERENCES workflow_executions(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    cursor.execute(workflow_table_sql)
    cursor.execute(notes_table_sql)
    conn.commit()
    cursor.close()
    conn.close()

def save_to_mysql(response_data):
    """保存工作流执行结果和小红书笔记数据到MySQL"""
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 清理emoji的函数
        def remove_emoji(text):
            if not isinstance(text, str):
                return text
                
            import re
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE)
            return emoji_pattern.sub(r'', text)
        
        print("\n开始保存数据...")
        
        # 1. 保存工作流执行记录
        workflow_sql = """
        INSERT INTO workflow_executions 
        (code, cost, debug_url, msg, token, raw_response)
        VALUES 
        (%s, %s, %s, %s, %s, %s)
        """
        
        workflow_values = (
            response_data.get('code', 0),
            response_data.get('cost', '0'),
            '',   # debug_url
            '',   # msg
            0,    # token
            json.dumps(response_data, ensure_ascii=False)  # 原始响应
        )
        
        cursor.execute(workflow_sql, workflow_values)
        workflow_execution_id = cursor.lastrowid
        print(f"工作流记录ID: {workflow_execution_id}")
        
        # 2. 解析并保存所有笔记数据
        note_sql = """
        INSERT INTO xhs_notes 
        (workflow_execution_id, note_id, author_id, author_nickname,
        author_avatar, author_homepage, title, description,
        create_time, update_time, liked_count, collected_count,
        comment_count, share_count, note_url, images_json, tags_json,
        raw_note_data)
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # 解析数据结构
        content_data = json.loads(response_data['data'])
        notes_data = json.loads(content_data['data'])
        
        # 遍历所有笔记数据
        for i, note_item in enumerate(notes_data):
            print(f"\n处理第 {i+1} 条笔记:")
            note_data = note_item['data']['note']
            
            # 获取并打印note_desc
            note_desc = note_data.get('note_desc', '')
            print(f"笔记描述: {note_desc}")
            
            note_values = (
                workflow_execution_id,
                note_data.get('note_id', ''),
                note_data.get('auther_user_id', ''),
                remove_emoji(note_data.get('auther_nick_name', '')),
                note_data.get('auther_avatar', ''),
                note_data.get('auther_home_page_url', ''),
                remove_emoji(note_data.get('note_display_title', '')),
                note_desc,  # 直接保存原始note_desc，不移除emoji
                note_data.get('note_create_time', ''),
                note_data.get('note_last_update_time', ''),
                int(note_data.get('note_liked_count', 0)),
                int(note_data.get('collected_count', 0)),
                int(note_data.get('comment_count', 0)),
                int(note_data.get('share_count', 0)),
                note_data.get('note_url', ''),
                json.dumps(note_data.get('note_image_list', []), ensure_ascii=False),
                json.dumps(note_data.get('note_tags', []), ensure_ascii=False),
                json.dumps(note_data, ensure_ascii=False)  # 保存完整的笔记数据
            )
            
            cursor.execute(note_sql, note_values)
            print(f"已保存第 {i+1} 条笔记数据")
        
        conn.commit()
        print("\n所有数据已成功保存到MySQL")
        
        # 验证数据是否保存成功
        print("\n验证保存的数据:")
        cursor.execute(f"""
            SELECT id, note_id, description 
            FROM xhs_notes 
            WHERE workflow_execution_id = {workflow_execution_id}
        """)
        notes_result = cursor.fetchall()
        print(f"笔记记录数量: {len(notes_result)}")
        for note in notes_result:
            print(f"\nID: {note[0]}")
            print(f"Note ID: {note[1]}")
            print(f"Description: {note[2]}")
        
    except Exception as e:
        print(f"\n保存数据时出错: {str(e)}")
        print("错误详情:", e.__class__.__name__)
        import traceback
        print(traceback.format_exc())
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    try:
        # 确保数据表存在
        create_tables()
        
        url = "https://api.coze.cn/v1/workflow/run"
        headers = {
            "Authorization": "Bearer pat_rpq7IBxqlMNQuGDWLuiks6kC5Z87kvu2nX2pPAT6CFLa3zmD28YDvxr5Mi7OyB1E",
            "Content-Type": "application/json"
        }
        data = {
            "workflow_id": "7433327654700875786",
            "is_async": False,
            "parameters": {
                "BOT_USER_INPUT": "上海major"
            }
        }

        print("\n发送请求:")
        print("URL:", url)
        print("Headers:", json.dumps(headers, indent=2, ensure_ascii=False))
        print("Request Data:", json.dumps(data, indent=2, ensure_ascii=False))

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        print("\n接口返回原始数据:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        print("\n解析后的笔记数据:")
        for i in range(len(response_data)):
            if str(i) in response_data:
                note_data = response_data[str(i)]['data']['note']
                print(f"\n第 {i+1} 条笔记:")
                print(json.dumps(note_data, indent=2, ensure_ascii=False))
        
        save_to_mysql(response_data)
        
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {str(e)}")
    except Exception as e:
        print(f"处理数据时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()