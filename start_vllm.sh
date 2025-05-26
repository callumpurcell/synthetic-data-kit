# CUDA_VISIBLE_DEVICES=7 \
# vllm serve Qwen/Qwen3-0.6B \
#   --port 8000 \
#   --chat-template /home/callumpurcell/dissertation/diss/synthetic-data-kit/qwen-chat-template.jinja \
#   --chat-template-content-format string \
#   --uvicorn-log-level info \
#   --enable-reasoning \
#   --reasoning-parser deepseek_r1

# might have to do --enable-reasoning or --reasoning-parser

CUDA_VISIBLE_DEVICES=7 \
vllm serve Qwen/Qwen3-0.6B \
  --port 8000 \
  --enable-reasoning \
  --reasoning-parser deepseek_r1

# no idea why this second one started working with the kit. 