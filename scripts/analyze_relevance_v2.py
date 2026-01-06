#!/usr/bin/env python3
"""
ERNIE相关性和价值分析工具（V2）
1. 判断讨论是否与ERNIE相关
2. 如果相关，进一步判断是否有价值
"""

import os
import csv
import json
import time
import requests
from datetime import datetime, date
from typing import Dict, List, Optional
from pathlib import Path


class QianfanAPI:
    """百度千帆API客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://qianfan.baidubce.com/v2/chat/completions"
        self.model = "ernie-4.5-8k-preview"  # 使用ERNIE 4.5预览版

    def _call_api_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Dict:
        """调用API并实现重试机制"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Appbuilder-Authorization": self.api_key
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        delay = initial_delay
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    if data.get("error_code") or data.get("error_msg"):
                        error_msg = data.get("error_msg") or f"错误码: {data.get('error_code')}"
                        raise Exception(f"千帆API错误: {error_msg}")

                    if not data.get("choices") or not data["choices"][0].get("message"):
                        raise Exception("API返回数据格式异常")

                    return data

                elif response.status_code in [429, 500, 502, 503, 504]:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    if attempt < max_retries:
                        print(f"  ⚠️  API请求失败 ({attempt + 1}/{max_retries + 1}): {last_error}")
                        print(f"  ⏳ 等待 {delay:.1f} 秒后重试...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                    raise Exception(last_error)

                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                if attempt < max_retries:
                    print(f"  ⚠️  {last_error} ({attempt + 1}/{max_retries + 1})")
                    print(f"  ⏳ 等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise Exception(last_error)

            except requests.exceptions.RequestException as e:
                last_error = f"网络错误: {str(e)}"
                if attempt < max_retries:
                    print(f"  ⚠️  {last_error} ({attempt + 1}/{max_retries + 1})")
                    print(f"  ⏳ 等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise Exception(last_error)

        raise Exception(f"达到最大重试次数，最后错误: {last_error}")

    def analyze_relevance(self, title: str, content: str) -> Dict:
        """分析讨论内容是否与ERNIE相关"""
        system_prompt = """你是一位AI模型分析专家，擅长判断内容是否与ERNIE文心大模型相关。

## 判断标准

### 明确相关（confidence >= 0.8）
- 直接提到"ERNIE"、"文心"、"文心一言"、"Ernie"等关键词
- 讨论ERNIE模型的性能、能力、技术细节
- 与ERNIE的对比评测
- ERNIE的应用案例、使用体验
- 百度发布的ERNIE相关公告、更新

### 可能相关（confidence 0.4-0.7）
- 提到"百度"的AI模型（但未明确指出ERNIE）
- 讨论中国AI大模型发展（可能涉及ERNIE）

### 不相关（confidence < 0.4）
- 仅提到百度但与AI无关
- 讨论其他公司的AI模型且未提及ERNIE
- 有ERNIE关键词但指其他同名对象

## 输出要求

严格按照以下JSON格式输出：

{
  "is_related": true或false,
  "confidence": 0.0到1.0之间的数字,
  "reason": "简短的判断理由（中文，不超过50字）"
}"""

        user_prompt = f"""请判断以下讨论是否与ERNIE文心大模型相关：

标题：{title if title and title.strip() else "无标题"}

内容：{content if content and content.strip() else "无内容"}

请严格按照JSON格式输出分析结果。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self._call_api_with_retry(messages)
            content_str = response["choices"][0]["message"]["content"]

            # 处理可能包含markdown代码块的响应
            if content_str.strip().startswith("```"):
                lines = content_str.strip().split('\n')
                json_str = '\n'.join(lines[1:-1])
            else:
                json_str = content_str

            result = json.loads(json_str)

            if not all(key in result for key in ["is_related", "confidence", "reason"]):
                raise ValueError("API返回的JSON缺少必需字段")

            return {
                "is_related": bool(result["is_related"]),
                "confidence": float(result["confidence"]),
                "reason": str(result["reason"])
            }

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON解析失败: {e}")
            return {
                "is_related": False,
                "confidence": 0.0,
                "reason": "API返回格式错误，无法解析"
            }
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            return {
                "is_related": False,
                "confidence": 0.0,
                "reason": f"分析出错: {str(e)}"
            }

    def analyze_value(self, title: str, content: str) -> Dict:
        """分析ERNIE相关内容是否有价值"""
        system_prompt = """你是一位内容价值分析专家，擅长判断关于ERNIE文心大模型的讨论是否有实质性价值。

## 有价值的内容

### 优点反馈（value_type: "优点"）
- 用户体验到的具体优势（如速度快、理解准确等）
- 与其他模型对比后发现的优势
- 具体应用场景中的良好表现

### 缺点反馈（value_type: "缺点"）
- 用户遇到的具体问题或不足
- 性能、准确度等方面的不足
- 与其他模型对比后的劣势

### 问题报告（value_type: "问题"）
- 使用过程中遇到的具体技术问题
- Bug报告或异常行为
- 功能限制或缺失

### 集成需求（value_type: "需求"）
- 希望与其他工具/平台集成的需求
- 功能改进建议
- 新功能请求

### 深度讨论（value_type: "深度讨论"）
- 技术细节分析
- 架构或原理探讨
- 应用案例分享

## 无价值的内容

- **官方通稿**：仅转发官方新闻，无个人观点或体验
- **情绪宣泄**：仅有情绪表达，无具体内容
- **简单转述**：仅转述他人观点，无新信息
- **无关讨论**：虽提及ERNIE但实际讨论其他话题
- **spam/广告**：营销性质内容

## 输出要求

严格按照以下JSON格式输出：

{
  "has_value": true或false,
  "value_type": "优点/缺点/问题/需求/深度讨论/无价值",
  "value_reason": "简短说明（中文，不超过50字）"
}"""

        user_prompt = f"""请判断以下关于ERNIE的讨论是否有价值：

标题：{title if title and title.strip() else "无标题"}

内容：{content if content and content.strip() else "无内容"}

请严格按照JSON格式输出分析结果。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self._call_api_with_retry(messages)
            content_str = response["choices"][0]["message"]["content"]

            if content_str.strip().startswith("```"):
                lines = content_str.strip().split('\n')
                json_str = '\n'.join(lines[1:-1])
            else:
                json_str = content_str

            result = json.loads(json_str)

            if not all(key in result for key in ["has_value", "value_type", "value_reason"]):
                raise ValueError("API返回的JSON缺少必需字段")

            return {
                "has_value": bool(result["has_value"]),
                "value_type": str(result["value_type"]),
                "value_reason": str(result["value_reason"])
            }

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON解析失败: {e}")
            return {
                "has_value": False,
                "value_type": "无价值",
                "value_reason": "API返回格式错误，无法解析"
            }
        except Exception as e:
            print(f"  ❌ 价值分析失败: {e}")
            return {
                "has_value": False,
                "value_type": "无价值",
                "value_reason": f"分析出错: {str(e)}"
            }


class RelevanceAnalyzer:
    """ERNIE相关性和价值分析器"""

    def __init__(self, api_key: str, input_csv: str, output_csv: Optional[str] = None):
        self.api = QianfanAPI(api_key)
        self.input_csv = input_csv

        if output_csv is None:
            input_path = Path(input_csv)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_csv = input_path.parent / f"{input_path.stem}_analyzed_v2_{timestamp}.csv"

        self.output_csv = output_csv
        self.progress_file = Path(output_csv).with_suffix('.progress.json')

    def load_progress(self) -> Dict:
        """加载处理进度"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"processed_ids": [], "last_index": -1}

    def save_progress(self, progress: Dict):
        """保存处理进度"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def analyze_csv(self, batch_size: int = 10, start_date: Optional[date] = None):
        """分析CSV文件中的所有讨论"""
        print(f"\n{'='*60}")
        print(f"ERNIE相关性和价值分析工具 V2")
        print(f"{'='*60}")
        print(f"输入文件: {self.input_csv}")
        print(f"输出文件: {self.output_csv}")
        print(f"进度文件: {self.progress_file}")
        if start_date:
            print(f"日期过滤: 只分析 {start_date} 及之后的数据")
        print(f"{'='*60}\n")

        # 读取CSV
        print("📖 正在读取CSV文件...")
        with open(self.input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        total_rows = len(rows)
        print(f"✓ 共读取 {total_rows} 条讨论\n")

        # 加载进度
        progress = self.load_progress()
        processed_ids = set(progress.get("processed_ids", []))
        start_index = progress.get("last_index", -1) + 1

        if start_index > 0:
            print(f"📌 检测到上次进度，从第 {start_index + 1} 条继续处理\n")

        # 添加新字段
        new_fieldnames = list(fieldnames) + [
            'is_ernie_related', 'relevance_score', 'relevance_reason',
            'has_value', 'value_type', 'value_reason'
        ]

        # 准备输出文件
        output_file = open(self.output_csv, 'w', encoding='utf-8-sig', newline='')
        writer = csv.DictWriter(output_file, fieldnames=new_fieldnames)
        writer.writeheader()

        # 如果有已处理的数据，先写入
        if processed_ids:
            print(f"📝 写入已处理的 {len(processed_ids)} 条记录...")
            for i, row in enumerate(rows):
                row_id = row.get('db_id', str(i))
                if row_id in processed_ids:
                    writer.writerow(row)

        # 处理剩余数据
        success_count = 0
        error_count = 0
        related_count = 0
        valuable_count = 0
        skipped_count = 0

        start_time = time.time()

        print(f"\n🚀 开始分析...\n")

        for i in range(start_index, total_rows):
            row = rows[i]
            row_id = row.get('db_id', str(i))

            # 跳过已处理的
            if row_id in processed_ids:
                continue

            # 日期过滤
            if start_date:
                created_at_str = row.get('created_at', '')
                if created_at_str:
                    try:
                        created_date = datetime.strptime(created_at_str.split()[0], '%Y-%m-%d').date()
                        if created_date < start_date:
                            row['is_ernie_related'] = 'SKIPPED'
                            row['relevance_score'] = ''
                            row['relevance_reason'] = f'日期早于{start_date}'
                            row['has_value'] = ''
                            row['value_type'] = ''
                            row['value_reason'] = ''
                            writer.writerow(row)
                            skipped_count += 1
                            continue
                    except (ValueError, IndexError):
                        pass

            title = row.get('title', '')
            content = row.get('content', '')

            print(f"[{i + 1}/{total_rows}] 分析中...", end=' ')

            try:
                # 第一步：分析相关性
                result = self.api.analyze_relevance(title, content)

                row['is_ernie_related'] = 'YES' if result['is_related'] else 'NO'
                row['relevance_score'] = f"{result['confidence']:.2f}"
                row['relevance_reason'] = result['reason']

                # 第二步：如果相关，分析价值
                if result['is_related']:
                    related_count += 1
                    print(f"✓ 相关 (置信度: {result['confidence']:.2f})", end=' ')

                    value_result = self.api.analyze_value(title, content)
                    row['has_value'] = 'YES' if value_result['has_value'] else 'NO'
                    row['value_type'] = value_result['value_type']
                    row['value_reason'] = value_result['value_reason']

                    if value_result['has_value']:
                        valuable_count += 1
                        print(f"→ 有价值 [{value_result['value_type']}]")
                    else:
                        print(f"→ 无价值 [{value_result['value_type']}]")
                else:
                    row['has_value'] = ''
                    row['value_type'] = ''
                    row['value_reason'] = ''
                    print(f"○ 不相关 (置信度: {result['confidence']:.2f})")

                writer.writerow(row)
                output_file.flush()

                success_count += 1
                processed_ids.add(row_id)

                # 定期保存进度
                if (i + 1) % batch_size == 0:
                    progress = {
                        "processed_ids": list(processed_ids),
                        "last_index": i
                    }
                    self.save_progress(progress)

                    elapsed = time.time() - start_time
                    avg_time = elapsed / success_count if success_count > 0 else 0
                    remaining = (total_rows - i - 1) * avg_time

                    print(f"\n  💾 进度已保存 | 已处理: {i + 1}/{total_rows} | "
                          f"相关: {related_count} | 有价值: {valuable_count} | "
                          f"预计剩余: {remaining/60:.1f}分钟\n")

                # API限流控制
                time.sleep(0.5)

            except Exception as e:
                error_count += 1
                print(f"❌ 错误: {e}")

                row['is_ernie_related'] = 'ERROR'
                row['relevance_score'] = '0.00'
                row['relevance_reason'] = f"处理失败: {str(e)}"
                row['has_value'] = ''
                row['value_type'] = ''
                row['value_reason'] = ''
                writer.writerow(row)
                output_file.flush()

                processed_ids.add(row_id)

        output_file.close()

        # 完成，删除进度文件
        if self.progress_file.exists():
            self.progress_file.unlink()

        # 输出统计
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"✅ 分析完成！")
        print(f"{'='*60}")
        print(f"总计: {total_rows} 条")
        if skipped_count > 0:
            print(f"已跳过（日期过滤）: {skipped_count} 条")
        print(f"已分析: {success_count} 条")
        print(f"失败: {error_count} 条")
        if success_count > 0:
            print(f"ERNIE相关: {related_count} 条 ({related_count/success_count*100:.1f}%)")
        if related_count > 0:
            print(f"有价值内容: {valuable_count} 条 ({valuable_count/related_count*100:.1f}% of related)")
        print(f"耗时: {elapsed/60:.1f} 分钟")
        print(f"\n结果已保存至: {self.output_csv}")
        print(f"{'='*60}\n")


def main():
    """主函数"""
    api_key = "bce-v3/ALTAK-3t7fjMhp5Bx2KUqiEj4SF/8b44c3fc85f248a4b9b1c7532d0d2fc3f91150bc"
    input_csv = "data/exports/discussions_ERNIE_20251117_184548.csv"

    if not os.path.exists(input_csv):
        print(f"❌ 错误: 找不到输入文件 {input_csv}")
        return

    analyzer = RelevanceAnalyzer(
        api_key=api_key,
        input_csv=input_csv
    )

    # 设置起始日期：11月1日
    filter_start_date = date(2025, 11, 1)

    try:
        analyzer.analyze_csv(batch_size=10, start_date=filter_start_date)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，进度已保存，下次运行将继续处理")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        raise


if __name__ == "__main__":
    main()
