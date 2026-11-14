import json

PATIENT = {"age_years": 6, "sex": "femme", "weight_kg": 19, "country": "Congo", "temperature_c": 39.8}


def create(c, symptoms="Fièvre 39,8 °C, convulsions", files=None, **extra):
    payload = {"symptoms": symptoms, "patient": PATIENT, **extra}
    return c.post("/api/analyses", data={"data": json.dumps(payload)}, files=files or [])


def test_create_runs_analysis_and_stores_normalised_report(make_user, fake_ai):
    c = make_user()
    r = create(c)
    assert r.status_code == 202
    detail = c.get(f"/api/analyses/{r.json()['id']}").json()
    assert detail["status"] == "done"
    assert detail["triage_level"] == "urgence_vitale"
    assert detail["top_diagnosis"].startswith("Paludisme")
    probs = [h["probabilite"] for h in detail["result"]["hypotheses"]]
    assert sum(probs) == 100 and probs == sorted(probs, reverse=True)  # 50/25/15 rescaled
    case = fake_ai.analyze_calls[0]
    assert "Congo" in case.patient_text and "convulsions" in case.patient_text


def test_ai_failure_is_recorded_and_retry_works(make_user, fake_ai):
    c = make_user()
    fake_ai.fail_with = "Service IA injoignable"
    aid = create(c).json()["id"]
    d = c.get(f"/api/analyses/{aid}").json()
    assert d["status"] == "error" and d["error_message"] == "Service IA injoignable"
    fake_ai.fail_with = None
    assert c.post(f"/api/analyses/{aid}/retry").status_code == 202
    assert c.get(f"/api/analyses/{aid}").json()["status"] == "done"


def test_empty_case_rejected(make_user):
    c = make_user()
    assert create(c, symptoms="").status_code == 422


def test_invalid_payloads_rejected(make_user):
    c = make_user()
    assert c.post("/api/analyses", data={"data": "{not json"}).status_code == 422
    assert create(c, patient={"age_years": -4}).status_code == 422
    assert create(c, patient={"sex": "robot"}).status_code == 422
    assert create(c, injected="x").status_code == 422


def test_idor_other_users_cannot_read_retry_or_delete(make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    aid = create(alice).json()["id"]
    assert bob.get(f"/api/analyses/{aid}").status_code == 404
    assert bob.post(f"/api/analyses/{aid}/retry").status_code == 404
    assert bob.delete(f"/api/analyses/{aid}").status_code == 404
    assert bob.post("/api/conversations", json={"analysis_id": aid}).status_code == 404
    assert bob.get("/api/analyses").json()["total"] == 0
    assert alice.get(f"/api/analyses/{aid}").status_code == 200


def test_history_search_pagination_and_injection(make_user):
    c = make_user()
    for i in range(3):
        create(c, symptoms=f"Toux chronique cas {i}")
    create(c, symptoms="Diarrhée aqueuse 100%_profuse")
    page = c.get("/api/analyses", params={"page_size": 2}).json()
    assert page["total"] == 4 and len(page["items"]) == 2
    assert c.get("/api/analyses", params={"q": "toux"}).json()["total"] == 3
    assert c.get("/api/analyses", params={"q": "100%_"}).json()["total"] == 1  # wildcards escaped
    # "%" must match only the row that literally contains it (unescaped it would match all 4)
    assert c.get("/api/analyses", params={"q": "%"}).json()["total"] == 1
    for payload in ["' OR 1=1 --", "'; DROP TABLE analyses; --", "\\"]:
        r = c.get("/api/analyses", params={"q": payload})
        assert r.status_code == 200 and r.json()["total"] == 0
    assert c.get("/api/analyses").json()["total"] == 4  # table intact
    assert c.get("/api/analyses", params={"triage": "x' OR 1=1"}).status_code == 422
    assert c.get("/api/analyses", params={"page": 0}).status_code == 422


def test_malformed_ids_return_422_not_500(make_user):
    c = make_user()
    for bad in ["1", "../../etc/passwd", "1 OR 1=1"]:
        assert c.get(f"/api/analyses/{bad}").status_code in (404, 422)


def test_delete_analysis(make_user):
    c = make_user()
    aid = create(c).json()["id"]
    assert c.delete(f"/api/analyses/{aid}").status_code == 204
    assert c.get(f"/api/analyses/{aid}").status_code == 404


def test_stats(make_user):
    c = make_user()
    create(c)
    create(c)
    s = c.get("/api/stats").json()
    assert s["total_analyses"] == 2 and s["by_triage"] == {"urgence_vitale": 2}
    assert s["top_diagnoses"][0]["nombre"] == 2


def test_analysis_rate_limit(make_user):
    c = make_user()
    codes = [create(c).status_code for _ in range(31)]
    assert codes[-1] == 429 and codes.count(202) == 30
