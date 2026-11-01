"""04 | 检索评测：Recall@k 与拒答率。

对应文档：04-RAG检索增强生成.md「评测」

运行：
    python 04_rag/eval_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_lib import is_relevant, load_index, retrieve

CASES_FILE = Path(__file__).resolve().parent / "eval_cases.json"


def load_cases() -> list[dict]:
    if not CASES_FILE.exists():
        raise SystemExit(f"评测集不存在：{CASES_FILE}")
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def eval_retrieval(store, cases: list[dict], use_hybrid: bool, use_rerank: bool):
    recalls, mrrs, details = [], [], []

    for c in cases:
        if not c.get("answerable", True):
            continue
        docs = retrieve(store, c["question"], top_n=5,
                        use_hybrid=use_hybrid, use_rerank=use_rerank)
        expected = set(c.get("expected_sources", []))
        hits = [i + 1 for i, d in enumerate(docs) if d["title"] in expected]

        recall = 1.0 if hits else 0.0
        mrr = 1.0 / hits[0] if hits else 0.0
        recalls.append(recall)
        mrrs.append(mrr)
        details.append({
            "id": c["id"], "question": c["question"],
            "hit": bool(hits), "rank": hits[0] if hits else None,
            "got": [d["title"] for d in docs[:3]],
        })

    return {
        "recall@5": sum(recalls) / len(recalls) if recalls else 0,
        "mrr": sum(mrrs) / len(mrrs) if mrrs else 0,
        "details": details,
    }


def eval_refusal(store, cases: list[dict], use_hybrid: bool, use_rerank: bool):
    tp = fp = fn = tn = 0
    details = []

    for c in cases:
        docs = retrieve(store, c["question"], use_hybrid=use_hybrid,
                        use_rerank=use_rerank)
        refused = not is_relevant(docs)
        answerable = c.get("answerable", True)

        if answerable and not refused:
            tp += 1
        elif answerable and refused:
            fn += 1
        elif not answerable and refused:
            tn += 1
        else:
            fp += 1

        details.append({
            "id": c["id"], "question": c["question"],
            "answerable": answerable, "refused": refused,
            "top_score": max((d["score"] for d in docs), default=0),
            "verdict": "ok" if (answerable != refused) else "WRONG",
        })

    def safe(a, b):
        return a / b if b else 0

    return {
        "覆盖率(该答且答了)": safe(tp, tp + fn),
        "误拒率(该答却拒了)": safe(fn, tp + fn),
        "拒答准确率(不该答且拒了)": safe(tn, tn + fp),
        "瞎答率(不该答却答了)": safe(fp, tn + fp),
        "details": details,
    }


def main() -> None:
    store = load_index()
    cases = load_cases()

    print("=" * 70)
    print(f"  评测集：{len(cases)} 条"
          f"（可回答 {sum(1 for c in cases if c.get('answerable', True))} 条，"
          f"不可回答 {sum(1 for c in cases if not c.get('answerable', True))} 条）")
    print("=" * 70)

    configs = [
        ("纯向量", False, False),
        ("向量 + 关键词", True, False),
        ("混合 + 重排", True, True),
    ]

    summary = []
    for name, hybrid, rerank in configs:
        print(f"\n{'─' * 70}")
        print(f"  【{name}】")
        print(f"{'─' * 70}")

        r = eval_retrieval(store, cases, hybrid, rerank)
        print(f"  Recall@5 = {r['recall@5']:.1%}   MRR = {r['mrr']:.3f}")

        misses = [d for d in r["details"] if not d["hit"]]
        if misses:
            print(f"  未召回的 {len(misses)} 条：")
            for d in misses[:5]:
                print(f"    ✗ {d['question']}")
                print(f"      期望：{d['id']}  实际：{d['got']}")

        ref = eval_refusal(store, cases, hybrid, rerank)
        print(f"  答案覆盖率={ref['覆盖率(该答且答了)']:.1%}  "
              f"误拒率={ref['误拒率(该答却拒了)']:.1%}")
        print(f"  拒答准确率={ref['拒答准确率(不该答且拒了)']:.1%}  "
              f"瞎答率={ref['瞎答率(不该答却答了)']:.1%}  ← 最需要关注的指标")

        wrong = [d for d in ref["details"] if d["verdict"] == "WRONG"]
        if wrong:
            print(f"  判定错误的 {len(wrong)} 条：")
            for d in wrong:
                kind = "瞎答" if d["answerable"] is False else "误拒"
                print(f"    ✗ [{kind}] {d['question']}  top_score={d['top_score']:.3f}")

        summary.append((name, r["recall@5"], ref["瞎答率(不该答却答了)"]))

    print("\n" + "=" * 70)
    print("  汇总")
    print("=" * 70)
    print(f"  {'策略':20s} {'Recall@5':>10s} {'瞎答率':>10s}")
    for name, rec, wrong in summary:
        print(f"  {name:20s} {rec:>9.1%} {wrong:>9.1%}")

    print("\n  👉 把这张表放进项目汇报，比任何形容词都有说服力。")
    print("  👉 阈值在 config.py 的 MIN_RELEVANCE，调它看瞎答率和误拒率的权衡。")


if __name__ == "__main__":
    main()
