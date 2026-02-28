import asyncio
import json
import logging
import uuid

import config
from services.parser import parse_text
from services.classifier import classify_sections
from services.analyzer import analyze_contract
from services.risk_flagger import flag_risks

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}
MAX_SESSIONS = 30
MAX_AGENT_ITERATIONS = 5

AGENT_SYSTEM_PROMPT = """You are the Student Privacy Agent — an AI advisor built for Hong Kong students and parents.
You help users understand privacy policies, terms of service, and data practices of popular apps and school platforms.

Your expertise covers:
- Hong Kong's Personal Data (Privacy) Ordinance (PDPO) and how it applies to students
- Common concerns with apps like TikTok, Spotify, Instagram, WhatsApp, school learning platforms (Google Classroom, Zoom, Teams)
- Age-appropriate data handling and parental consent requirements
- Cross-border data transfers (especially HK ↔ Mainland China)
- Student data rights in educational settings

When answering:
- Use simple, clear language suitable for students and parents (age 13+)
- Highlight specific risks relevant to young users in Hong Kong
- Reference HK privacy law (PDPO) where applicable
- Suggest concrete actions the user can take (privacy settings to change, opt-outs, etc.)
- If page text is available and the user wants analysis, use the analyze_privacy_document tool
- Format responses with clear sections using **bold** headers and bullet points
- Be warm, approachable, and non-alarmist while being thorough about risks

Key HK Privacy Context:
- PDPO requires data collectors to inform users of the purpose of data collection
- Personal data should only be collected for lawful purposes directly related to a function of the data user
- Students under 18 have additional protections; parental consent is important
- Cross-border data transfer to mainland China is a common concern for HK residents
- Schools must comply with PDPO when using ed-tech platforms
- The Privacy Commissioner for Personal Data (PCPD) enforces the ordinance
"""

TOOLS = [
    {
        "toolSpec": {
            "name": "analyze_privacy_document",
            "description": (
                "Analyze a privacy policy, terms of service, or legal document. "
                "Returns a structured summary with risk flags, key points, and section-by-section breakdown. "
                "Use this when the user wants to understand a specific document or the page they are viewing."
            ),
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The full text of the document to analyze",
                        },
                        "doc_type": {
                            "type": "string",
                            "description": "Type of document: privacy_policy, terms_of_service, student_agreement, etc.",
                        },
                        "persona": {
                            "type": "string",
                            "description": "User persona for tailored analysis. Default: hong_kong_student",
                        },
                    },
                    "required": ["text"],
                }
            },
        }
    }
]


async def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "analyze_privacy_document":
        text = tool_input.get("text", "")
        doc_type = tool_input.get("doc_type", "privacy_policy")
        persona = tool_input.get("persona", "hong_kong_student")

        if len(text.strip()) < 50:
            return json.dumps({"error": "Document text too short to analyze (need 50+ characters)."})

        sections = parse_text(text)
        classified = classify_sections(sections)
        llm_result = await analyze_contract(classified, doc_type, persona)
        risks = flag_risks(classified, llm_result)

        result = {
            "summary": llm_result.get("summary", ""),
            "key_points": llm_result.get("key_points", []),
            "risks": [
                {
                    "category": r.category,
                    "severity": r.severity,
                    "clause_excerpt": r.clause_excerpt,
                    "explanation": r.explanation,
                }
                for r in risks
            ],
            "entities": llm_result.get("entities", {}),
            "persona_notes": llm_result.get("persona_notes"),
        }
        return json.dumps(result, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _get_or_create_session(session_id: str | None, page_text: str | None = None) -> tuple[str, dict]:
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        if page_text:
            session["page_text"] = page_text
        return session_id, session

    new_id = str(uuid.uuid4())
    session = {"messages": [], "page_text": page_text}
    _sessions[new_id] = session

    if len(_sessions) > MAX_SESSIONS:
        oldest = next(iter(_sessions))
        del _sessions[oldest]

    return new_id, session


async def _call_bedrock(client, messages: list, system_prompt: str):
    return await asyncio.to_thread(
        client.converse,
        modelId=config.BEDROCK_MODEL_ID,
        messages=messages,
        system=[{"text": system_prompt}],
        toolConfig={"tools": TOOLS},
        inferenceConfig={"maxTokens": 2048, "temperature": 0.7},
    )


async def agent_chat(
    session_id: str | None,
    message: str,
    page_text: str | None = None,
) -> dict:
    sid, session = _get_or_create_session(session_id, page_text)

    system_prompt = AGENT_SYSTEM_PROMPT
    if session.get("page_text"):
        truncated_text = session["page_text"][:8000]
        system_prompt += (
            "\n\nCONTEXT: The user is currently viewing a web page. "
            "If the user asks you to analyze it, call analyze_privacy_document with the text below.\n\n"
            f"<page_text>\n{truncated_text}\n</page_text>"
        )

    session["messages"].append({
        "role": "user",
        "content": [{"text": message}],
    })

    if not config.AWS_REGION or not config.BEDROCK_MODEL_ID:
        fallback = _generate_fallback_reply(message, session.get("page_text"))
        session["messages"].append({"role": "assistant", "content": [{"text": fallback}]})
        return {"session_id": sid, "reply": fallback}

    try:
        import boto3
        from botocore.exceptions import ClientError

        client_kwargs: dict = {"region_name": config.AWS_REGION}
        if config.AWS_ACCESS_KEY_ID:
            client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
        if config.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY

        client = boto3.client("bedrock-runtime", **client_kwargs)

        for _ in range(MAX_AGENT_ITERATIONS):
            response = await _call_bedrock(client, session["messages"], system_prompt)
            output_msg = response["output"]["message"]
            session["messages"].append(output_msg)
            stop_reason = response["stopReason"]

            if stop_reason == "tool_use":
                tool_results = []
                for block in output_msg["content"]:
                    if "toolUse" in block:
                        tool_use = block["toolUse"]
                        logger.info("Agent calling tool: %s", tool_use["name"])
                        result_text = await _execute_tool(tool_use["name"], tool_use["input"])
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"text": result_text}],
                            }
                        })

                session["messages"].append({"role": "user", "content": tool_results})
                continue

            # Final text response
            reply_parts = []
            for block in output_msg["content"]:
                if "text" in block:
                    reply_parts.append(block["text"])

            return {"session_id": sid, "reply": "\n".join(reply_parts)}

        return {
            "session_id": sid,
            "reply": "I've been thinking too hard about this. Could you try rephrasing your question?",
        }

    except Exception as e:
        logger.error("Agent error: %s", e)
        fallback = _generate_fallback_reply(message, session.get("page_text"))
        session["messages"].append({"role": "assistant", "content": [{"text": fallback}]})
        return {"session_id": sid, "reply": fallback, "error": str(e)}


def _generate_fallback_reply(message: str, page_text: str | None) -> str:
    """Provide useful responses even without AWS Bedrock configured."""
    msg = message.lower()

    if any(w in msg for w in ["tiktok", "抖音", "douyin"]):
        return (
            "**TikTok Privacy Concerns for HK Students:**\n\n"
            "- **Data Collection**: TikTok collects extensive data — location, device info, browsing history, "
            "and message content. Users under 18 get some extra protections, but enforcement varies.\n"
            "- **Cross-border Data**: TikTok (ByteDance) may transfer your data to mainland China servers, "
            "which operate under different privacy laws than Hong Kong's PDPO.\n"
            "- **Recommendations:**\n"
            "  - Set your account to **Private**\n"
            "  - Disable **Personalized Ads** in Settings → Privacy\n"
            "  - Turn off **location access**\n"
            "  - Parents: Enable **Family Pairing** for users under 16\n"
            "  - Avoid sharing personal info (school name, HKID) in videos or bio\n\n"
            "Under the PDPO, you have the right to request access to and correction of your personal data held by TikTok."
        )

    if "spotify" in msg:
        return (
            "**Spotify Privacy Concerns for HK Students:**\n\n"
            "- **Data Collection**: Spotify tracks listening habits, device data, and location for "
            "personalized recommendations and ads (free tier).\n"
            "- **Third-party Sharing**: Data is shared with advertisers, analytics partners, and social platforms.\n"
            "- **Student Plans**: The student discount uses SheerID verification, which collects "
            "additional educational data.\n\n"
            "**Recommendations:**\n"
            "- Review privacy settings at spotify.com/account/privacy\n"
            "- Opt out of tailored ads\n"
            "- Be careful connecting social media accounts\n"
            "- Disable \"Social\" features if you don't want listening activity shared"
        )

    if any(w in msg for w in ["instagram", "ig", "insta"]):
        return (
            "**Instagram Privacy Concerns for HK Students:**\n\n"
            "- **Data Collection**: Instagram (Meta) collects photos, messages, location, contacts, "
            "and browsing activity across Meta's family of apps.\n"
            "- **Under-18 Protections**: Accounts for users under 16 are set to Private by default. "
            "Direct messages from unknown adults are restricted.\n"
            "- **Cross-border Data**: Meta transfers data to US servers.\n\n"
            "**Recommendations:**\n"
            "- Keep your account **Private**\n"
            "- Disable **Activity Status**\n"
            "- Turn off **Location Services** for Instagram\n"
            "- Review connected apps in Settings → Security → Apps and Websites\n"
            "- Limit ad personalization in Settings → Ads"
        )

    if any(w in msg for w in ["whatsapp"]):
        return (
            "**WhatsApp Privacy Concerns for HK Students:**\n\n"
            "- **End-to-end Encryption**: Messages are encrypted, which is good for privacy.\n"
            "- **Metadata Collection**: WhatsApp still collects metadata — who you talk to, when, "
            "how often, your phone number, contacts list, device info.\n"
            "- **Meta Sharing**: WhatsApp shares data with Meta (Facebook/Instagram) for business "
            "and advertising purposes.\n\n"
            "**Recommendations:**\n"
            "- Enable **two-step verification**\n"
            "- Disable **Read Receipts** if you value privacy\n"
            "- Set **Last Seen** and **Profile Photo** visibility to \"My Contacts\"\n"
            "- Be cautious about joining unknown groups\n"
            "- Review privacy settings regularly"
        )

    if any(w in msg for w in ["safe", "rights", "pdpo", "law", "regulation"]):
        return (
            "**Your Privacy Rights as a HK Student (PDPO Overview):**\n\n"
            "Under Hong Kong's Personal Data (Privacy) Ordinance:\n\n"
            "1. **Right to Know** — Any app must tell you what data they collect and why\n"
            "2. **Right to Access** — You can request a copy of all your personal data\n"
            "3. **Right to Correct** — You can ask for incorrect data to be fixed\n"
            "4. **Consent** — For students under 18, parental consent is important\n"
            "5. **Cross-border Transfers** — Apps must ensure adequate protection when "
            "transferring data outside HK\n\n"
            "**Quick Tips:**\n"
            "- Always read permission requests before clicking \"Allow\"\n"
            "- Use strong, unique passwords for each app\n"
            "- Regularly review app permissions in your phone settings\n"
            "- Never share your HKID or school ID online"
        )

    if any(w in msg for w in ["analyze", "check", "scan", "review", "page"]):
        if page_text:
            return (
                "I can see you have a page loaded! To get full AI-powered analysis through the agent, "
                "please add your AWS credentials to the backend `.env` file:\n\n"
                "```\nAWS_ACCESS_KEY_ID=your_key\nAWS_SECRET_ACCESS_KEY=your_secret\n"
                "AWS_REGION=us-east-1\n```\n\n"
                "In the meantime, try the **Summary** and **Risks** tabs — they use the existing "
                "analysis pipeline and work right now!"
            )
        return (
            "I'd be happy to analyze a privacy policy for you! Navigate to the page you want me "
            "to check, then click the ContractLens icon first to capture the page text."
        )

    if any(w in msg for w in ["zoom", "google classroom", "teams", "school"]):
        return (
            "**School Platform Privacy for HK Students:**\n\n"
            "Schools in Hong Kong must comply with the PDPO when choosing ed-tech platforms. "
            "Here's what to watch for:\n\n"
            "- **Google Classroom**: Collects usage data, but Google Workspace for Education "
            "has stronger privacy controls than consumer Google accounts.\n"
            "- **Zoom**: Records may be stored on overseas servers. Check if your school's "
            "Zoom admin has enabled proper privacy settings.\n"
            "- **Microsoft Teams**: Similar to Google — enterprise education accounts have "
            "better protections than personal ones.\n\n"
            "**What your school should do:**\n"
            "- Conduct a Privacy Impact Assessment before adopting new platforms\n"
            "- Get parental consent for data collection from minors\n"
            "- Ensure data is not used for advertising\n\n"
            "Ask your school's IT department about their data protection policies!"
        )

    return (
        "Hi! I'm your **Student Privacy Agent** — here to help Hong Kong students "
        "and parents navigate app privacy and data rights.\n\n"
        "I can help you with:\n"
        "- **Analyzing privacy policies** of apps like TikTok, Spotify, Instagram, WhatsApp\n"
        "- **Understanding your rights** under Hong Kong's PDPO\n"
        "- **Checking school platforms** like Google Classroom, Zoom, Teams\n"
        "- **Advising on privacy settings** to protect your data\n\n"
        "Try asking me something like:\n"
        "- \"Is TikTok safe for a 13-year-old?\"\n"
        "- \"What data does Spotify collect about me?\"\n"
        "- \"Analyze this page's privacy policy\"\n"
        "- \"What are my privacy rights as a student in HK?\""
    )
