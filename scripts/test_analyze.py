#!/usr/bin/env python3
"""
测试ERNIE相关性分析工具
只分析前3条数据，验证功能是否正常
"""

from analyze_relevance import QianfanAPI

def test_api():
    """测试API调用"""
    api_key = "bce-v3/ALTAK-3t7fjMhp5Bx2KUqiEj4SF/8b44c3fc85f248a4b9b1c7532d0d2fc3f91150bc"
    api = QianfanAPI(api_key)

    print("="*60)
    print("测试 ERNIE 相关性分析 API")
    print("="*60)

    # 测试用例
    test_cases = [
        {
            "title": "Ernie 5.0 released, achieving frontier performance across multimodal domains",
            "content": "Anyone tested it? I did some own tests, it's very slow and not as good as they make it out to be."
        },
        {
            "title": "Are there any benchmarks for best quantized model within a certain VRAM footprint?",
            "content": "For what its worth, https://maxkruse.github.io/vitepress-llm-recommends/ (and the sourcecode for it) are personal findings about that - but not at all compehensive."
        },
        {
            "title": "BREAKING: ERNIE 5.0 from Baidu is out and it's legitimately impressive",
            "content": "They didn't iterate, they reimagined. True omni-modal capabilities, with text, images, audio, and video running through one unified system"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试用例 {i}/{len(test_cases)}")
        print(f"{'='*60}")
        print(f"标题: {case['title'][:80]}...")
        print(f"内容: {case['content'][:80]}...")
        print("\n分析中...")

        try:
            result = api.analyze_relevance(case['title'], case['content'])

            print(f"\n结果:")
            print(f"  是否相关: {'✓ 是' if result['is_related'] else '✗ 否'}")
            print(f"  置信度: {result['confidence']:.2f}")
            print(f"  理由: {result['reason']}")

        except Exception as e:
            print(f"\n❌ 错误: {e}")

    print(f"\n{'='*60}")
    print("测试完成！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    test_api()
