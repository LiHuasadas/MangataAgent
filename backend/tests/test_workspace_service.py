"""Comprehensive tests for WorkspaceService and Workspace API endpoints."""

import asyncio
import io
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.workspace_service import (
    WorkspaceSecurityError,
    WorkspaceService,
)
from backend.app.main import app


@pytest.fixture
def temp_workspace_dir():
    """Create a temporary directory for workspace tests and clean up afterwards."""
    temp_dir = Path(tempfile.mkdtemp(prefix="mangata_ws_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def workspace_service(temp_workspace_dir):
    """Instantiate a WorkspaceService with isolated temp directory."""
    return WorkspaceService(base_dir=temp_workspace_dir)


class TestWorkspaceServiceIsolationAndSecurity:
    """Security and tenant isolation verification."""

    def test_valid_workspace_resolution(self, workspace_service, temp_workspace_dir):
        ws_path = workspace_service.resolve_workspace_dir("user_123", "proj_abc")
        expected = (temp_workspace_dir / "user_123" / "proj_abc").resolve()
        assert ws_path == expected
        assert ws_path.exists()

    def test_prevent_user_id_path_traversal(self, workspace_service):
        with pytest.raises(WorkspaceSecurityError):
            workspace_service.resolve_workspace_dir("../evil_user", "default")

        with pytest.raises(WorkspaceSecurityError):
            workspace_service.resolve_workspace_dir("user/sub", "default")

        with pytest.raises(WorkspaceSecurityError):
            workspace_service.resolve_workspace_dir("", "default")

    def test_prevent_workspace_id_path_traversal(self, workspace_service):
        with pytest.raises(WorkspaceSecurityError):
            workspace_service.resolve_workspace_dir("user_123", "../../etc")

        with pytest.raises(WorkspaceSecurityError):
            workspace_service.resolve_workspace_dir("user_123", "a\\b")


class TestArchiveUploadAndExtraction:
    """Test Zip and Tar extraction with Zip Slip defense."""

    def test_zip_archive_extraction_with_root_stripping(self, workspace_service, temp_workspace_dir):
        # Create a mock zip with a GitHub-style outer root folder: repo-master/...
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("repo-master/src/main.py", "print('hello from uploaded project')")
            zf.writestr("repo-master/README.md", "# Project Readme")
            zf.writestr("repo-master/config/settings.json", '{"debug": true}')

        zip_buffer.seek(0)
        zip_path = temp_workspace_dir / "test_upload.zip"
        zip_path.write_bytes(zip_buffer.getvalue())

        result = asyncio.run(workspace_service.extract_project_archive(
            user_id="alice",
            archive_path=zip_path,
            workspace_id="my-repo",
            strip_root_dir=True,
        ))

        assert result["success"] is True
        assert result["file_count"] == 3
        ws_dir = workspace_service.resolve_workspace_dir("alice", "my-repo", create=False)
        assert (ws_dir / "src" / "main.py").exists()
        assert (ws_dir / "README.md").exists()
        assert (ws_dir / "config" / "settings.json").exists()
        assert (ws_dir / "src" / "main.py").read_text(encoding="utf-8") == "print('hello from uploaded project')"

    def test_zip_slip_protection(self, workspace_service, temp_workspace_dir):
        # Craft a malicious zip containing path traversal
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Attempt to write outside workspace directory
            zf.writestr("../../escape.txt", "malicious payload")

        zip_buffer.seek(0)
        zip_path = temp_workspace_dir / "malicious.zip"
        zip_path.write_bytes(zip_buffer.getvalue())

        with pytest.raises(WorkspaceSecurityError, match="Zip Slip"):
            asyncio.run(workspace_service.extract_project_archive(
                user_id="bob",
                archive_path=zip_path,
                workspace_id="hack-attempt",
            ))

    def test_tar_archive_extraction(self, workspace_service, temp_workspace_dir):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tf:
            data = b"package com.example;\npublic class App {}"
            ti = tarfile.TarInfo(name="my-app/App.java")
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))

        tar_path = temp_workspace_dir / "project.tar.gz"
        tar_path.write_bytes(tar_buffer.getvalue())

        result = asyncio.run(workspace_service.extract_project_archive(
            user_id="charlie",
            archive_path=tar_path,
            workspace_id="java-proj",
            strip_root_dir=True,
        ))
        assert result["success"] is True
        assert result["file_count"] == 1
        ws_dir = workspace_service.resolve_workspace_dir("charlie", "java-proj", create=False)
        assert (ws_dir / "App.java").exists()


class TestMultiFileUploadAndTree:
    """Test folder-structured file uploads and file tree generation."""

    def test_save_uploaded_files_preserves_structure(self, workspace_service):
        files_data = [
            ("frontend/src/index.tsx", b"import React from 'react';"),
            ("frontend/package.json", b'{"name": "test"}'),
            ("backend/main.py", b"from fastapi import FastAPI"),
        ]
        result = asyncio.run(workspace_service.save_uploaded_files(
            user_id="david",
            files_data=files_data,
            workspace_id="fullstack",
        ))
        assert result["success"] is True
        assert result["file_count"] == 3

        ws_dir = workspace_service.resolve_workspace_dir("david", "fullstack", create=False)
        assert (ws_dir / "frontend" / "src" / "index.tsx").exists()
        assert (ws_dir / "backend" / "main.py").exists()

        # Check tree
        tree = workspace_service.get_workspace_tree(user_id="david", workspace_id="fullstack")
        assert tree["exists"] is True
        assert tree["is_dir"] is True
        child_names = [c["name"] for c in tree["children"]]
        assert "backend" in child_names
        assert "frontend" in child_names

    def test_workspace_status(self, workspace_service):
        ws_dir = workspace_service.resolve_workspace_dir("emma", "test-stat")
        (ws_dir / "file1.txt").write_text("12345", encoding="utf-8")
        (ws_dir / "file2.txt").write_text("67890", encoding="utf-8")

        status = workspace_service.get_workspace_status("emma", "test-stat")
        assert status.exists is True
        assert status.file_count == 2
        assert status.total_size_bytes == 10
        assert status.is_git_repo is False


class TestWorkspaceApiEndpoints:
    """FastAPI endpoints integration tests."""

    @pytest.fixture
    def client(self, workspace_service):
        # Inject isolated workspace_service into app.state
        app.state.workspace_service = workspace_service
        return TestClient(app)

    def test_upload_archive_endpoint(self, client, workspace_service):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("index.html", "<h1>Hello Mangata</h1>")
            zf.writestr("css/style.css", "body { color: gold; }")

        zip_buf.seek(0)
        response = client.post(
            "/api/v1/workspaces/upload-archive",
            headers={"X-User-ID": "test_user_api"},
            data={"workspace_id": "web-site", "clean_existing": "true"},
            files={"file": ("project.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["workspace_id"] == "web-site"
        assert data["file_count"] == 2

        # Verify status endpoint
        status_resp = client.get(
            "/api/v1/workspaces/web-site/status",
            headers={"X-User-ID": "test_user_api"},
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["file_count"] == 2

        # Verify tree endpoint
        tree_resp = client.get(
            "/api/v1/workspaces/web-site/tree",
            headers={"X-User-ID": "test_user_api"},
        )
        assert tree_resp.status_code == 200
        assert tree_resp.json()["exists"] is True

    def test_upload_files_endpoint(self, client):
        response = client.post(
            "/api/v1/workspaces/upload-files",
            headers={"X-User-ID": "test_user_api"},
            data={"workspace_id": "direct-upload"},
            files=[
                ("files", ("a.py", b"print('a')", "text/plain")),
                ("files", ("b.py", b"print('b')", "text/plain")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_count"] == 2

    def test_git_clone_endpoint_mocked(self, client, workspace_service):
        # Mock _run_git_command to simulate a successful git clone
        with patch.object(workspace_service, "_run_git_command", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = (0, "Cloning into...", "")
            with patch.object(workspace_service, "get_git_info") as mock_info:
                from backend.app.core.workspace_service import GitRepoInfo
                mock_info.return_value = GitRepoInfo(
                    branch="main",
                    commit_hash="a1b2c3d4",
                    commit_message="Initial commit",
                    author="Developer",
                    remote_url="https://github.com/mangata/repo.git",
                )

                response = client.post(
                    "/api/v1/workspaces/git-clone",
                    headers={"X-User-ID": "test_user_api"},
                    json={
                        "repo_url": "https://github.com/mangata/repo.git",
                        "workspace_id": "cloned-repo",
                        "branch": "main",
                        "depth": 1,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["action"] == "clone"
                assert data["branch"] == "main"
                assert data["commit_hash"] == "a1b2c3d4"

    def test_delete_workspace_endpoint(self, client, workspace_service):
        ws_dir = workspace_service.resolve_workspace_dir("del_user", "to-delete")
        (ws_dir / "temp.txt").write_text("bye", encoding="utf-8")

        response = client.delete(
            "/api/v1/workspaces/to-delete",
            headers={"X-User-ID": "del_user"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert not ws_dir.exists()
