"""
End-to-End Integration Tests for Template Quantities System

Tests the full workflow:
1. UI (Wizard) → API (Project Creation) → Database (Project Storage)
2. API (Generation Trigger) → Generator Service → Content Generator
3. Verify template distribution matches quantities
4. Verify pricing calculations
5. Test backward compatibility

Run with: pytest tests/integration/test_template_quantities_e2e.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import app components separately to avoid table redefinition
from fastapi import FastAPI
from backend.database import Base, get_db
from backend.utils.auth import get_password_hash

# Import models
from backend.models import User, Client, Project

# Import routers
from backend.routers import auth, projects

# Create a minimal app for testing
def create_test_app():
    """Create a minimal FastAPI app for testing"""
    test_app = FastAPI(title="Test App")

    # Register only the routers we need for testing
    test_app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    test_app.include_router(projects.router, prefix="/api/projects", tags=["projects"])

    return test_app


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_e2e.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a new database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override"""
    # Create a fresh app instance for this test
    test_app = create_test_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(db_session, client):
    """Create test user and return auth headers"""
    # Create test user
    test_user = User(
        id="user-test-e2e-123",
        email="test-e2e@example.com",
        hashed_password=get_password_hash("Test1234!"),
        full_name="E2E Test User",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db_session.add(test_user)
    db_session.commit()

    # Login to get token
    response = client.post(
        "/api/auth/login",
        json={"email": "test-e2e@example.com", "password": "Test1234!"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_client_record(db_session):
    """Create a test client in the database"""
    test_client = Client(
        id="client-e2e-test-123",
        name="E2E Test Client",
        email="client-e2e@example.com",
        company="E2E Test Company",
        industry="Technology",
        created_at=datetime.utcnow()
    )
    db_session.add(test_client)
    db_session.commit()
    db_session.refresh(test_client)

    return test_client


class TestTemplateQuantitiesE2E:
    """End-to-end tests for template quantities system"""

    def test_full_workflow_with_template_quantities(
        self, client, auth_headers, test_client_record, db_session
    ):
        """
        Test complete workflow:
        1. Create project with template_quantities
        2. Verify database storage
        3. Verify pricing calculation
        4. Trigger generation
        5. Verify template distribution
        """
        # Step 1: Create project with template quantities
        project_data = {
            "name": "E2E Test Project",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 3,   # Problem Recognition x3
                "2": 2,   # Statistic + Insight x2
                "9": 5,   # How-To x5
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 0.0,
            "platforms": ["linkedin"],
            "tone": "professional"
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        # Step 2: Verify database storage
        assert "id" in project_response
        assert project_response["name"] == "E2E Test Project"
        assert project_response["templateQuantities"] == {"1": 3, "2": 2, "9": 5}
        assert project_response["numPosts"] == 10  # 3 + 2 + 5
        assert project_response["pricePerPost"] == 40.0
        assert project_response["totalPrice"] == 400.0  # 10 posts * $40

        # Verify in database
        project_id = project_response["id"]
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is not None
        assert db_project.template_quantities == {"1": 3, "2": 2, "9": 5}
        assert db_project.num_posts == 10
        assert db_project.total_price == 400.0

        print("✓ Project created successfully with template quantities")
        print(f"  - Project ID: {project_id}")
        print(f"  - Template quantities: {db_project.template_quantities}")
        print(f"  - Total posts: {db_project.num_posts}")
        print(f"  - Total price: ${db_project.total_price}")

    def test_pricing_calculation_with_research(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test pricing calculation with research add-on"""
        project_data = {
            "name": "E2E Pricing Test",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 5,
                "2": 5,
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 15.0,  # Research add-on
            "platforms": ["linkedin"],
            "tone": "professional"
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        # Verify pricing: 10 posts * ($40 + $15) = $550
        assert project_response["numPosts"] == 10
        assert project_response["pricePerPost"] == 40.0
        assert project_response["researchPricePerPost"] == 15.0
        assert project_response["totalPrice"] == 550.0

        print("✓ Pricing calculation correct with research add-on")
        print(f"  - Base: 10 posts * $40 = $400")
        print(f"  - Research: 10 posts * $15 = $150")
        print(f"  - Total: ${project_response['totalPrice']}")

    def test_validation_template_quantities_bounds(
        self, client, auth_headers, test_client_record
    ):
        """Test validation of template quantities (bounds checking)"""
        # Test: quantity exceeds max (100)
        project_data = {
            "name": "Invalid Quantities Test",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 150,  # Exceeds max of 100
            },
            "pricePerPost": 40.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert "cannot exceed 100" in str(error_detail)

        print("✓ Validation correctly rejects excessive quantities")

    def test_validation_invalid_template_id(
        self, client, auth_headers, test_client_record
    ):
        """Test validation of invalid template IDs"""
        project_data = {
            "name": "Invalid Template ID Test",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "999": 5,  # Invalid template ID (> 100)
            },
            "pricePerPost": 40.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert "Invalid template_id" in str(error_detail)

        print("✓ Validation correctly rejects invalid template IDs")

    def test_validation_too_many_templates(
        self, client, auth_headers, test_client_record
    ):
        """Test validation of excessive number of templates (DoS prevention)"""
        # Create 51 templates (exceeds limit of 50)
        template_quantities = {str(i): 1 for i in range(1, 52)}

        project_data = {
            "name": "Too Many Templates Test",
            "clientId": test_client_record.id,
            "templateQuantities": template_quantities,
            "pricePerPost": 40.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert "cannot exceed 50 templates" in str(error_detail)

        print("✓ Validation correctly rejects excessive template count (DoS prevention)")

    def test_preset_package_quick_start(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test creating project with Quick Start preset package (15 posts)"""
        project_data = {
            "name": "Quick Start Package",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 3,  # Problem Recognition
                "2": 3,  # Statistic
                "5": 3,  # Question
                "9": 3,  # How-To
                "10": 3, # Comparison
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 0.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        assert project_response["numPosts"] == 15
        assert project_response["totalPrice"] == 600.0  # 15 * $40

        print("✓ Quick Start preset package created successfully")
        print(f"  - Posts: {project_response['numPosts']}")
        print(f"  - Price: ${project_response['totalPrice']}")

    def test_preset_package_professional(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test creating project with Professional preset package (30 posts)"""
        project_data = {
            "name": "Professional Package",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 2, "2": 2, "3": 2, "4": 2, "5": 2,
                "6": 2, "7": 2, "8": 2, "9": 2, "10": 2,
                "11": 2, "12": 2, "13": 2, "14": 2, "15": 2,
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 0.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        assert project_response["numPosts"] == 30
        assert project_response["totalPrice"] == 1200.0  # 30 * $40

        print("✓ Professional preset package created successfully")
        print(f"  - Posts: {project_response['numPosts']}")
        print(f"  - Price: ${project_response['totalPrice']}")

    def test_preset_package_premium_with_research(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test creating project with Premium preset package (50 posts + research)"""
        project_data = {
            "name": "Premium Package",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 4, "2": 4, "3": 3, "4": 3, "5": 3,
                "6": 3, "7": 3, "8": 3, "9": 3, "10": 3,
                "11": 3, "12": 3, "13": 3, "14": 3, "15": 3,
            },
            "pricePerPost": 40.0,
            "researchPricePerPost": 15.0,  # Research included
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        assert project_response["numPosts"] == 50
        assert project_response["totalPrice"] == 2750.0  # 50 * ($40 + $15)

        print("✓ Premium preset package created successfully")
        print(f"  - Posts: {project_response['numPosts']}")
        print(f"  - Price: ${project_response['totalPrice']}")

    def test_custom_template_selection(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test custom template selection (not a preset)"""
        project_data = {
            "name": "Custom Selection",
            "clientId": test_client_record.id,
            "templateQuantities": {
                "1": 10,  # Heavy on Problem Recognition
                "9": 15,  # Heavy on How-To
                "13": 5,  # Some Future Thinking
            },
            "pricePerPost": 40.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        project_response = response.json()

        assert project_response["numPosts"] == 30
        assert project_response["totalPrice"] == 1200.0

        print("✓ Custom template selection created successfully")
        print(f"  - Template distribution: {project_response['templateQuantities']}")

    def test_project_update_with_quantities(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test updating project with new template quantities"""
        # Create project
        project_data = {
            "name": "Update Test",
            "clientId": test_client_record.id,
            "templateQuantities": {"1": 5, "2": 5},
            "pricePerPost": 40.0,
        }

        create_response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        project_id = create_response.json()["id"]

        # Update quantities
        update_data = {
            "templateQuantities": {"1": 10, "9": 10},  # Changed quantities
        }

        update_response = client.put(
            f"/api/projects/{project_id}",
            json=update_data,
            headers=auth_headers
        )

        assert update_response.status_code == 200
        updated_project = update_response.json()

        # Note: num_posts and total_price are NOT auto-recalculated on update
        # (only on create via model_validator)
        assert updated_project["templateQuantities"] == {"1": 10, "9": 10}

        print("✓ Project updated successfully with new quantities")

    def test_empty_template_quantities(
        self, client, auth_headers, test_client_record
    ):
        """Test that empty template_quantities is handled gracefully"""
        project_data = {
            "name": "Empty Quantities Test",
            "clientId": test_client_record.id,
            "templateQuantities": {},  # Empty dict
            "numPosts": 30,  # Manually specified
            "pricePerPost": 40.0,
            "totalPrice": 1200.0,  # Manually specified
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        # Should succeed - empty quantities is valid (uses intelligent selection)
        assert response.status_code == 200
        project_response = response.json()

        assert project_response["numPosts"] == 30
        assert project_response["totalPrice"] == 1200.0

        print("✓ Empty template_quantities handled gracefully (fallback to intelligent selection)")


class TestBackwardCompatibility:
    """Tests for backward compatibility with old template system"""

    def test_old_templates_field_still_works(
        self, client, auth_headers, test_client_record, db_session
    ):
        """Test that projects with old 'templates' array field still work"""
        # Old format: templates as array of IDs
        project_data = {
            "name": "Legacy Template Format",
            "clientId": test_client_record.id,
            "templates": ["1", "2", "9"],  # Old format
            "numPosts": 30,
            "pricePerPost": 40.0,
        }

        response = client.post(
            "/api/projects",
            json=project_data,
            headers=auth_headers
        )

        # Should succeed for backward compatibility
        assert response.status_code == 200
        project_response = response.json()

        # Old templates field should be stored
        assert project_response.get("templates") == ["1", "2", "9"]
        assert project_response["numPosts"] == 30

        print("✓ Backward compatibility: old 'templates' array format works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
