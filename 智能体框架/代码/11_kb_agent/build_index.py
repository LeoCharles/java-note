"""11 | 建索引（带权限元数据）。

运行：
    python 11_kb_agent/build_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kb_core import DOCS_DIR, build_and_save, load_docs_with_acl


def main() -> None:
    print("=" * 60)
    print("  建立知识库索引")
    print("=" * 60)

    docs = load_docs_with_acl()
    print(f"\n  发现 {len(docs)} 篇文档：")
    for d in docs:
        print(f"    · {d['title']:20s} ACL={d['acl']}  更新={d['updated_at']}")

    print()
    build_and_save()

    print("\n  下一步：")
    print("    python 11_kb_agent/chat.py")
    print("    python 11_kb_agent/chat.py \"年假有几天\"")
    print("    权限演示：python 11_kb_agent/chat.py --acl-demo")


if __name__ == "__main__":
    main()
