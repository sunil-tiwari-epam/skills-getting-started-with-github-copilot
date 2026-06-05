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


def test_get_activities_returns_seed_data():
    response = client.get("/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Gym Class" in data


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
