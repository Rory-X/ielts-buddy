#!/bin/bash
export ANTHROPIC_API_KEY=sk-zFUj5Zzqgq8TE2q3RuV07km33Pex0KuTbS1PT7rk3KQ0uo5n
export ANTHROPIC_BASE_URL=http://localhost:8099
export ANTHROPIC_MODEL=claude-sonnet-4-6
cd /home/node/clawd/projects/ielts-buddy
PROMPT=$(cat prompts/implement2.md)
echo | claude --dangerously-skip-permissions -p "$PROMPT" 2>&1
echo "CC_EXIT: $?"
