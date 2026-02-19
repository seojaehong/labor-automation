# Report: Legal Platform Integration Feasibility

> Date verified: 2026-02-19 (US local date context)

## 1. Research Question

Can LBOX and SuperLawyer be directly connected through MCP/API for automated legal drafting workflow?

## 2. Verified Findings

1. MCP requires a server exposing standardized tool interfaces (`tools/list`, `tools/call`) for agent-to-tool execution.
2. SuperLawyer provides documented document workflows:
   - long-form drafting and export options
   - supported upload formats include `.hwp/.hwpx/.doc/.docx/.pdf`
3. SuperLawyer terms include restrictions against reverse engineering and non-authorized automated access.
4. Public MCP support exists for coding agents and browser automation tooling (e.g., Playwright MCP), but this does not imply legal platform authorization.
5. For LBOX, publicly accessible pages reviewed in this run did not show a public API/MCP endpoint; parts of the main site were not crawlable from this environment.

## 3. Conclusion

- Immediate direct integration path: **not clearly available**.
- Technically possible workaround (browser automation): **operationally fragile and policy-risky**.
- Best present-state solution: **hybrid local pipeline** using controlled export/import + AI packet generation.

## 4. Sources

- MCP server tools spec: https://modelcontextprotocol.io/specification/2024-11-05/server/tools
- SuperLawyer long-form drafting help: https://docs.channel.io/superlawyer/ko/articles/%EB%A1%B1%ED%8F%BC%EB%AC%B8%EC%84%9C%EC%9E%91%EC%84%B1-%EA%B8%B0%EB%8A%A5-51420f37
- SuperLawyer document-based conversation (formats): https://docs.channel.io/superlawyer/ko/articles/%EB%AC%B8%EC%84%9C-%EA%B8%B0%EB%B0%98-%EB%8C%80%ED%99%94-552c3302
- SuperLawyer terms: https://help.superlawyer.co.kr/7a0c27fd-b91d-4057-9b18-d95f0e681647
- Playwright MCP (official repo): https://github.com/microsoft/playwright-mcp
- OpenAI MCP docs entry: https://developers.openai.com/resources/docs-mcp
- Claude Code MCP docs: https://docs.anthropic.com/en/docs/claude-code/mcp
- Gemini CLI MCP server doc (official repo): https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md
- LBOX AI Agent intro page: https://lbox-agent.framer.website/
