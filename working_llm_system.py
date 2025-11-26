#!/usr/bin/env python3
"""
Real LLM-Based SDN Intent Generator - Experiment 1
Closed-loop verification of LLM-generated iptables rules in Mininet.
"""

import time
import sys
import os
from groq import Groq
from mininet.net import Mininet
from mininet.node import Controller

# Read API key from environment for safety
# Read API key from environment for safety
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if not GROQ_API_KEY:
    print("[FATAL] GROQ_API_KEY environment variable is not set.")
    print("        Export your key first, e.g.:")
    print('        export GROQ_API_KEY="your_real_key_here"')
    sys.exit(1)


def generate_network_command(user_intent, feedback=None):
    """Call Groq LLM to generate a single iptables command."""
    print("      [LLM] Querying Groq API...")

    client = Groq(api_key=GROQ_API_KEY)

    # Prompt: allow different strategies (OUTPUT / FORWARD, etc.)
    system_prompt = """You are an experienced Linux network engineer working in a Mininet testbed.

Your job is to translate high-level user intents into a SINGLE iptables command
that SHOULD implement the requested behavior on the source host.

Environment:
- Hosts: h1, h2, h3
- IPs:   h1 = 10.0.0.1, h2 = 10.0.0.2, h3 = 10.0.0.3
- A single OpenFlow switch connects all hosts.
- The iptables command will be executed on the SOURCE host's shell.

Requirements:
- Return EXACTLY ONE iptables command.
- Do NOT include explanations, comments, prompts, or code fences.
- You MAY use OUTPUT, INPUT, or FORWARD chains, or interface-based rules.
- Use normal iptables syntax that would run on a Linux host.

Examples:
User intent: "Block traffic from h1 to h2"
Possible answer: iptables -I OUTPUT -d 10.0.0.2 -j DROP

User intent: "Block h1 from reaching h3"
Possible answer: iptables -I OUTPUT -d 10.0.0.3 -j DROP
"""

    if feedback:
        user_message = (
            f"User intent: {user_intent}\n\n"
            f"The previous command FAILED in testing. Details: {feedback}\n"
            "Generate a different iptables command that might work better."
        )
    else:
        user_message = f"User intent: {user_intent}"

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=100,
        )

        command = completion.choices[0].message.content.strip()

        # Strip code fences if the model still adds them
        if "```" in command:
            parts = command.split("```")
            # take the middle part if possible
            if len(parts) >= 2:
                command = parts[1]
            command = command.replace("bash", "").replace("sh", "")
            command = command.strip()

        # Remove quotes just in case
        command = command.replace('"', "").replace("'", "").strip()

        print(f"      [LLM] Generated: {command}")
        return command

    except Exception as e:
        print(f"      [ERROR] LLM call failed: {e}")
        return None


def test_connectivity(net, src, dst):
    """Test if src can reach dst using ping."""
    h_src = net.get(src)
    h_dst = net.get(dst)
    result = h_src.cmd(f"ping -c 3 -W 1 {h_dst.IP()}")

    if "0% packet loss" in result:
        return 0, "REACHABLE"
    elif "100% packet loss" in result:
        return 100, "BLOCKED"
    else:
        # Some intermediate loss or different output
        return 50, "PARTIAL"


def process_intent(net, intent, src, dst, max_attempts=3):
    """Process a single user intent with baseline, deploy, verify, feedback."""
    print("\n" + "=" * 70)
    print(f" USER INTENT: {intent}")
    print("=" * 70)

    h_src = net.get(src)
    feedback = None

    for attempt in range(1, max_attempts + 1):
        print(f"\n--- Attempt {attempt}/{max_attempts} ---")

        # 1) LLM Translation
        print("\n[1/5] LLM Translation")
        command = generate_network_command(intent, feedback)
        if not command:
            print("      [SKIP] No command generated, moving to next attempt...")
            continue

        # 2) Baseline test
        print("\n[2/5] Baseline Test")
        loss_before, status_before = test_connectivity(net, src, dst)
        print(f"      Before: {loss_before}% loss ({status_before})")

        # 3) Deploy configuration
        print("\n[3/5] Deploy Configuration")
        deploy_output = h_src.cmd(command)
        print(f"      Applied: {command}")
        if deploy_output.strip():
            print(f"      iptables output: {deploy_output.strip()}")
        time.sleep(1)

        # 4) Verification test
        print("\n[4/5] Verification Test")
        loss_after, status_after = test_connectivity(net, src, dst)
        print(f"      After: {loss_after}% loss ({status_after})")

        # 5) Validation
        print("\n[5/5] Validation")

        # For "block" intents, we expect 100% packet loss.
        # (For allow intents, we would expect 0%, but here we only test blocking.)
        if "block" in intent.lower():
            success = loss_after == 100
        else:
            success = loss_after == 0

        if success:
            print("\n" + "=" * 70)
            print(" *** SUCCESS: INTENT VERIFIED ***")
            print("=" * 70)
            print(f"\n Intent:    {intent}")
            print(f" LLM Gen:   {command}")
            print(f" Before:    {loss_before}% loss")
            print(f" After:     {loss_after}% loss")
            print(f" Attempts:  {attempt}")
            return {"success": True, "command": command, "attempts": attempt}
        else:
            print(
                f"      [FAIL] Intent not satisfied. "
                f"Expected fully blocked, but got {loss_after}% loss."
            )
            feedback = (
                f"Expected traffic to be fully blocked between {src} and {dst}, "
                f"but after applying the rule, measured {loss_after}% packet loss."
            )

            # Reset iptables on the source host before the next attempt
            h_src.cmd("iptables -F")
            time.sleep(1)

    print("\n[FAIL] Could not verify intent after all attempts.")
    return {"success": False, "command": None, "attempts": max_attempts}


def main():
    print("=" * 70)
    print(" REAL LLM-BASED SDN INTENT GENERATOR - EXPERIMENT 1")
    print("=" * 70)
    print("\n[Architecture]")
    print(" LLM:          Groq (Llama-3.3-70B)")
    print(" Network:      Mininet (single switch, three hosts)")
    print(" Verification: Automated ping-based testing")
    print(" Feedback:     Closed-loop refinement with LLM")

    input("\n[Press Enter to start the experiment...]")

    # Create network
    print("\n[Network Setup]")
    net = Mininet(controller=Controller)
    c0 = net.addController("c0")
    s1 = net.addSwitch("s1")
    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    h3 = net.addHost("h3", ip="10.0.0.3/24")
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.start()
    print(" [OK] Network ready: h1, h2, h3")
    time.sleep(2)

    # MAIN EXPERIMENT CASE 
    tests = [
        {"intent": "Block traffic from h1 to h2", "src": "h1", "dst": "h2"},
        # If you want a second scenario, uncomment this:
        # {"intent": "Block h1 from reaching h3", "src": "h1", "dst": "h3"},
    ]

    results = []
    for i, test in enumerate(tests, 1):
        print("\n" + "=" * 70)
        print(f" TEST {i}/{len(tests)}")
        print("=" * 70)
        input("\n[Press Enter to run this test case...]")

        result = process_intent(net, test["intent"], test["src"], test["dst"])
        results.append({**test, **result})

        # Cleanup iptables on source host between tests
        h = net.get(test["src"])
        h.cmd("iptables -F")
        time.sleep(1)

    # Summary
    print("\n\n" + "=" * 70)
    print(" FINAL RESULTS")
    print("=" * 70)

    for i, r in enumerate(results, 1):
        status = "[PASS]" if r["success"] else "[FAIL]"
        print(f"\n {i}. {status} {r['intent']}")
        print(f"    Attempts: {r['attempts']}")
        if r["command"]:
            print(f"    Command:  {r['command']}")

    success_count = sum(1 for r in results if r["success"])
    success_rate = (success_count / len(results)) * 100 if results else 0.0
    print(f"\n Success Rate: {success_rate:.0f}%")

    print("\n" + "=" * 70)
    print(" KEY DEMONSTRATION ELEMENTS")
    print("=" * 70)
    print(" [OK] Real LLM called via Groq API")
    print(" [OK] Natural-language intent processed")
    print(" [OK] Network behavior validated in Mininet")
    print(" [OK] Closed-loop verification workflow executed")

    net.stop()
    print("\n Experiment finished.\n")


if __name__ == "__main__":
    main()