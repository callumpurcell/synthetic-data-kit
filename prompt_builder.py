import os
import json

from utils import get_question_for_file


def generate_prompt(mode, page_text, q_prompt, code_prompt, args, base=None):
    if mode == 'question':
        return q_prompt.format(text=page_text)

    # code mode: load & validate question JSON
    q_path = get_question_for_file(base, args)
    if not os.path.exists(q_path):
        raise FileNotFoundError(f"Question JSON not found: {q_path}")

    with open(q_path, 'r', encoding='utf-8') as f:
        try:
            q_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {q_path}: {e}")

    question = q_data.get('Question')
    if not question:
        raise ValueError(f"Missing 'Question' field in {q_path}")

    return code_prompt.format(text=page_text, question=question)