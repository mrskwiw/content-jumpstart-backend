"""
Contract Testing: Validate API responses against OpenAPI schema

Tests that actual API behavior matches the OpenAPI specification exactly.
Catches contract drift, missing fields, wrong types, and schema violations.
"""

import pytest


@pytest.fixture(scope="module")
def openapi_spec():
    """Load OpenAPI schema from backend"""
    import sys
    import os

    # Suppress backend startup output
    devnull = open(os.devnull, "w")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = devnull
    sys.stderr = devnull

    try:
        from backend.main import app
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        devnull.close()

    return app.openapi()


@pytest.fixture
def validate_response(openapi_spec):
    """Factory for validating responses against OpenAPI schema"""
    from jsonschema import validate, ValidationError

    def _validate(method: str, path: str, response):
        """Validate response against OpenAPI schema"""
        schema_dict = openapi_spec
        paths = schema_dict.get("paths", {})

        # Find the path in schema
        openapi_path = None
        for schema_path in paths.keys():
            if schema_path == path or path.startswith(schema_path.split("{")[0]):
                openapi_path = schema_path
                break

        if not openapi_path:
            raise AssertionError(f"Path {path} not found in OpenAPI schema")

        # Get the operation (method)
        operation = paths[openapi_path].get(method.lower())
        if not operation:
            raise AssertionError(f"Method {method} not found for path {path}")

        # Get the response schema for this status code
        responses = operation.get("responses", {})
        status_code_str = str(response.status_code)

        if status_code_str not in responses:
            raise AssertionError(
                f"Status code {status_code_str} not documented in schema for {method} {path}"
            )

        response_spec = responses[status_code_str]
        content_spec = response_spec.get("content", {})

        # Check if response has JSON content
        if "application/json" in content_spec:
            json_schema = content_spec["application/json"].get("schema", {})

            # Resolve $ref if present
            if "$ref" in json_schema:
                ref_path = json_schema["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    schema_name = ref_path.split("/")[-1]
                    json_schema = schema_dict["components"]["schemas"][schema_name]

            # Validate response JSON against schema
            try:
                response_data = response.json()
                validate(instance=response_data, schema=json_schema)
            except ValidationError as e:
                raise AssertionError(
                    f"OpenAPI contract validation failed for {method} {path}:\n"
                    f"Schema validation error: {e.message}\n"
                    f"Failed at path: {'.'.join(str(p) for p in e.absolute_path)}"
                )

    return _validate


class TestClientContractValidation:
    """Validate /api/clients/* endpoints against OpenAPI schema"""

    def test_list_clients_schema(self, client, test_user_headers, validate_response):
        """List clients endpoint returns schema-compliant response"""
        response = client.get("/api/clients/", headers=test_user_headers)
        assert response.status_code == 200
        validate_response("GET", "/api/clients/", response)

    def test_get_client_schema(self, client, test_user_headers, test_client, validate_response):
        """Get client by ID returns schema-compliant response"""
        response = client.get(f"/api/clients/{test_client.id}", headers=test_user_headers)
        assert response.status_code == 200
        validate_response("GET", f"/api/clients/{test_client.id}", response)


class TestProjectContractValidation:
    """Validate /api/projects/* endpoints against OpenAPI schema"""

    def test_list_projects_schema(self, client, test_user_headers, validate_response):
        """List projects endpoint returns schema-compliant response"""
        response = client.get("/api/projects/", headers=test_user_headers)
        assert response.status_code == 200
        validate_response("GET", "/api/projects/", response)

    def test_get_project_schema(self, client, test_user_headers, test_project, validate_response):
        """Get project by ID returns schema-compliant response"""
        response = client.get(f"/api/projects/{test_project.id}", headers=test_user_headers)
        assert response.status_code == 200
        validate_response("GET", f"/api/projects/{test_project.id}", response)


class TestResearchContractValidation:
    """Validate /api/research/* endpoints against OpenAPI schema"""

    def test_list_research_tools_schema(self, client, test_user_headers, validate_response):
        """List research tools returns schema-compliant response"""
        response = client.get("/api/research/tools", headers=test_user_headers)
        assert response.status_code == 200
        validate_response("GET", "/api/research/tools", response)


class TestHealthContractValidation:
    """Validate health check endpoints against OpenAPI schema"""

    def test_health_check_schema(self, client, validate_response):
        """Health check endpoint returns schema-compliant response"""
        response = client.get("/health")
        assert response.status_code == 200
        validate_response("GET", "/health", response)


def test_contract_validation_coverage(openapi_spec):
    """
    Document contract testing coverage

    This test serves as documentation of endpoints with contract testing.
    """
    endpoints_tested = [
        ("GET", "/api/clients/"),
        ("GET", "/api/clients/{id}"),
        ("GET", "/api/projects/"),
        ("GET", "/api/projects/{project_id}"),
        ("GET", "/api/research/tools"),
        ("GET", "/health"),
    ]

    # Verify all endpoints exist in OpenAPI schema
    paths = openapi_spec.get("paths", {})

    for method, path in endpoints_tested:
        # Check if path exists in schema (exact or with path params)
        found = False
        for schema_path in paths.keys():
            if path == schema_path or path.split("{")[0] == schema_path.split("{")[0]:
                found = True
                break
        assert found, f"Path {path} not found in OpenAPI schema"

    assert (
        len(endpoints_tested) == 6
    ), f"Contract validation covers {len(endpoints_tested)} critical endpoints"
