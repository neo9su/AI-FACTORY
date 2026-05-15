#!/usr/bin/env python3
"""
notify_test.py — 一键验证飞书通知配置的 CLI 工具

用法:
  # 读取 .env 文件中的环境变量
  cd ~/autonomous-ai-factory
  python3 scripts/notify_test.py

  # 指定 Webhook URL（覆盖环境变量）
  python3 scripts/notify_test.py --webhook https://open.feishu.cn/open-apis/bot/v2/hook/xxx

  # 发送所有通知类型
  python3 scripts/notify_test.py --all

  # 指定单一类型
  python3 scripts/notify_test.py --type stage
  python3 scripts/notify_test.py --type task
  python3 scripts/notify_test.py --type test
  python3 scripts/notify_test.py --type delivery
  python3 scripts/notify_test.py --type gate
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# 加载 .env（如果存在）
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.notifier import FeishuNotifier, NotifyContext  # noqa: E402


def _make_ctx(stage: str = "developing") -> NotifyContext:
    return NotifyContext(
        project_id="demo-project-001",
        project_name="🤖 AI Factory 测试项目",
        stage=stage,
        message="这是一条来自 notify_test.py 的测试消息，用于验证飞书通知配置是否正常工作。",
        preview_url="http://localhost:3000/projects/demo",
    )


async def run_tests(notifier: FeishuNotifier, types: list[str]) -> None:
    results = {}

    if "stage" in types:
        print("📤 发送「阶段更新」通知...")
        for stage in ["planning", "developing", "testing", "delivered", "failed"]:
            ctx = _make_ctx(stage)
            r = await notifier.send_stage_update(ctx)
            status = "✅ 成功" if r.success else f"❌ 失败: {r.error}"
            print(f"   {stage:25s} → {status}")
        results["stage"] = True

    if "task" in types:
        print("📤 发送「任务完成」通知...")
        ctx = _make_ctx("developing")
        r = await notifier.send_task_complete(ctx, task_title="实现用户认证模块", task_status="completed", retry_count=0)
        status = "✅ 成功" if r.success else f"❌ 失败: {r.error}"
        print(f"   task_complete (success)  → {status}")

        r2 = await notifier.send_task_complete(ctx, task_title="部署到 Kubernetes", task_status="failed", retry_count=2)
        status2 = "✅ 成功" if r2.success else f"❌ 失败: {r2.error}"
        print(f"   task_complete (failed)   → {status2}")
        results["task"] = True

    if "test" in types:
        print("📤 发送「测试结果」通知...")
        ctx = _make_ctx("testing")
        r = await notifier.send_test_result(ctx, passed=27, failed=0, test_type="unit")
        status = "✅ 成功" if r.success else f"❌ 失败: {r.error}"
        print(f"   test_result (all pass)   → {status}")

        r2 = await notifier.send_test_result(
            ctx,
            passed=24,
            failed=3,
            test_type="integration",
            # 模拟错误日志
        )
        status2 = "✅ 成功" if r2.success else f"❌ 失败: {r2.error}"
        print(f"   test_result (3 failed)   → {status2}")
        results["test"] = True

    if "delivery" in types:
        print("📤 发送「交付报告」通知...")
        ctx = _make_ctx("delivered")
        r = await notifier.send_delivery_report(
            ctx,
            repo_url="https://github.com/org/ai-generated-project",
            preview_url="https://staging.ai-factory.example.com",
            passed_tests=30,
            failed_tests=0,
            known_issues=["首页加载速度有待优化", "移动端适配待完善"],
        )
        status = "✅ 成功" if r.success else f"❌ 失败: {r.error}"
        print(f"   delivery_report          → {status}")
        results["delivery"] = True

    if "gate" in types:
        print("📤 发送「权限门禁」通知...")
        ctx = _make_ctx("blocked_by_gate")
        r = await notifier.send_gate_blocked(
            ctx,
            operation="deploy_to_production",
            reason="生产环境部署需要人工审批，此操作已被 Gatekeeper 拦截。",
        )
        status = "✅ 成功" if r.success else f"❌ 失败: {r.error}"
        print(f"   gate_blocked             → {status}")
        results["gate"] = True

    print()
    if all(results.values()):
        print("🎉 所有通知发送成功！飞书配置正常。")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"⚠️ 以下类型通知发送失败：{failed}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="飞书通知配置验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--webhook", help="Feishu Webhook URL（覆盖环境变量 FEISHU_WEBHOOK_URL）")
    parser.add_argument("--sign-secret", help="签名密钥（覆盖环境变量 FEISHU_SIGN_SECRET）")
    parser.add_argument(
        "--type",
        choices=["stage", "task", "test", "delivery", "gate"],
        default="stage",
        help="要发送的通知类型（默认: stage）",
    )
    parser.add_argument("--all", action="store_true", help="发送所有通知类型")
    args = parser.parse_args()

    webhook = args.webhook or os.getenv("FEISHU_WEBHOOK_URL")
    sign_secret = args.sign_secret or os.getenv("FEISHU_SIGN_SECRET")

    if not webhook:
        print("❌ 错误：未配置 FEISHU_WEBHOOK_URL")
        print("   请在 .env 文件中设置，或用 --webhook 参数传入")
        sys.exit(1)

    print(f"🔗 Webhook: {webhook[:50]}{'...' if len(webhook) > 50 else ''}")
    print(f"🔐 签名:    {'已启用' if sign_secret else '未启用'}")
    print()

    notifier = FeishuNotifier(webhook_url=webhook, sign_secret=sign_secret)

    types = ["stage", "task", "test", "delivery", "gate"] if args.all else [args.type]

    asyncio.run(run_tests(notifier, types))


if __name__ == "__main__":
    main()
