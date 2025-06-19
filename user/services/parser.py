import re
from calendar import monthrange

import jiagu
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import requests
from dateutil.parser import parse as date_parse
from dateutil.relativedelta import relativedelta


class ScheduleParser:

    def __init__(self):
        jiagu.init()

        self.ACTION_VERBS = [
            '准备', '完成', '提交', '讨论', '进行', '检查', '安排', '参加', '召开',
            '处理', '审核', '编写', '修改', '审批', '汇报', '评估', '测试', '部署',
            '开发', '设计', '培训', '学习', '研究', '分析', '采购', '签约', '谈判',
            '接待', '拜访', '演示', '发布', '维护', '优化', '调试', '安装', '配置',
            '跟进', '协调', '沟通', '确认', '批准', '签署', '归档', '备份', '恢复',
            '翻译', '校对', '排版', '印刷', '配送', '验收', '结算', '报销', '统计',
            '调查', '考核', '面试', '招聘', '离职', '入职', '转正', '晋升', '调岗',
            '授课', '备课', '听课', '评课', '说课', '试讲', '辅导', '答疑', '批改', '阅卷',
            '监考', '出题', '命题', '组卷', '评分', '录分', '讲解', '演示', '示范', '指导',
            '预习', '复习', '背诵', '默写', '朗读', '阅读', '做题', '练习', '实验', '实践',
            '研讨', '答辩', '汇报', '展示', '参赛', '考证', '考研', '留学', '交流', '访学',
            '考勤', '查寝', '值日', '评比', '表彰', '处分', '约谈', '家访', '建档', '评优',
            '保研', '评教', '选课', '调课', '排课', '代课', '补考', '重修', '休学', '复学',
            '升旗', '集会', '排练', '演出', '竞赛', '义诊', '义卖', '捐赠', '支教', '调研',
            '实习', '实训', '见习', '军训', '拉练', '体检', '接种', '防疫', '疏散', '演练'
        ]

        self.RESOURCE_DB = {
            'location': ['会议室', '会客室', '洽谈室', '咖啡厅', '餐厅', '实验室',
                         '车间', '工位', 'A区', 'B区', 'C区', '总部', '分部', '基地',
                         '教室', '阶梯教室', '多媒体教室', '实验室', '计算机房', '语音室', '琴房', '画室',
                         '舞蹈房', '体育馆', '操场', '篮球场', '图书馆', '阅览室', '自习室', '报告厅',
                         '礼堂', '校医院', '食堂', '宿舍', '辅导员办公室', '教务处', '学生处', '招生办'
                         ],
            'device': ['电脑', '笔记本', '台式机', '平板', '投影仪', '显示屏', '服务器',
                       '手机', '电话', '打印机', '复印机', '扫描仪', '传真机', '路由器',
                       '黑板', '白板', '投影幕', '讲台', '课桌椅', '实验器材', '显微镜', '天平',
                       '钢琴', '画架', '体育器材', '教学电脑', '电钢琴', '舞蹈把杆', '校园卡', '一卡通',
                       '广播系统', '监控设备', '电子班牌', '班班通'
                       ],
            'material': ['资料', '文件', '文档', '合同', '协议', '标书', '样品', '原型',
                         'U盘', '硬盘', '设计稿', '图纸', '报告', '报表', '统计数据',
                         '教材', '教参', '教案', '课件', '学案', '试卷', '答题卡', '成绩单', '作业本',
                         '实验报告', '毕业论文', '学位论文', '教学计划', '课表', '考勤表', '学生档案',
                         '录取通知书', '毕业证书', '奖学金证书', '竞赛奖状'
                         ],
        }

        self.TIME_KEYWORDS = {
            'morning': ['早上', '上午', '早晨'],
            'noon': ['中午', '午休'],
            'afternoon': ['下午', '午后'],
            'evening': ['晚上', '傍晚', '黄昏']
        }

        # 优先级关键词
        self.PRIORITY_KEYWORDS = {
            3: ['紧急', '立刻', '马上', '尽快', '务必', '必须'],
            1: ['有空', '抽空', '不着急', '闲暇时', '非紧急'],
            2: []
        }

        self.CHINESE_NUM_MAP = {
            '零': 0, '〇': 0, '一': 1, '两': 2,'二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
            '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
            '二十一': 21, '二十二': 22, '二十三': 23
        }

    def parse(self, text: str, executor: str) -> Dict:
        if not text.strip():
            raise ValueError("输入文本不能为空")

        original_text = text
        clean_text = self._preprocess_text(text)

        time_range = self._parse_time_range(clean_text)
        if time_range:
            start_time, end_time = time_range
        else:
            start_time, end_time = self._parse_relative_time(clean_text)

        content = self._extract_action_content(clean_text)

        resources = self._find_resources(clean_text)
        priority = self._detect_priority(clean_text)

        return {
            "executor": executor,
            "scheduleContent": content[:256],
            "startTime": start_time,
            "endTime": end_time,
            "resource": ",".join(resources),
            "priority": priority
        }

    def _preprocess_text(self, text: str) -> str:
        text = re.sub(r'[到至~-]', '-', text)
        return re.sub(r'[^\u4e00-\u9fa5\d\s:：\-]', '', text).strip()

    def _parse_time_range(self, text: str) -> Optional[Tuple[str, str]]:
        pattern = r'(上午|下午|中午|晚上)?\s*([零〇一二两三四五六七八九十\d]{1,3})点(半|[零〇一二三四五六七八九十\d]{0,3})?[分]?\s*[-到至~]+\s*([零〇一二两三四五六七八九十\d]{1,3})点(半|[零〇一二三四五六七八九十\d]{0,3})?[分]?'
        match = re.search(pattern, text)
        if match:
            period, sh_str, sm_str, eh_str, em_str = match.groups()

            def cn(num):  # 兼容汉字与数字
                if not num:
                    return 0
                if num.isdigit():
                    return int(num)
                return self._chinese_to_arabic(num)

            start_h = cn(sh_str)
            start_m = 30 if sm_str == '半' else cn(sm_str)
            end_h = cn(eh_str)
            end_m = 30 if em_str == '半' else cn(em_str)

            if period in ['下午', '晚上'] and start_h < 12:
                start_h += 12
                end_h += 12 if end_h < 12 else 0
            elif period == '中午':
                if start_h < 11:
                    start_h += 12
                if end_h < 11:
                    end_h += 12

            base_date = self._get_base_date(text)

            start_time = base_date.replace(hour=start_h, minute=start_m, second=0)
            end_time = base_date.replace(hour=end_h, minute=end_m, second=0)

            if end_time <= start_time:
                end_time += timedelta(days=1)

            return (
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S")
            )
        return None

    def _get_base_date(self, text: str) -> datetime:
        now = datetime.now()

        if '今天' in text or '今日' in text or '今' in text: return now
        if '明天' in text or '明日' in text or '明' in text: return now + timedelta(days=1)
        if '后天' in text: return now + timedelta(days=2)
        if '大后天' in text: return now + timedelta(days=3)

        if '下下周' in text or '下下个星期' in text:
            base_date = now + timedelta(days=7)
            if match := re.search(r'下下周([一二三四五六七日天])', text):
                weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
                target_weekday = weekday_map[match.group(1)]
                current_weekday = base_date.weekday()
                delta = target_weekday - current_weekday + 7
                return base_date + timedelta(days=delta)
            return base_date

        if '下个月' in text or '下月' in text:
            next_month = now + relativedelta(months=1)

            if match := re.search(r'下(?:个)?月([零〇一二两三四五六七八九十百]+|\d{1,2})[号日]', text):
                day_str = match.group(1)
                if day_str.isdigit():
                    day = int(day_str)
                else:
                    day = self._chinese_to_arabic(day_str)

                year = next_month.year
                month = next_month.month
                max_day = monthrange(year, month)[1]
                day = min(day, max_day)
                return datetime(year, month, day)

            if match := re.search(r'下(?:个)?月(?:第([一二三四])周)?(?:周|星期|礼拜)([一二三四五六七日天])',
                                  text):
                week_num = match.group(1)
                weekday_char = match.group(2)

                weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
                target_weekday = weekday_map[weekday_char]

                first_day = next_month.replace(day=1)
                first_weekday = first_day.weekday()

                if week_num:
                    week_num_map = {'一': 1, '二': 2, '三': 3, '四': 4}
                    week_num = week_num_map[week_num]
                    delta_days = (target_weekday - first_weekday) % 7 + (week_num - 1) * 7
                else:
                    delta_days = (target_weekday - first_weekday) % 7

                return first_day + timedelta(days=delta_days)

            return next_month.replace(day=1)

        weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
        if match := re.search(r'下周(?:星期|礼拜|周)?([一二三四五六七日天])', text):
            target_day = weekday_map[match.group(1)]
            delta = target_day - now.weekday() + 7
            return now + timedelta(days=delta)

        if match := re.search(r'本(?:个)?(?:星期|礼拜|周)([一二三四五六七日天])', text):
            target_day = weekday_map[match.group(1)]
            delta = target_day - now.weekday()
            return now + timedelta(days=delta)

        if match := re.search(r'(?:星期|礼拜|周)([一二三四五六七日天])', text):
            target_day = weekday_map[match.group(1)]
            delta = target_day - now.weekday()
            return now + timedelta(days=delta)

        if match := re.search(r'本(?:个)?月(\d{1,2})[号日]', text):
            day = int(match.group(1))
            try:
                return now.replace(day=day)
            except ValueError:
                return now.replace(day=1) + timedelta(days=day - 1)

        if match := re.search(r'(\d{1,2})月(\d{1,2})[号日]', text):
            month, day = map(int, match.groups())
            year = now.year + (1 if month < now.month else 0)
            try:
                return datetime(year, month, day)
            except ValueError:
                return datetime(year, month, 1) + timedelta(days=day - 1)

        if match := re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})[号日]?', text):
            year, month, day = map(int, match.groups())
            try:
                return datetime(year, month, day)
            except ValueError:
                return datetime(year, month, 1) + timedelta(days=day - 1)

        return now

    def _parse_relative_time(self, text: str) -> Tuple[str, str]:
        base_date = self._get_base_date(text)

        hour, minute = self._parse_exact_time(text)

        duration = self._parse_duration(text) or 1.0

        start_time = base_date.replace(
            hour=hour,
            minute=minute,
            second=0
        )
        end_time = start_time + timedelta(hours=duration)

        return (
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S")
        )

    def _chinese_to_arabic(self, chinese_num: str) -> int:
        if not chinese_num:
            return 0

        if chinese_num in self.CHINESE_NUM_MAP:
            return self.CHINESE_NUM_MAP[chinese_num]

        if chinese_num == '十':
            return 10
        if chinese_num.startswith('十'):
            return 10 + self._chinese_to_arabic(chinese_num[1:])
        if chinese_num.endswith('十'):
            return self._chinese_to_arabic(chinese_num[:-1]) * 10

        total = 0
        for char in chinese_num:
            if char in self.CHINESE_NUM_MAP:
                total += self.CHINESE_NUM_MAP[char]
        return total

    def _parse_exact_time(self, text: str) -> Tuple[int, int]:
        hour, minute = 14, 0  # 默认下午2点

        if match := re.search(r'([零〇一二三四五六七八九十]+)点半', text):
            hour_str = match.group(1)
            hour = self._chinese_to_arabic(hour_str)
            minute = 30

            if '下午' in text or '晚上' in text:
                if hour < 12: hour += 12
            elif '中午' in text:
                hour = 12
            elif '凌晨' in text and hour >= 6:
                hour -= 12
            return hour, minute

        if match := re.search(r'(\d+)点(30|三十|半)(分)?', text):
            hour = int(match.group(1))
            minute = 30
            if '下午' in text or '晚上' in text:
                if hour < 12: hour += 12
            elif '中午' in text:
                hour = 12
            elif '凌晨' in text and hour >= 6:
                hour -= 12
            return hour, minute

        if match := re.search(r'([零〇一二三四五六七八九十]+)点([零〇一二三四五六七八九十]+)?分?', text):
            hour_str = match.group(1)
            minute_str = match.group(2) or ''

            hour = self._chinese_to_arabic(hour_str)
            minute = self._chinese_to_arabic(minute_str) if minute_str else 0

            if '下午' in text or '晚上' in text:
                if hour < 12:
                    hour += 12
            elif '中午' in text:
                hour = 12
            elif '凌晨' in text:
                if hour >= 6:
                    hour -= 12

            return hour, minute

        if match := re.search(r'(\d{1,2})[:点时](\d{0,2})分?', text):
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0

            if hour <= 12:
                if ('下午' in text or '晚上' in text or '晚' in text) and hour < 12:
                    hour += 12
                elif '中午' in text and hour < 12:
                    hour = 12
                elif '凌晨' in text and hour >= 6:
                    hour -= 12
        else:
            if '早上' in text or '上午' in text or '早晨' in text:
                hour = 9
            elif '中午' in text:
                hour = 12
            elif '下午' in text:
                hour = 14
            elif '晚上' in text or '傍晚' in text or '晚' in text:
                hour = 19

        return hour, minute

    def _extract_action_content(self, text: str) -> str:

        original_text = text
        time_patterns = [
            r'\d{1,2}[:点时]\d{0,2}分?\s*-\s*\d{1,2}[:点时]\d{0,2}分?',
            r'[零〇一二三四五六七八九十百\d]{1,3}[点时][:：]?[零〇一二三四五六七八九十百\d]{0,2}分?\s*[-~至到]?\s*[零〇一二三四五六七八九十百\d]{1,3}[点时][:：]?[零〇一二三四五六七八九十百\d]{0,2}分?',
            r'[零〇一二三四五六七八九十百\d]{1,3}点半',
            r'[零〇一二三四五六七八九十百\d]{1,3}[点时][:：]?[零〇一二三四五六七八九十百\d]{0,2}分?',
            r'[零〇一二三四五六七八九十百\d]{1,3}点半',
            r'上午|下午|晚上|中午',
            r'下周(?:星期|礼拜|周)?[一二三四五六七日天]',
            r'本(?:个)?(?:星期|礼拜|周)[一二三四五六七日天]',
            r'(?:星期|礼拜|周)[一二三四五六七日天]',
            r'今天|明天|后天|大后天|下周|下个月|下月|本月|本(?:个)?月|本周|本(?:个)?星期|本礼拜',
            r'预计需要\d+\s*(小时|分钟|h|min)',
            r'约?\d+\s*(小时|分钟|h|min)(?:左右|钟)?'
        ]

        for pattern in time_patterns:
            text = re.sub(pattern, '', text)

        words = jiagu.seg(original_text)
        pos_tags = jiagu.pos(words)

        for i, (word, pos) in enumerate(zip(words, pos_tags)):
            if (pos == 'v' and word in self.ACTION_VERBS) or word in self.ACTION_VERBS:
                content = []
                for w in words[i:]:
                    if w in ['，', '。', '！', '？', '；', '-']:
                        break
                    content.append(w)
                return ''.join(content)
        return self._filter_resources(text).strip()

    def _filter_resources(self, text: str) -> str:
        for words in self.RESOURCE_DB.values():
            for word in words:
                text = text.replace(word, '')
        return text.strip()

    def _find_resources(self, text: str) -> List[str]:
        found = set()
        for category, words in self.RESOURCE_DB.items():
            for word in words:
                if word in text and word not in found:
                    found.add(word)
        return list(found)

    def _parse_duration(self, text: str) -> Optional[float]:
        if match := re.search(r'(半|一|两|三|\d+)\s*(小时|分钟|h|min)', text):
            num_map = {'半': 0.5, '一': 1, '二': 2, '两': 2, '三': 3}
            num = num_map.get(match.group(1), float(match.group(1)))
            unit = match.group(2)
            return num if unit in ['小时', 'h'] else num / 60
        return None

    def _detect_priority(self, text: str) -> int:
        text_lower = text.lower()
        for level, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return level
        return 2


# 测试用例
if __name__ == "__main__":
    parser = ScheduleParser()

    test_cases = [
        ("下午3点-5点准备项目评审材料", "user001"),
        ("明天上午十点提交季度报告给财务部", "user002"),
        ("处理客户投诉，需要调取合同资料", "user003"),
        ("下周日14:30-16:00参观产品需求讨论会", "user004"),
        ("紧急！今天下班前必须完成系统测试", "user005"),
        ("检查实验室样品质量，预计需要2小时", "user006"),
        ("下个月24日下午和开发团队进行圣诞活动策划", "user007"),
        ("下个月第一周周三上午10点团队会议", "user008"),
        ("下下周一下午4点客户演示", "user009"),
        ("本月15号上午体检", "user010"),
        ("2月29号下午部门总结", "user011"),
        ("下周一下午4点客户演示", "user009"),
    ]

    for text, executor in test_cases:
        print(f"\n输入: {text}")
        result = parser.parse(text, executor)
        print("解析结果:")
        for k, v in result.items():
            print(f"  {k}: {v}")
