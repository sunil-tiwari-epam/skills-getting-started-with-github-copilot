from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities_state():
    original_state = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_state)


client = TestClient(app)
# Tests intentionally cover signup and unregister happy/error paths.


def test_root_redirects_to_static_index():
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_seed_data():
    response = client.get("/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Gym Class" in data


def test_get_activities_includes_cache_headers_and_expected_shape():
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["pragma"] == "no-cache"

    data = response.json()
    sample_activity = data["Chess Club"]
    assert {"description", "schedule", "max_participants", "participants"}.issubset(sample_activity.keys())
    assert isinstance(sample_activity["participants"], list)


def test_signup_successfully_adds_participant():
    email = "newstudent@mergington.edu"

    response = client.post(f"/activities/Chess%20Club/signup?email={email}")

    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for Chess Club"
    assert email in activities["Chess Club"]["participants"]


def test_signup_rejects_invalid_email():
    response = client.post("/activities/Chess%20Club/signup?email=not-an-email")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email address"


def test_signup_requires_email_query_parameter():
    response = client.post("/activities/Chess%20Club/signup")

    assert response.status_code == 422


def test_signup_rejects_empty_or_whitespace_email():
    response = client.post("/activities/Chess%20Club/signup", params={"email": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email address"


def test_signup_rejects_non_school_domain_email():
    response = client.post("/activities/Chess%20Club/signup?email=student@gmail.com")

    assert response.status_code == 400
    assert response.json()["detail"] == "Email must use @mergington.edu domain"


def test_signup_rejects_missing_activity():
    response = client.post("/activities/Photography%20Club/signup?email=student@mergington.edu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant():
    existing_email = "michael@mergington.edu"

    response = client.post(f"/activities/Chess%20Club/signup?email={existing_email}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Student is already signed up"


def test_signup_rejects_when_activity_is_full():
    activities["Micro Robotics"] = {
        "description": "Small group robotics workshop",
        "schedule": "Mondays, 4:00 PM - 5:00 PM",
        "max_participants": 1,
        "participants": ["one@mergington.edu"],
    }

    response = client.post("/activities/Micro%20Robotics/signup?email=two@mergington.edu")

    assert response.status_code == 409
    assert response.json()["detail"] == "Activity is full"


def test_signup_normalizes_email_case_and_spaces():
    raw_email = "  NewStudent@Mergington.edu  "
    normalized = "newstudent@mergington.edu"

    response = client.post("/activities/Chess%20Club/signup", params={"email": raw_email})

    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {normalized} for Chess Club"
    assert normalized in activities["Chess Club"]["participants"]


def test_unregister_removes_participant():
    response = client.delete("/activities/Chess%20Club/participants/michael@mergington.edu")

    assert response.status_code == 200
    assert response.json()["message"] == "Unregistered michael@mergington.edu from Chess Club"
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


def test_unregister_rejects_unknown_activity():
    response = client.delete("/activities/Unknown%20Club/participants/student@mergington.edu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_missing_participant():
    response = client.delete("/activities/Chess%20Club/participants/notfound@mergington.edu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found in activity"


def test_unregister_normalizes_email_case_and_spaces():
    response = client.delete("/activities/Chess%20Club/participants/  Michael@Mergington.edu  ")

    assert response.status_code == 200
    assert response.json()["message"] == "Unregistered michael@mergington.edu from Chess Club"
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


def test_unregister_same_participant_twice_fails_second_time():
    first_response = client.delete("/activities/Chess%20Club/participants/michael@mergington.edu")
    second_response = client.delete("/activities/Chess%20Club/participants/michael@mergington.edu")

    assert first_response.status_code == 200
    assert second_response.status_code == 404
    assert second_response.json()["detail"] == "Participant not found in activity"
