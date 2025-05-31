import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser(
        description="Process input file(s) for code or question generation."
    )
    parser.add_argument(
        '--mode', choices=['code', 'question'], required=True,
        help='"code" for code gen or "question" for question gen'
    )
    parser.add_argument(
        '--config', default='configs/config_ey.yaml',
        help='Path to YAML configuration file.'
    )
    parser.add_argument(
        '--input', required=True,
        help='Input file or directory of .txt files.'
    )
    parser.add_argument(
        '--question',
        help='In code mode: question JSON file or directory. In question mode: not used.'
    )
    parser.add_argument(
        '--num-questions', '-k', type=int, default=3,
        help='Number of questions to generate in question mode.'
    )
    parser.add_argument(
        '--output-dir', required=True,
        help='Directory for generated JSON outputs.'
    )
    return parser.parse_args()


def classify_paths(args):
    # classify --input
    if os.path.isdir(args.input):
        args.input_dir = args.input
        args.input_file = None
    elif os.path.isfile(args.input):
        args.input_file = args.input
        args.input_dir = None
    else:
        raise ValueError(f"Input path not found: {args.input}")

    # classify --question only in code mode
    if args.mode == 'code':
        if not args.question:
            raise ValueError("--question required in code mode")
        if os.path.isdir(args.question):
            args.question_dir = args.question
            args.question_file = None
        elif os.path.isfile(args.question):
            args.question_file = args.question
            args.question_dir = None
        else:
            raise ValueError(f"Question path not found: {args.question}")
    else:
        args.question_dir = None
        args.question_file = None

    return args