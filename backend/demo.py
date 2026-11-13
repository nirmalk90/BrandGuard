from uuid import uuid4

from backend.db import rules, sources, workspaces
from backend.schemas import Profile, Rule

DEMO_CONTENT = (
    "Our magic AI guarantees 100% accurate results and is the cheapest solution in India. "
    "Subscribe today for just ₹99 per month!"
)
ACTORS = {"creator": "Avery Shah", "reviewer": "Jordan Rao", "admin": "Morgan Patel"}


def new_id():
    return str(uuid4())


def seed_workspace(connection):
    workspace_id = new_id()
    profile = Profile(
        name="NovaTech", industry="AI and Business Software",
        description="AI-powered productivity tools for modern teams.",
        audience="Small businesses and operations teams",
        personality="Trustworthy and approachable", style="Direct, concise, evidence-led",
        tone="Professional, clear, trustworthy, friendly",
    )
    connection.execute(workspaces.insert().values(id=workspace_id, profile=profile.model_dump()))
    guide_id, facts_id = new_id(), new_id()
    connection.execute(sources.insert(), [
        dict(id=guide_id, workspace_id=workspace_id, title="NovaTech Messaging Guidelines",
             version=1, content="Use professional, clear, trustworthy and friendly language. "
             "Use AI-powered solution in place of magic AI. Use Designed to improve efficiency "
             "in place of guaranteed productivity. Avoid accuracy or results guarantees, "
             "market-wide price superlatives and risk-free investment claims."),
        dict(id=facts_id, workspace_id=workspace_id, title="NovaTech Product Fact Sheet",
             version=1, content="NovaTech offers subscription plans starting at ₹499 per month. "
             "NovaTech provides AI-powered productivity tools. NovaTech offers customer support "
             "through official support channels."),
    ])
    entries = [
        ("AI product terminology", "Terminology", "magic AI", "AI-powered solution", "medium"),
        ("Efficiency terminology", "Terminology", "guaranteed productivity", "designed to improve efficiency", "medium"),
        ("Absolute accuracy claims", "Promotional claim", "100% accurate", "designed to improve accuracy", "high"),
        ("Results guarantees", "Promotional claim", "guaranteed results", "designed to support consistent results", "high"),
        ("Market-wide price comparisons", "Promotional claim", "cheapest in India|cheapest solution in India", "built for growing teams", "high"),
        ("Investment risk claims", "Promotional claim", "risk-free investment", "review the applicable terms", "high"),
        ("Professional calls to action", "Tone", "buy now or else|act now or lose out", "explore our plans", "medium"),
    ]
    policy = [
        Rule(title=title, category=category, pattern=phrase, replacement=replacement,
             severity=severity, kind="phrase", source_id=guide_id,
             description=f"NovaTech guidance requires copy to avoid {phrase.replace('|', ' or ')}.")
        for title, category, phrase, replacement, severity in entries
    ]
    policy.append(Rule(
        title="Starting subscription price", category="Approved fact", kind="price_floor",
        pattern="subscribe|subscription|subscriptions|plans|plan", severity="high",
        source_id=facts_id, value=499,
        description="NovaTech subscription plans start at ₹499 per month. This floor applies to standard monthly subscriptions.",
        replacement="₹499 per month",
    ))
    for fact in (
        "NovaTech provides AI-powered productivity tools.",
        "NovaTech offers customer support through official support channels.",
    ):
        policy.append(Rule(title=fact, category="Approved fact", kind="approved_fact",
                           description=fact, severity="low", source_id=facts_id))
    connection.execute(rules.insert(), [
        dict(id=new_id(), workspace_id=workspace_id, source_id=rule.source_id,
             version=1, active=True, spec=rule.model_dump(mode="json"))
        for rule in policy
    ])
    return workspace_id
