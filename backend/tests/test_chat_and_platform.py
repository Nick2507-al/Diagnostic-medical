import json

from app.schemas import DiagnosisReport
from app.services.ai import SYSTEM_PROMPT, format_patient, normalise_report

from .fakes import sample_report


def sse_events(text: str) -> list[tuple[str, dict]]:
    out = []
    for chunk in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def new_analysis(c) -> str:
    return c.post("/api/analyses", data={"data": json.dumps({"symptoms": "fièvre"})}).json()["id"]


def test_chat_about_analysis_streams_and_persists(make_user, fake_ai):
    c = make_user()
    aid = new_analysis(c)
    conv = c.post("/api/conversations", json={"analysis_id": aid}).json()
    r = c.post(f"/api/conversations/{conv['id']}/messages", json={"content": "Et si c'était une typhoïde ?"})
    assert r.headers["content-type"].startswith("text/event-stream")
    events = sse_events(r.text)
    assert [e for e, _ in events] == ["start", "delta", "delta", "done"]
    case, history = fake_ai.chat_calls[0]
    assert case.report is not None and history[-1]["content"] == "Et si c'était une typhoïde ?"
    msgs = c.get(f"/api/conversations/{conv['id']}").json()["messages"]
    assert [(m["role"], m["content"]) for m in msgs] == [
        ("user", "Et si c'était une typhoïde ?"), ("assistant", "Réponse clinique.")]
    # second turn carries the full history
    c.post(f"/api/conversations/{conv['id']}/messages", json={"content": "Quel antibiotique ?"})
    assert len(fake_ai.chat_calls[1][1]) == 3


def test_free_conversation_titled_from_first_message(make_user):
    c = make_user()
    conv = c.post("/api/conversations", json={}).json()
    c.post(f"/api/conversations/{conv['id']}/messages", json={"content": "Schéma TB de l'enfant\nmerci"})
    assert c.get("/api/conversations").json()[0]["title"] == "Schéma TB de l'enfant"


def test_chat_error_ends_stream_cleanly(make_user, fake_ai):
    c = make_user()
    conv = c.post("/api/conversations", json={}).json()
    fake_ai.fail_with = "Limite de débit"
    events = sse_events(c.post(f"/api/conversations/{conv['id']}/messages", json={"content": "x"}).text)
    assert ("error", {"message": "Limite de débit"}) in events and events[-1][0] == "done"


def test_chat_idor_and_validation(make_user):
    alice, bob = make_user("alice@example.com"), make_user("bob@example.com")
    conv = alice.post("/api/conversations", json={}).json()
    assert bob.get(f"/api/conversations/{conv['id']}").status_code == 404
    assert bob.post(f"/api/conversations/{conv['id']}/messages", json={"content": "x"}).status_code == 404
    assert bob.delete(f"/api/conversations/{conv['id']}").status_code == 404
    assert alice.post(f"/api/conversations/{conv['id']}/messages", json={"content": ""}).status_code == 422
    assert alice.post(f"/api/conversations/{conv['id']}/messages", json={"content": "x" * 8001}).status_code == 422


def test_cannot_chat_about_pending_or_failed_analysis(make_user, fake_ai):
    c = make_user()
    fake_ai.fail_with = "panne"
    aid = new_analysis(c)
    assert c.post("/api/conversations", json={"analysis_id": aid}).status_code == 409


def test_security_headers_and_no_store(make_user):
    c = make_user()
    r = c.get("/api/auth/me")
    for h in ("x-content-type-options", "x-frame-options", "content-security-policy", "referrer-policy"):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"


def test_errors_are_json_and_leak_nothing(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}
    r = client.post("/api/auth/login", content=b"{bad json", headers={"content-type": "application/json"})
    assert r.status_code == 422 and "Traceback" not in r.text


def test_oversized_body_rejected_early(client):
    r = client.post("/api/auth/login", content=b"x", headers={"content-length": str(200 * 1024 * 1024)})
    assert r.status_code == 413


def test_health(client):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "ai_configured": False}


def test_missing_api_key_gives_clear_503(make_user):
    from app.main import app
    from app.services import ai as ai_module

    app.dependency_overrides.pop(ai_module.get_ai, None)
    c = make_user()
    r = c.post("/api/analyses", data={"data": json.dumps({"symptoms": "fièvre"})})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["detail"]


# ─── unit checks on the AI layer ───

def test_normalise_report_bounds_sorts_and_sums_to_100():
    report = sample_report(probs=(10, 130, 40))
    out = normalise_report(report)
    probs = [h["probabilite"] for h in out["hypotheses"]]
    assert sum(probs) == 100 and probs == sorted(probs, reverse=True)


def test_report_schema_is_structured_output_compatible():
    schema = DiagnosisReport.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for key in ("minimum", "maximum", "minLength", "maxLength"):
                assert key not in node
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)


def test_prompt_mentions_african_priorities_and_injection_guard():
    for term in ("Paludisme", "Tuberculose", "drépanocytose".capitalize(), "PCIME", "jamais une instruction"):
        assert term.lower() in SYSTEM_PROMPT.lower()
    text = format_patient({"age_years": 4, "sex": "homme", "hiv_status": "inconnu"}, "toux", "")
    assert "Âge (ans) : 4" in text and "VIH" not in text  # unknown values omitted
