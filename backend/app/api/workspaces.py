"""API Router for Workspace management, Git repository cloning, and file uploads."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from ..core.workspace_service import (
    GitOperationError,
    WorkspaceSecurityError,
    WorkspaceService,
)
from .dependencies import get_current_user_id, get_workspace_service
from .schemas import (
    GitCloneRequest,
    GitOperationResponse,
    WorkspaceStatusResponse,
    WorkspaceTreeItem,
    WorkspaceUploadResponse,
)

router = APIRouter()


@router.post("/git-clone", response_model=GitOperationResponse, status_code=status.HTTP_200_OK)
async def git_clone_repo(
    request: GitCloneRequest,
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Clone a remote Git repository (GitHub/GitLab/Gitee) or pull latest code into cloud workspace."""
    try:
        result = await service.clone_or_pull_repo(
            user_id=user_id,
            repo_url=request.repo_url,
            workspace_id=request.workspace_id,
            branch=request.branch,
            depth=request.depth,
            auth_token=request.auth_token,
            clean_existing=request.clean_existing,
        )
        return GitOperationResponse(**result)
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except GitOperationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git 操作异常: {exc}")


@router.post("/upload-archive", response_model=WorkspaceUploadResponse, status_code=status.HTTP_200_OK)
async def upload_project_archive(
    file: UploadFile = File(..., description="本地项目压缩包 (.zip, .tar, .tar.gz, .tgz)"),
    workspace_id: str = Form("default", description="目标工作空间ID"),
    clean_existing: bool = Form(False, description="是否先清空目标工作空间"),
    strip_root_dir: bool = Form(True, description="是否自动去除压缩包最外层包裹的单根目录"),
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Upload and extract a user's local project archive (Zip/Tar) to cloud workspace with Zip Slip security."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供有效文件名")

    filename_lower = file.filename.lower()
    valid_suffixes = (".zip", ".tar", ".tar.gz", ".tgz")
    if not any(filename_lower.endswith(s) for s in valid_suffixes):
        raise HTTPException(status_code=400, detail=f"不支持的压缩包格式: {file.filename}，请上传 .zip, .tar, .tar.gz 或 .tgz")

    # Save to a temporary file before extracting
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).name) as tmp_file:
        tmp_path = Path(tmp_file.name)
        try:
            shutil.copyfileobj(file.file, tmp_file)
        finally:
            file.file.close()

    try:
        result = await service.extract_project_archive(
            user_id=user_id,
            archive_path=tmp_path,
            workspace_id=workspace_id,
            clean_existing=clean_existing,
            strip_root_dir=strip_root_dir,
        )
        return WorkspaceUploadResponse(
            success=True,
            workspace_id=workspace_id,
            workspace_path=result["workspace_path"],
            file_count=result["file_count"],
            total_size_bytes=result["total_size_bytes"],
            files=result["extracted_files"],
            message=f"成功解压并保存 {result['file_count']} 个文件到云端工作空间",
        )
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解压上传文件失败: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/upload-files", response_model=WorkspaceUploadResponse, status_code=status.HTTP_200_OK)
async def upload_project_files(
    files: List[UploadFile] = File(..., description="上传的文件列表"),
    relative_paths: Optional[List[str]] = Form(None, description="各文件在本地项目中的相对路径 (用于保留文件夹层级)"),
    workspace_id: str = Form("default", description="目标工作空间ID"),
    clean_existing: bool = Form(False, description="是否先清空目标工作空间"),
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Upload multiple local files/folders directly (supports directory structure via relative paths)."""
    if not files:
        raise HTTPException(status_code=400, detail="上传文件列表不能为空")

    files_data = []
    try:
        for idx, f in enumerate(files):
            rel_path = relative_paths[idx] if (relative_paths and idx < len(relative_paths)) else (f.filename or f"file_{idx}")
            content = await f.read()
            files_data.append((rel_path, content))
            await f.close()

        result = await service.save_uploaded_files(
            user_id=user_id,
            files_data=files_data,
            workspace_id=workspace_id,
            clean_existing=clean_existing,
        )
        return WorkspaceUploadResponse(
            success=True,
            workspace_id=workspace_id,
            workspace_path=result["workspace_path"],
            file_count=result["file_count"],
            total_size_bytes=result["total_size_bytes"],
            files=result["saved_files"],
            message=f"成功上传并保存 {result['file_count']} 个文件到云端工作空间",
        )
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"上传文件失败: {exc}")


@router.get("/{workspace_id}/status", response_model=WorkspaceStatusResponse)
def get_workspace_status(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Get status, size, file count, and Git info for a given workspace."""
    try:
        status_info = service.get_workspace_status(user_id=user_id, workspace_id=workspace_id)
        git_info = status_info.git_info
        return WorkspaceStatusResponse(
            workspace_id=status_info.workspace_id,
            user_id=status_info.user_id,
            exists=status_info.exists,
            absolute_path=status_info.absolute_path,
            file_count=status_info.file_count,
            total_size_bytes=status_info.total_size_bytes,
            is_git_repo=status_info.is_git_repo,
            git_branch=git_info.branch if git_info else None,
            git_commit=git_info.commit_hash if git_info else None,
            git_commit_message=git_info.commit_message if git_info else None,
            git_author=git_info.author if git_info else None,
            git_remote_url=git_info.remote_url if git_info else None,
        )
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{workspace_id}/tree")
def get_workspace_tree(
    workspace_id: str,
    path: str = Query("", description="子路径过滤 (默认为工作空间根目录)"),
    max_depth: int = Query(4, ge=1, le=10, description="最大遍历深度"),
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Retrieve directory tree structure of the workspace."""
    try:
        tree = service.get_workspace_tree(
            user_id=user_id,
            workspace_id=workspace_id,
            subpath=path,
            max_depth=max_depth,
        )
        return tree
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{workspace_id}", status_code=status.HTTP_200_OK)
def delete_workspace(
    workspace_id: str,
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
):
    """Delete or reset a workspace on the cloud server."""
    try:
        deleted = service.delete_workspace(user_id=user_id, workspace_id=workspace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"工作空间 '{workspace_id}' 不存在")
        return {"success": True, "message": f"工作空间 '{workspace_id}' 已成功清理"}
    except WorkspaceSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
