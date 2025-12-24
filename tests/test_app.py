"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


class TestActivitiesEndpoint:
    """Test the GET /activities endpoint"""

    def test_get_activities_returns_200(self):
        """Test that getting activities returns status code 200"""
        response = client.get("/activities")
        assert response.status_code == 200

    def test_get_activities_returns_dict(self):
        """Test that activities endpoint returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)

    def test_get_activities_contains_expected_fields(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_has_activities(self):
        """Test that at least some activities are returned"""
        response = client.get("/activities")
        activities = response.json()
        assert len(activities) > 0


class TestSignupEndpoint:
    """Test the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_valid_activity(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]

    def test_signup_returns_message(self):
        """Test that signup returns a message"""
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "student@mergington.edu"}
        )
        data = response.json()
        assert "message" in data

    def test_signup_duplicate_fails(self):
        """Test that signing up twice fails"""
        email = "duplicate@mergington.edu"
        activity = "Art Club"
        
        # First signup
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_invalid_activity_returns_404(self):
        """Test that signing up for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_adds_to_participants(self):
        """Test that signup actually adds participant to activity"""
        email = "verify@mergington.edu"
        activity = "Drama Club"
        
        # Get initial participants
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        final_count = len(response.json()[activity]["participants"])
        assert final_count == initial_count + 1
        assert email in response.json()[activity]["participants"]


class TestUnregisterEndpoint:
    """Test the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_removes_participant(self):
        """Test that unregister removes participant from activity"""
        email = "removeme@mergington.edu"
        activity = "Debate Team"
        
        # Sign up first
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        response = client.get("/activities")
        final_count = len(response.json()[activity]["participants"])
        assert final_count == initial_count - 1
        assert email not in response.json()[activity]["participants"]

    def test_unregister_invalid_activity_returns_404(self):
        """Test that unregistering from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404

    def test_unregister_not_registered_returns_400(self):
        """Test that unregistering non-registered user returns 400"""
        response = client.delete(
            "/activities/Math Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_returns_message(self):
        """Test that unregister returns appropriate message"""
        email = "unregtest@mergington.edu"
        activity = "Chess Club"
        
        # Sign up first
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        data = response.json()
        assert "message" in data
        assert email in data["message"]


class TestRootEndpoint:
    """Test the root endpoint"""

    def test_root_redirects(self):
        """Test that root endpoint redirects to static content"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307


class TestIntegration:
    """Integration tests for multiple operations"""

    def test_complete_signup_and_unregister_flow(self):
        """Test full flow: signup then unregister"""
        email = "integration@mergington.edu"
        activity = "Programming Class"
        
        # Verify activity exists
        response = client.get("/activities")
        assert activity in response.json()
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify in participants
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify removed from participants
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]

    def test_multiple_signups_same_activity(self):
        """Test multiple different users can sign up for same activity"""
        activity = "Gym Class"
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
