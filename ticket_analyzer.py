import json
import dashscope
from dashscope import Generation
from datetime import datetime

# 设置通义千问API密钥
dashscope.api_key = "Your API Key"

def analyze_ticket_content(note_desc):
    """
    使用通义千问分析笔记内容中的票务信息
    """
    prompt = f"""
请分析以下小红书笔记内容，判断是否涉及演出票务转售。如果涉及，请提取以下信息：
1. 是否转售票务（true/false）
2. 演出名称（如：上海Major）
3. 城市（如：上海）
4. 场次日期（如：2024-12-15）
5. 区域位置（如：B区）
6. 票价信息（如：1000元/张）
7. 数量（如：2张）
8. 联系方式（如：私信）
9. 其他备注（如：可刀）

原文：{note_desc}

请按以下JSON格式返回：
{{
    "is_ticket_resale": true/false,
    "event_name": "演出名称",
    "city": "城市",
    "event_date": "场次日期",
    "area": "区域位置",
    "price": "票价信息",
    "quantity": "数量",
    "contact": "联系方式",
    "notes": "其他备注"
}}

如果不是票务转售内容，只返回 {{"is_ticket_resale": false}}，不要返回多余解释
"""

    try:
        response = Generation.call(
            model='qwen-turbo',
            prompt=prompt,
            temperature=0.1,
            top_p=0.8,
            result_format='text'
        )
        
        if response.status_code == 200:
            try:
                # 打印原始响应以便调试
                print("\n原始响应:", response)
                print("响应状态:", response.status_code)
                print("响应输出:", response.output)
                
                # 获取响应文本
                if hasattr(response.output, 'text'):
                    response_text = response.output.text
                elif isinstance(response.output, str):
                    response_text = response.output
                else:
                    response_text = str(response.output)
                
                print("\n响应文本:", response_text)
                
                # 尝试直接解析JSON
                try:
                    result = json.loads(response_text)
                    print("JSON解析成功:", result)
                    return result
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试提取JSON部分
                    try:
                        # 查找第一个 { 和最后一个 } 的位置
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start != -1 and end != -1:
                            json_str = response_text[start:end]
                            print("提取的JSON字符串:", json_str)
                            result = json.loads(json_str)
                            print("JSON解析成功:", result)
                            return result
                        else:
                            print("未找到JSON格式的响应")
                            return {"is_ticket_resale": False}
                    except json.JSONDecodeError as e:
                        print(f"JSON提取解析失败: {e}")
                        print(f"原始响应文本: {response_text}")
                        return {"is_ticket_resale": False}
                
            except Exception as e:
                print(f"解析AI响应失败: {str(e)}")
                print(f"错误类型: {type(e)}")
                print(f"响应内容: {response.output}")
                return {"is_ticket_resale": False}
        else:
            print(f"AI请求失败: {response.status_code}")
            print(f"错误信息: {response.output if hasattr(response, 'output') else '无错误信息'}")
            return {"is_ticket_resale": False}
            
    except Exception as e:
        print(f"调用AI服务出错: {str(e)}")
        print(f"错误类型: {type(e)}")
        import traceback
        print(traceback.format_exc())
        return {"is_ticket_resale": False}

def save_ticket_info(conn, note_id, ticket_info):
    """保存票务分析结果到数据库"""
    cursor = conn.cursor()
    try:
        # 创建票务信息表（如果不存在）
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ticket_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            note_id VARCHAR(50),
            is_ticket_resale BOOLEAN,
            event_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            event_date DATE,
            area VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            price VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            quantity VARCHAR(50),
            contact VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            notes TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES xhs_notes(note_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_sql)
        
        # 插入票务信息
        if ticket_info['is_ticket_resale']:
            insert_sql = """
            INSERT INTO ticket_info 
            (note_id, is_ticket_resale, event_name, event_date, area, 
             price, quantity, contact, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 转换日期格式
            event_date = None
            if ticket_info.get('event_date'):
                try:
                    event_date = datetime.strptime(ticket_info['event_date'], '%Y-%m-%d').date()
                except ValueError:
                    print(f"日期格式转换失败: {ticket_info['event_date']}")
            
            values = (
                note_id,
                ticket_info['is_ticket_resale'],
                ticket_info.get('event_name', ''),
                event_date,
                ticket_info.get('area', ''),
                ticket_info.get('price', ''),
                ticket_info.get('quantity', ''),
                ticket_info.get('contact', ''),
                ticket_info.get('notes', '')
            )
            
            cursor.execute(insert_sql, values)
            conn.commit()
            print(f"票务信息已保存 - Note ID: {note_id}")
        
    except Exception as e:
        print(f"保存票务信息时出错: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()

def process_notes(conn):
    """
    处理数据库中的笔记内容
    """
    cursor = conn.cursor()
    try:
        # 获取所有未分析的笔记
        cursor.execute("SELECT note_id, description FROM xhs_notes WHERE note_id NOT IN (SELECT note_id FROM ticket_info)")
        notes = cursor.fetchall()
        
        for note_id, description in notes:
            print(f"\n分析笔记 {note_id}:")
            print(f"内容: {description}")
            
            # 分析票务信息
            ticket_info = analyze_ticket_content(description)
            print(f"分析结果: {json.dumps(ticket_info, ensure_ascii=False, indent=2)}")
            
            # 保存分析结果
            save_ticket_info(conn, note_id, ticket_info)
            
    except Exception as e:
        print(f"处理笔记时出错: {str(e)}")
    finally:
        cursor.close()

if __name__ == "__main__":
    # 连接数据库
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    try:
        process_notes(conn)
    finally:
        conn.close() 