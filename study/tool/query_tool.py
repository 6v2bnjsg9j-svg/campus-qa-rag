import os
import psycopg2
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv(override=True)
DB_DSN = os.getenv("DB_DSN")


@tool
def search_kuan(block_id: int, chapter_id: int, article_id: int) -> str:
    """根据 block_id、chapter_id、article_id 查询该条下面的所有款（具体条款内容）。

    当检索到的文档 is_kuan=True 时，必须调用此工具获取完整条款。

    Args:
        block_id: 条款的块 id
        chapter_id: 条款的章 id
        article_id: 条款的 article_id
    """
    conn = None
    try:
        conn = psycopg2.connect(DB_DSN)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT content
            FROM law_node
            WHERE block_id = %s
              AND chapter_id = %s
              AND article_id = %s
            ORDER BY id
            """,
            (block_id, chapter_id, article_id),
        )
        rows = cur.fetchall()
        cur.close()
        return "\n".join(r[0] for r in rows) if rows else "未找到该条款"
    except Exception as e:
        return f"查询失败: {e}"
    finally:
        if conn:
            conn.close()



@tool
def search_zhang(block_id: int, chapter_id: int)->str:
    """根据 block_id、chapter_id 查询本章内容
    当用户询问概览类问题（如"这一章讲什么""有哪些规定"），
    或检索到的资料标注为"章"级别时，调用此工具获取完整章节。

        Args:
            block_id: 块 id
            chapter_id: 章 id
        """
    conn = None
    try:
        conn = psycopg2.connect(DB_DSN)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT content
            FROM law_node
            WHERE block_id = %s
              AND chapter_id = %s
              AND article_id = 0
            ORDER BY id
            """,
            (block_id, chapter_id),
        )
        rows = cur.fetchall()
        cur.close()
        if not rows:
            return "未找到该章节"
        result = "\n".join(r[0] for r in rows)
        if len(result) > 3000:
            result = result[:3000] + "\n...（内容过长，已截断）"
        return result

    except Exception as e:
        return f"查询失败: {e}"
    finally:
        if conn:
            conn.close()