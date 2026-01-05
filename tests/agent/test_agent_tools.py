"""
Unit tests for agent tools
"""

import pytest

from agent.tools import AgentTools


class TestAgentTools:
    """Test agent tool wrappers"""

    def setup_method(self):
        """Setup test tools"""
        self.tools = AgentTools()

    def test_list_clients(self):
        """Test listing clients"""
        result = self.tools.list_clients()

        assert result is not None
        assert "success" in result
        assert "clients" in result
        assert isinstance(result["clients"], list)

    def test_list_projects(self):
        """Test listing projects"""
        result = self.tools.list_projects(limit=5)

        assert result is not None
        assert "success" in result
        assert "projects" in result
        assert isinstance(result["projects"], list)

    def test_list_projects_with_filter(self):
        """Test listing projects filtered by client"""
        result = self.tools.list_projects(client_name="NonExistentClient", limit=10)

        assert result is not None
        # Should return success=True with empty projects list
        if not result["success"]:
            print(f"Error: {result.get('error', 'Unknown error')}")
        assert result["success"] is True
        assert result["count"] == 0

    def test_read_file_not_found(self):
        """Test reading non-existent file"""
        result = self.tools.read_file("nonexistent_file.txt")

        assert result is not None
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_search_files_empty_pattern(self):
        """Test searching for files with pattern"""
        result = self.tools.search_files(pattern="*.nonexistent")

        assert result is not None
        assert "success" in result
        assert "matches" in result
        assert isinstance(result["matches"], list)

    def test_get_available_tools(self):
        """Test getting list of available tools"""
        tools = self.tools.get_available_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check tool structure
        first_tool = tools[0]
        assert "name" in first_tool
        assert "description" in first_tool
        assert "parameters" in first_tool

    def test_extract_project_id(self):
        """Test project ID extraction from output"""
        output = """
        Generation complete!
        Project ID: TestProject_20251203_120000
        Files saved to: data/outputs/
        """

        project_id = self.tools._extract_project_id(output)
        assert project_id == "TestProject_20251203_120000"

    def test_extract_project_id_not_found(self):
        """Test project ID extraction when not present"""
        output = "Some other output without project ID"

        project_id = self.tools._extract_project_id(output)
        assert project_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
