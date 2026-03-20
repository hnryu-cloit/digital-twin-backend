from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login() -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@digital-twin.ai", "password": "Admin1234!"},
    )
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_project_and_persona_flow():
    headers = login()

    project_response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "name": "신규 컨셉 테스트",
            "type": "컨셉 테스트",
            "purpose": "초기 반응 검증",
            "data_sources": ["customer_profile"],
            "tags": ["신제품"],
            "target_responses": 500,
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    persona_response = client.post(
        "/api/personas/pool",
        headers=headers,
        json={
            "project_id": project_id,
            "segment": "MZ 얼리어답터",
            "age_range": "20-34",
            "gender": "혼합",
            "occupation": "직장인",
            "size": 3,
        },
    )
    assert persona_response.status_code == 201
    assert persona_response.json()["total"] == 3


def test_survey_simulation_report_flow():
    headers = login()

    generate_response = client.post(
        "/api/surveys/generate",
        headers=headers,
        json={
            "project_id": "prj-001",
            "prompt": "AI 카메라 반응 조사",
            "survey_type": "컨셉 테스트",
            "question_count": 4,
        },
    )
    assert generate_response.status_code == 200
    assert len(generate_response.json()["questions"]) == 4

    control_response = client.post(
        "/api/simulations/control",
        headers=headers,
        json={"project_id": "prj-001", "action": "start"},
    )
    assert control_response.status_code == 200
    assert control_response.json()["status"] == "running"

    report_response = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"project_id": "prj-001"},
    )
    assert report_response.status_code == 201
    assert report_response.json()["project_id"] == "prj-001"
