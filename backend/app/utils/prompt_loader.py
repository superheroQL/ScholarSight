import sys
import os
# 将项目根目录加入 sys.path，确保 backend 等模块可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config_handler import prompts_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


def load_system_prompts():
    try:
        system_prompt_path = get_abs_path(prompts_conf["main_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_system_prompts]在yaml配置项中没有main_prompt配置项")
        raise e 

    try:
        return open(system_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_system_prompts]解析系统提示词出错，{str(e)}")
        raise e


def load_rag_prompts():
    try:
        rag_prompt_path = get_abs_path(prompts_conf["rag_summary_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_rag_prompts]在yaml配置项中没有rag_summary_prompt配置项")
        raise e

    try:
        return open(rag_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_rag_prompts]解析RAG总结提示词出错，{str(e)}")
        raise e


def load_pdf_prompts():
    try:
        pdf_prompt_path = get_abs_path(prompts_conf["pdf_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_pdf_prompts]在yaml配置项中没有pdf_prompt配置项")
        raise e

    try:
        return open(pdf_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_pdf_prompts]解析PDF提取提示词出错，{str(e)}")
        raise e


def load_pdf_metadata_prompts():
    try:
        pdf_prompt_path = get_abs_path(prompts_conf["pdf_metadata_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_pdf_prompts]在yaml配置项中没有pdf_metadata_prompt配置项")
        raise e

    try:
        return open(pdf_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_pdf_prompts]解析PDF提取提示词出错，{str(e)}")
        raise e


def load_paper_analysis_prompts():
    try:
        prompt_path = get_abs_path(prompts_conf["paper_analysis_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_paper_analysis_prompts]在yaml配置项中没有paper_analysis_prompt配置项")
        raise e

    try:
        return open(prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_paper_analysis_prompts]解析论文分析提示词出错，{str(e)}")
        raise e


def load_review_prompts():
    try:
        prompt_path = get_abs_path(prompts_conf["review_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_review_prompts]在yaml配置项中没有review_prompt配置项")
        raise e

    try:
        return open(prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_review_prompts]解析文献综述提示词出错，{str(e)}")
        raise e


def load_multi_paper_analysis_prompts():
    try:
        prompt_path = get_abs_path(prompts_conf["multi_paper_analysis_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_multi_paper_analysis_prompts]在yaml配置项中没有multi_paper_analysis_prompt配置项")
        raise e

    try:
        return open(prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_multi_paper_analysis_prompts]解析多论文分析提示词出错，{str(e)}")
        raise e


def load_report_prompts():
    try:
        report_prompt_path = get_abs_path(prompts_conf["report_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_report_prompts]在yaml配置项中没有report_prompt配置项")
        raise e

    try:
        return open(report_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_report_prompts]解析报告生成提示词出错，{str(e)}")
        raise e


def load_reorder_prompts():
    try:
        reorder_prompt_path = get_abs_path(prompts_conf["reorder_prompt"])
    except KeyError as e:
        logger.error(f"[❌ load_reorder_prompts]在yaml配置项中没有reorder_prompt配置项")
        raise e

    try:
        return open(reorder_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[❌ load_reorder_prompts]解析重新排序提示词出错，{str(e)}")
        raise e


if __name__ == '__main__':
    print(load_reorder_prompts())

