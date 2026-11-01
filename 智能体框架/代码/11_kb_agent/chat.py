"""11 | 知识库问答：带权限、引用、拒答。

运行：
    python 11_kb_agent/chat.py                      # 交互（普通员工）
    python 11_kb_agent/chat.py "年假有几天"          # 单次
    python 11_kb_agent/chat.py --as-hr "P7 薪资范围"  # 以 HR 身份
    python 11_kb_agent/chat.py --acl-demo            # 权限对比演示
    python 11_kb_agent/chat.py --compare "年假"      # 检索策略对比
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.prompts import ChatPromptTemplate

from common import get_model, print_divider
from kb_core import (
    is_relevant, load_store, retrieve_with_acl, user_acls,
)

SYSTEM = """你是公司内部知识库助手。

【回答规则】
1. 只依据【资料】回答，不使用资料外的知识。
2. 每个结论后用 [编号] 标注来源。
3. 资料不足以回答时，明确说「知识库中没有找到相关信息」，并建议咨询对应部门。
4. 回答控制在 200 字以内。
5. 涉及金额、天数、比例，必须与资料完全一致。

【资料】
{docs}
"""

CITE_RE = re.compile(r"\[(\d+)\]")

NO_ANSWER = """知识库中没有找到与「{q}」直接相关的内容。

建议：
- 换个说法再问（例如用制度名称、流程名称）
- 咨询 {dept}
"""

DEPT_ROUTING = [
    (("请假", "年假", "病假", "考勤", "入职", "离职"), "HR"),
    (("报销", "发票", "付款", "差旅"), "财务部"),
    (("VPN", "账号", "密码", "电脑", "网络", "软件"), "IT 服务台"),
]


def suggest_dept(q: str) -> str:
    for kws, dept in DEPT_ROUTING:
        if any(k in q for k in kws):
            return dept
    return "相关部门"


def validate_citations(answer: str, docs: list[dict]) -> tuple[str, list[dict]]:
    """只保留指向真实资料的引用编号，返回 (清洗后回答, 实际用到的资料)。

    模型编造编号是很常见的（它想显得"有出处"）。
    如果不校验，用户点 [9] 会找不到东西 —— 引用的公信力就没了。
    """
    valid = {str(i) for i in range(1, len(docs) + 1)}
    used: set[int] = set()

    def fix(m):
        n = m.group(1)
        if n in valid:
            used.add(int(n))
            return m.group(0)
        return ""

    cleaned = CITE_RE.sub(fix, answer)

    # 删掉编号后可能留下「另见 。」「参见 、」这类残句，一并清掉
    cleaned = re.sub(r"(另见|参见|详见|参考)\s*[、，。；]?", "", cleaned)
    cleaned = re.sub(r"[、，；]\s*(?=[。！？])", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    return cleaned, [docs[i - 1] for i in sorted(used)]


def answer(question: str, store, model, user: dict, verbose: bool = True) -> dict:
    acls = user_acls(user)
    docs = retrieve_with_acl(store, question, acls, top_n=4)

    if verbose:
        print(f"\n  [用户] {user['name']}（{user.get('dept', '?')}）"
              f" ACL={acls}")
        print(f"  [检索] 命中 {len(docs)} 条")
        for i, d in enumerate(docs, 1):
            print(f"    [{i}] {d['title']} / {d['section']}  "
                  f"更新={d['updated_at']}")

    if not is_relevant(docs, question):
        return {
            "answer": NO_ANSWER.format(q=question, dept=suggest_dept(question)),
            "sources": [],
            "relevant": False,
        }

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", "{question}"),
    ])

    docs_text = "\n\n---\n\n".join(
        f"[{i}] 《{d['title']}》— {d['section'] or '正文'}（更新于 {d['updated_at']}）\n"
        f"{d['content']}"
        for i, d in enumerate(docs, 1)
    )

    resp = (prompt | model).invoke({"docs": docs_text, "question": question})
    text, sources = validate_citations(resp.content, docs)

    # 时效提示
    note = ""
    if sources:
        oldest = min(s["updated_at"] for s in sources)
        if oldest < "2025-06-01":
            note = f"\n\n⚠️ 引用内容最早更新于 {oldest}，可能已过时，建议确认。"

    return {
        "answer": text + note,
        "sources": sources,
        "relevant": True,
    }


def print_result(r: dict) -> None:
    print(f"\n  【回答】\n    {r['answer']}")
    if r["sources"]:
        print("\n  【来源】")
        for i, s in enumerate(r["sources"], 1):
            print(f"    [{i}] 《{s['title']}》{(' — ' + s['section']) if s['section'] else ''}"
                  f"  (更新于 {s['updated_at']})")


def acl_demo(store, model) -> None:
    print_divider("权限对比演示")

    question = "P7 的薪资范围是多少？"

    users = [
        {"name": "张三", "dept": "研发", "departments": ["RD"]},
        {"name": "李四", "dept": "HR", "departments": ["HR"]},
        {"name": "王五", "dept": "财务", "departments": ["FINANCE"],
         "level": "manager"},
    ]

    for u in users:
        print(f"\n{'━' * 65}")
        r = answer(question, store, model, u)
        print_result(r)

    print_divider("关键点")
    print("""
  · 张三（研发普通员工）→ 检索不到薪酬文档 → 拒答
  · 李四（HR）        → 能检索到 → 正常回答
  · 王五（管理者）     → 薪酬文档的 acl 是 dept:HR / level:manager
                        有 level:manager 就能命中

  ⚠️ 权限过滤必须在「检索阶段」做（SQL 的 WHERE acl && user_acls）。
     如果先取回再过滤，会导致：结果数量不足、排序失真、日志泄露。
""")


def compare(question: str, store, model, user: dict) -> None:
    print_divider(f"检索策略对比：「{question}」")

    acls = user_acls(user)
    for name, top_n in [("只取 2 条", 2), ("取 4 条", 4), ("取 8 条", 8)]:
        docs = retrieve_with_acl(store, question, acls, top_n=top_n)
        print(f"\n  【{name}】相对={is_relevant(docs, question)}")
        for i, d in enumerate(docs, 1):
            print(f"    [{i}] {d['title']} / {d['section']}")


def main() -> None:
    store = load_store()
    model = get_model()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--acl-demo" in sys.argv:
        acl_demo(store, model)
        return

    user = {
        "name": "王五" if "--as-hr" in sys.argv else "张三",
        "dept": "HR" if "--as-hr" in sys.argv else "研发",
        "departments": ["HR"] if "--as-hr" in sys.argv else ["RD"],
        "level": "manager" if "--as-hr" in sys.argv else "staff",
    }

    if "--compare" in sys.argv and args:
        compare(args[0], store, model, user)
        return

    if args:
        r = answer(args[0], store, model, user)
        print_result(r)
        return

    print_divider(f"知识库问答（当前用户：{user['name']}）")
    print("  输入 q 退出。试试：")
    print("    · 入职满三年有几天年假？")
    print("    · 出差住酒店能报多少？")
    print("    · VPN 连不上怎么办？")
    print("    · P7 薪资范围是多少？（普通员工会被拒）")
    print("    · 公司有食堂吗？（应该拒答）")
    print("  提示：加 --as-hr 用 HR 身份再问薪资问题\n")

    while True:
        try:
            q = input("  问：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in ("q", "quit", "exit"):
            break
        print_result(answer(q, store, model, user))
        print()


if __name__ == "__main__":
    main()
