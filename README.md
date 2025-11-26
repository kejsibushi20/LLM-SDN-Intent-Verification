This repository contains the implementation and experiments for our project:

“Automatic Generation of SDN Intents from Natural Language Commands Using LLMs”
University of Luxembourg —  2025.

The project investigates the reliability issues of Large Language Models (LLMs) in SDN automation and provides a verification-driven intent generation framework that tests LLM-generated rules in a Mininet sandbox before trusting or deploying them.

🎯 Project Goal

LLMs can translate natural-language requests (e.g., “Block traffic from h1 to h2”) into SDN policies, but research shows that most generated configurations fail without verification due to hallucinations or topology inconsistencies.
Our goal is to build a safe SDN intent pipeline that:
Accepts natural-language intents
Generates SDN configurations via LLM (Groq Llama-3.3-70B)
Applies them in Mininet
Verifies real network behavior
Uses feedback to refine incorrect attempts
Accepts only validated configurations

🧩 System Architecture

Our architecture includes:

Natural Language Interface – User expresses high-level intents
LLM Translation Engine – Generates OpenFlow/iptables/JSON outputs
Sandbox SDN Environment (Mininet) – Safe network emulation
Automated Verification Module – Ping tests + packet loss measurement
Feedback Loop – Flow-table analysis + intent refinement
This ensures that no hallucinated or incorrect SDN configuration is ever trusted.
