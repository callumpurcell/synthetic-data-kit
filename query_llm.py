import json, yaml
from openai import OpenAI

# Load the YAML file
with open("configs/config_ey.yaml", "r") as f:
    data = yaml.safe_load(f)

# Grab your specific prompt
q_prompt = data["prompts"]["q_generation"]
system_prompt = data["prompts"]["system_prompt"]

# Read text file
with open("data/output/initial_038.txt", "r", encoding="utf-8") as f:
    page_text = f.read()

# Fill in the {text} slot
q_prompt = q_prompt.format(text=page_text)

# Configure client to talk to your local vLLM server
openai_api_key = "EMPTY"
openai_api_base = "http://localhost:8000/v1"
client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)

# Send the retrieved prompt
response = client.chat.completions.create(
    model="Qwen/Qwen3-0.6B",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": q_prompt}
    ],
    temperature=0.7,
    top_p=0.95,
    max_tokens=4096
)

# ——— extract
msg    = response.choices[0].message
output    = msg.content.strip()            # the JSON question+answer+reasoning
reasoning = getattr(msg, "reasoning_content", None)  # the chain‐of‐thought text

# ——— save the structured output
with open("data/qwen_gen/output_q.json", "w", encoding="utf-8") as f:
    # if it's already JSON text, just dump it:
    try:
        parsed = json.loads(output)
        json.dump(parsed, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        f.write(output)  # fallback to raw write

# ——— save the raw CoT reasoning (optional)
if reasoning:
    with open("data/qwen_gen/output_reasoning.txt", "w", encoding="utf-8") as f:
        f.write(reasoning)
