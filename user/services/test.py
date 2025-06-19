from typing import List, Dict, Tuple
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from user.services.parser import ScheduleParser


def evaluate_all(parser: ScheduleParser, test_cases: List[Tuple[str, Dict]]) -> Dict:
    metrics = {
        "time": {"correct": 0, "total": 0, "startTime_correct": 0, "endTime_correct": 0},

        "content": {"exact_match": 0, "action_verb_correct": 0},

        "resource": {"TP": 0, "FP": 0, "FN": 0},

        "overall": {"perfect_match": 0, "avg_errors": 0},
        "case_details": []
    }

    for text, expected in test_cases:

        result = parser.parse(text, "evaluator")
        case_metrics = {"text": text, "errors": []}

        time_errors = 0
        for field in ["startTime", "endTime"]:
            if field in expected:
                metrics["time"]["total"] += 1
                if result[field] == expected[field]:
                    metrics["time"]["correct"] += 1
                    metrics["time"][f"{field}_correct"] += 1
                else:
                    time_errors += 1
                    case_metrics["errors"].append(f"时间错误({field})")

        if "scheduleContent" in expected:
            if result["scheduleContent"] == expected["scheduleContent"]:
                metrics["content"]["exact_match"] += 1
            else:
                case_metrics["errors"].append("内容不匹配")

            expected_verbs = [v for v in parser.ACTION_VERBS if v in expected["scheduleContent"]]
            actual_verbs = [v for v in parser.ACTION_VERBS if v in result["scheduleContent"]]
            if set(expected_verbs) == set(actual_verbs):
                metrics["content"]["action_verb_correct"] += 1

        if "resource" in expected:
            expected_res = set(expected["resource"])
            actual_res = set(result["resource"].split(",")) if result["resource"] else set()

            tp = len(expected_res & actual_res)
            fp = len(actual_res - expected_res)
            fn = len(expected_res - actual_res)

            metrics["resource"]["TP"] += tp
            metrics["resource"]["FP"] += fp
            metrics["resource"]["FN"] += fn

            if fp > 0:
                case_metrics["errors"].append(f"资源误识别(FP={fp})")
            if fn > 0:
                case_metrics["errors"].append(f"资源漏识别(FN={fn})")

        if len(case_metrics["errors"]) == 0:
            metrics["overall"]["perfect_match"] += 1
        metrics["overall"]["avg_errors"] += len(case_metrics["errors"])

        metrics["case_details"].append(case_metrics)

    metrics["overall"]["avg_errors"] /= len(test_cases)

    metrics["time"]["accuracy"] = (
        metrics["time"]["correct"] / metrics["time"]["total"] if metrics["time"]["total"] > 0 else 0
    )

    tp, fp, fn = metrics["resource"]["TP"], metrics["resource"]["FP"], metrics["resource"]["FN"]
    metrics["resource"]["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0
    metrics["resource"]["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0
    metrics["resource"]["f1"] = (
        2 * metrics["resource"]["precision"] * metrics["resource"]["recall"] /
        (metrics["resource"]["precision"] + metrics["resource"]["recall"])
        if (metrics["resource"]["precision"] + metrics["resource"]["recall"]) > 0 else 0
    )

    return metrics


def print_full_report(metrics: Dict):
    print("\n" + "=" * 80)
    print("调度文本解析综合评估报告".center(70))
    print("=" * 80)

    # 时间解析报告
    print("\n【时间解析】")
    print(f"- 总体准确率: {metrics['time']['accuracy']:.2%}")
    print(f"- 开始时间正确率: {metrics['time']['startTime_correct'] / len(test_cases):.2%}")

    # 任务内容报告
    print("\n【任务内容】")
    print(f"- 完全匹配率: {metrics['content']['exact_match'] / len(test_cases):.2%}")
    print(f"- 动作动词准确率: {metrics['content']['action_verb_correct'] / len(test_cases):.2%}")

    # 资源识别报告
    print("\n【资源识别】")
    print(f"- 精确率: {metrics['resource']['precision']:.2%}")
    print(f"- 召回率: {metrics['resource']['recall']:.2%}")
    print(f"- F1分数: {metrics['resource']['f1']:.4f}")

    errors = [case for case in metrics['case_details'] if case['errors']]
    if errors:
        print("\n【典型错误案例】")
        for case in errors[:30]:
            print(f"\n输入: {case['text']}")
            print("错误类型: " + ", ".join(case['errors']))


now = datetime.now()
today = now.strftime("%Y-%m-%d")
tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
next_day = (now + timedelta(days=2)).strftime("%Y-%m-%d")
test_cases = [
    (
        "明天下午3点在实验室进行设备调试",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=15, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=17, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "进行设备调试",
            "resource": ["实验室"]
        }
    ),
    (
        "明天上午10点-11点在会议室讨论项目进展",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=10, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=11, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "讨论项目进展",
            "resource": ["会议室"]
        }
    ),
    (
        "今天晚上8点部署新版系统，预计需要2小时",
        {
            "startTime": now.replace(hour=20, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=20, minute=0, second=0) + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "部署新版系统",
            "resource": []
        }
    ),
    (
        "后天下午2点评估市场调研结果",
        {
            "startTime": datetime.strptime(next_day, "%Y-%m-%d").replace(hour=14, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(next_day, "%Y-%m-%d").replace(hour=15, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "评估市场调研结果",
            "resource": []
        }
    ),
    (
        "紧急处理打印机故障，尽快恢复使用",
        {
            "startTime": now.replace(hour=14, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=14, minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "处理打印机故障",
            "resource": ["打印机"]
        }
    ),
    (
        "下周三下午3点至5点审核财务报表",
        {
            "startTime": (now + timedelta(days=(2 - now.weekday()) % 7 + 7)).replace(hour=15, minute=0,
                                                                                     second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(2 - now.weekday()) % 7 + 7)).replace(hour=17, minute=0,
                                                                                   second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "审核财务报表",
            "resource": []
        }
    ),
    (
        "今天下午和导师讨论毕业论文修改建议",
        {
            "startTime": now.replace(hour=14, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=14, minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "讨论毕业论文修改建议",
            "resource": []
        }
    ),
    (
        "今晚9点在语音室练习英语口语",
        {
            "startTime": now.replace(hour=21, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=21, minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "练习英语口语",
            "resource": ["语音室"]
        }
    ),
    (
        "下个月15号下午14:00-16:00组织教室卫生检查",
        {
            "startTime": (now + relativedelta(months=1)).replace(day=15, hour=14, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + relativedelta(months=1)).replace(day=15, hour=16, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "组织教室卫生检查",
            "resource": ["教室"]
        }
    ),
    (
        "下下周一下午四点给学生讲解实验原理",
        {
            "startTime": (now + timedelta(days=(0 - now.weekday()) % 7 + 7)).replace(hour=16, minute=0,
                                                                                      second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(0 - now.weekday()) % 7 + 7)).replace(hour=17, minute=0,
                                                                                    second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "讲解实验原理",
            "resource": []
        }
    ),
    (
        "周五晚上7点开部门会议",
        {
            "startTime": (now + timedelta(days=(4 - now.weekday()) % 7)).replace(hour=19, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(4 - now.weekday()) % 7)).replace(hour=20, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "开部门会议",
            "resource": []
        }
    ),
    (
        "今晚10点检查服务器状态",
        {
            "startTime": now.replace(hour=22, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=22, minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "检查服务器状态",
            "resource": ["服务器"]
        }
    ),
    (
        "下周一上午9点准备讲座PPT",
        {
            "startTime": (now + timedelta(days=(0 - now.weekday()) % 7)).replace(hour=9, minute=0,
                                                                                     second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(0 - now.weekday()) % 7)).replace(hour=10, minute=0,
                                                                                   second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "准备讲座PPT",
            "resource": []
        }
    ),
    (
        "今天下午5点半和家人视频通话",
        {
            "startTime": now.replace(hour=17, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=17, minute=30, second=0) + timedelta(minutes=30)).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "和家人视频通话",
            "resource": []
        }
    ),
    (
        "明天早上8点开车送孩子上学",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=8, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=8, minute=30, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "送孩子上学",
            "resource": ["车"]
        }
    ),
    (
        "明天下午两点到三点半参加培训",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=14, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=15, minute=30, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "参加培训",
            "resource": []
        }
    ),
    (
        "今晚整理文件归档",
        {
            "startTime": now.replace(hour=19, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=20, minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "整理文件归档",
            "resource": []
        }
    ),
    (
        "后天上午9点-12点举行招聘面试",
        {
            "startTime": datetime.strptime(next_day, "%Y-%m-%d").replace(hour=9, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(next_day, "%Y-%m-%d").replace(hour=12, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "举行招聘面试",
            "resource": []
        }
    ),
    (
        "下周五在图书馆查阅文献",
        {
            "startTime": (now + timedelta(days=(4 - now.weekday()) % 7 + 7)).replace(hour=14, minute=0,
                                                                                     second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(4 - now.weekday()) % 7 + 7)).replace(hour=15, minute=0,
                                                                                   second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "查阅文献",
            "resource": ["图书馆"]
        }
    ),
    (
        "每周三晚上健身1小时",
        {
            "startTime": (now + timedelta(days=(2 - now.weekday()) % 7)).replace(hour=19, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(2 - now.weekday()) % 7)).replace(hour=20, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "健身",
            "resource": []
        }
    ),
    (
        "周六早上看牙医",
        {
            "startTime": (now + timedelta(days=(5 - now.weekday()) % 7)).replace(hour=9, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(5 - now.weekday()) % 7)).replace(hour=10, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "看牙医",
            "resource": ["牙医"]
        }
    ),
    (
        "明天上午整理报销单据",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=9, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=10, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "整理报销单据",
            "resource": []
        }
    ),
    (
        "本周日参加朋友婚礼",
        {
            "startTime": (now + timedelta(days=(6 - now.weekday()) % 7)).replace(hour=10, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(6 - now.weekday()) % 7)).replace(hour=13, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "参加朋友婚礼",
            "resource": []
        }
    ),
    (
        "下下周二晚上辅导孩子数学作业",
        {
            "startTime": (now + timedelta(days=(1 - now.weekday()) + 14)).replace(hour=19, minute=0,
                                                                                      second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(1 - now.weekday()) + 14)).replace(hour=20, minute=0,
                                                                                    second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "辅导孩子数学作业",
            "resource": []
        }
    ),
    (
        "今天下午四点半开远程会议",
        {
            "startTime": now.replace(hour=16, minute=30, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (now.replace(hour=16, minute=30, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "开远程会议",
            "resource": []
        }
    ),
    (
        "明天下午修改技术文档",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=14, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=15, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "修改技术文档",
            "resource": []
        }
    ),
    (
        "周三上午测试新功能模块",
        {
            "startTime": (now + timedelta(days=(2 - now.weekday()) % 7)).replace(hour=9, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (now + timedelta(days=(2 - now.weekday()) % 7)).replace(hour=11, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "测试新功能模块",
            "resource": []
        }
    ),
    (
        "明天晚上回访客户反馈",
        {
            "startTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=19, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": datetime.strptime(tomorrow, "%Y-%m-%d").replace(hour=20, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "回访客户反馈",
            "resource": []
        }
    ),
    (
        "下午3点在301会议室进行项目评审",
        {
            "startTime": datetime.now().replace(hour=15, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": (datetime.now().replace(hour=15, minute=0, second=0) + timedelta(hours=2)).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "进行项目评审",
            "resource": ["会议室"]
        }
    ),
    (
        "明天上午10点提交季度报告",
        {
            "startTime": (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "endTime": (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0).strftime(
                "%Y-%m-%d %H:%M:%S"),
            "scheduleContent": "提交季度报告",
            "resource": []
        }
    ),
]

if __name__ == "__main__":
    parser = ScheduleParser()
    metrics = evaluate_all(parser, test_cases)
    print_full_report(metrics)
