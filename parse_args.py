import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Process input file(s) for code or question generation."
    )
    parser.add_argument(
        '--mode',
        choices=['code', 'question'],
        required=True,
        help='Select "code" for code generation or "question" for question generation.'
    )
    parser.add_argument(
        '--config',
        default='configs/config_ey.yaml',
        help='Path to the YAML configuration file.'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--input-dir',
        help='Directory containing input text files.'
    )
    group.add_argument(
        '--input-file',
        help='Single input text file to process.'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Directory where output JSON files will be saved.'
    )
    # For code mode: allow either single question file or directory of question files
    qgroup = parser.add_argument_group('code mode question input')
    qgroup.add_argument(
        '--question-dir',
        help='Directory containing question JSON files per input (use with input-dir).'
    )
    qgroup.add_argument(
        '--question-file',
        help='Single question JSON file (use with input-file).'
    )
    return parser.parse_args()