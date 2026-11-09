#!/usr/bin/env python3
"""
OCR工具链集成 - 作为AI视觉服务的降级备选方案

功能：
1. 提供统一的OCR接口（支持多个OCR引擎）
2. 自动故障转移（主服务失败时切换到备选）
3. 图片信息提取
4. 结果质量评估
"""

import os
import sys
import json
import base64
from datetime import datetime

# 支持的OCR引擎
OCR_ENGINES = {
    "tesseract": {
        "name": "Tesseract OCR",
        "available": False,
        "priority": 2  # 降级优先级
    },
    "paddleocr": {
        "name": "PaddleOCR",
        "available": False,
        "priority": 1
    },
    "easyocr": {
        "name": "EasyOCR",
        "available": False,
        "priority": 3
    }
}


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def detect_engines():
    """检测可用的OCR引擎"""
    log("检测OCR引擎...")

    # 检查 Tesseract
    try:
        import pytesseract
        from PIL import Image
        OCR_ENGINES["tesseract"]["available"] = True
        log("✓ Tesseract OCR 可用")
    except ImportError:
        log("✗ Tesseract OCR 不可用（缺少依赖）")
    except Exception as e:
        log(f"✗ Tesseract OCR 不可用: {e}")

    # 检查 PaddleOCR
    try:
        from paddleocr import PaddleOCR
        OCR_ENGINES["paddleocr"]["available"] = True
        log("✓ PaddleOCR 可用")
    except ImportError:
        log("✗ PaddleOCR 不可用（缺少依赖）")
    except Exception as e:
        log(f"✗ PaddleOCR 不可用: {e}")

    # 检查 EasyOCR
    try:
        import easyocr
        OCR_ENGINES["easyocr"]["available"] = True
        log("✓ EasyOCR 可用")
    except ImportError:
        log("✗ EasyOCR 不可用（缺少依赖）")
    except Exception as e:
        log(f"✗ EasyOCR 不可用: {e}")

    # 按优先级排序
    available = [(k, v) for k, v in OCR_ENGINES.items() if v["available"]]
    available.sort(key=lambda x: x[1]["priority"])
    return available


def ocr_with_tesseract(image_path, lang='chi_sim+eng'):
    """使用 Tesseract 进行OCR"""
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=lang)

        return {
            "engine": "tesseract",
            "text": text.strip(),
            "confidence": 0.8  # Tesseract 不直接提供置信度，给一个默认值
        }
    except Exception as e:
        log(f"Tesseract OCR 失败: {e}", "ERROR")
        return None


def ocr_with_paddleocr(image_path):
    """使用 PaddleOCR 进行OCR"""
    try:
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        result = ocr.ocr(image_path, cls=True)

        # 提取文本
        texts = []
        total_confidence = 0
        count = 0

        for line in result:
            for item in line:
                text = item[1][0]
                confidence = item[1][1]
                texts.append(text)
                total_confidence += confidence
                count += 1

        full_text = "\n".join(texts)
        avg_confidence = total_confidence / count if count > 0 else 0

        return {
            "engine": "paddleocr",
            "text": full_text.strip(),
            "confidence": avg_confidence,
            "details": result
        }
    except Exception as e:
        log(f"PaddleOCR 失败: {e}", "ERROR")
        return None


def ocr_with_easyocr(image_path):
    """使用 EasyOCR 进行OCR"""
    try:
        import easyocr

        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        results = reader.readtext(image_path)

        # 提取文本
        texts = []
        total_confidence = 0
        count = 0

        for (bbox, text, confidence) in results:
            texts.append(text)
            total_confidence += confidence
            count += 1

        full_text = "\n".join(texts)
        avg_confidence = total_confidence / count if count > 0 else 0

        return {
            "engine": "easyocr",
            "text": full_text.strip(),
            "confidence": avg_confidence,
            "details": results
        }
    except Exception as e:
        log(f"EasyOCR 失败: {e}", "ERROR")
        return None


def extract_text(image_path, preferred_engine=None, min_confidence=0.6):
    """
    从图片中提取文本（支持自动故障转移）

    Args:
        image_path: 图片文件路径
        preferred_engine: 首选引擎（如果不指定，使用优先级最高的）
        min_confidence: 最小置信度阈值

    Returns:
        {
            "success": bool,
            "engine": str,
            "text": str,
            "confidence": float,
            "fallback_used": bool
        }
    """
    # 检测可用引擎
    available_engines = detect_engines()

    if not available_engines:
        log("没有可用的OCR引擎", "ERROR")
        return {
            "success": False,
            "engine": None,
            "text": "",
            "confidence": 0,
            "fallback_used": False,
            "error": "没有可用的OCR引擎"
        }

    # 确定使用的引擎列表
    if preferred_engine and preferred_engine in [e[0] for e in available_engines]:
        # 如果指定了首选引擎，优先使用
        engines = [e for e in available_engines if e[0] == preferred_engine]
        engines.extend([e for e in available_engines if e[0] != preferred_engine])
    else:
        # 使用默认优先级
        engines = available_engines

    log(f"可用引擎: {[e[0] for e in engines]}")

    # 尝试每个引擎
    for engine_name, engine_info in engines:
        log(f"尝试使用 {engine_info['name']}...")

        result = None
        if engine_name == "tesseract":
            result = ocr_with_tesseract(image_path)
        elif engine_name == "paddleocr":
            result = ocr_with_paddleocr(image_path)
        elif engine_name == "easyocr":
            result = ocr_with_easyocr(image_path)

        if result and result["confidence"] >= min_confidence:
            log(f"✓ 成功使用 {engine_info['name']} (置信度: {result['confidence']:.2f})")
            return {
                "success": True,
                "engine": engine_name,
                "text": result["text"],
                "confidence": result["confidence"],
                "fallback_used": (engine_name != engines[0][0]),
                "details": result.get("details", None)
            }
        elif result:
            log(f"✗ {engine_info['name']} 置信度不足: {result['confidence']:.2f} < {min_confidence}")
        else:
            log(f"✗ {engine_info['name']} 执行失败")

    # 所有引擎都失败
    log("所有OCR引擎都失败", "ERROR")
    return {
        "success": False,
        "engine": None,
        "text": "",
        "confidence": 0,
        "fallback_used": False,
        "error": "所有OCR引擎都失败"
    }


def main():
    """主函数 - 测试OCR功能"""
    if len(sys.argv) < 2:
        print("用法: python ocr_fallback.py <图片路径> [首选引擎]")
        print("\n可用引擎:")
        for name, info in OCR_ENGINES.items():
            status = "✓" if info["available"] else "✗"
            print(f"  {status} {name} (优先级: {info['priority']})")
        return 1

    image_path = sys.argv[1]
    preferred_engine = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(image_path):
        log(f"图片不存在: {image_path}", "ERROR")
        return 1

    log("=" * 50)
    log("OCR工具链集成测试")
    log(f"图片: {image_path}")
    log("=" * 50)

    # 执行OCR
    result = extract_text(image_path, preferred_engine=preferred_engine)

    # 输出结果
    log("=" * 50)
    if result["success"]:
        log(f"✓ OCR 成功!")
        log(f"使用的引擎: {result['engine']}")
        log(f"是否使用了故障转移: {'是' if result['fallback_used'] else '否'}")
        log(f"置信度: {result['confidence']:.2f}")
        log("-" * 50)
        log("提取的文本:")
        print(result["text"])
        log("-" * 50)

        # 保存结果
        output_path = image_path.rsplit('.', 1)[0] + "_ocr.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        log(f"结果已保存: {output_path}")
    else:
        log("✗ OCR 失败")
        log(f"错误: {result.get('error', '未知错误')}")
    log("=" * 50)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
