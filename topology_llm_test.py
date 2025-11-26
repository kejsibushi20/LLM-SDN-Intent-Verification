import os
import requests
import json

# ---------- LLM CONFIG ----------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_topology_text():
    lines = [
        "Network topology summary:",
        "Host h1 | IP: 10.0.0.1 | Switch: s1",
        "Host h2 | IP: 10.0.0.2 | Switch: s1",
        "Host h3 | IP: 10.0.0.3 | Switch: s1",
    ]
    return "\n".join(lines)


def call_groq_llm(topology_text, user_intent):
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set.")
        print('Please run: export GROQ_API_KEY="your_real_key_here"')
        return None

    print(">>> Calling Groq LLM...")
    headers = {"Authorization": "Bearer %s" % GROQ_API_KEY}

    prompt = """
You are an SDN rule generator.

Here is the network topology:
%s

User intent: "%s"

Generate an SDN configuration in JSON with:
- switch_id
- match_src_ip
- match_dst_ip
- action (drop or allow)
Only output the JSON, nothing else.
""" % (topology_text, user_intent)

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload)
    print(">>> HTTP status:", resp.status_code)

    data = resp.json()
    print("\n=== Raw LLM Response ===")
    print(data)

    # Extract the text content from the first choice
    answer = data["choices"][0]["message"]["content"]
    return answer


def main():
    print(">>> Starting topology + LLM test...")
    topo_str = get_topology_text()
    print("\n" + topo_str)

    user_intent = "Block traffic from h1 to h2"
    print("\nUser Intent:", user_intent)

    llm_output = call_groq_llm(topo_str, user_intent)
    if llm_output is None:
        print("No LLM output because the API key was not set.")
        return

    print("\n=== LLM Output (raw) ===")
    print(llm_output)

    try:
        cleaned = llm_output.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "")
        rule = json.loads(cleaned)

        print("\n=== Parsed JSON rule ===")
        print(rule)
        print("switch_id:", rule.get("switch_id"))
        print("src_ip:", rule.get("match_src_ip"))
        print("dst_ip:", rule.get("match_dst_ip"))
        print("action:", rule.get("action"))

    except Exception as e:
        print("\nCould not parse JSON from LLM output:")
        print(e)

    print("\n>>> Done.")
    print("=====================")


if __name__ == "__main__":
    main()
