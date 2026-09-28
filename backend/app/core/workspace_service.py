"""Workspace service for managing user project storage, Git imports, and file uploads."""

import asyncio
import os
import re
import shutil
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse


class WorkspaceSecurityError(Exception):
    """Raised when an unsafe path or operation is attempted."""
    pass


class GitOperationError(Exception):
    """Raised when a Git operation fails."""
    pass


@dataclass
class GitRepoInfo:
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    remote_url: Optional[str] = None


@dataclass
class WorkspaceStatus:
    workspace_id: str
    user_id: str
    exists: bool
    absolute_path: str
    file_count: int = 0
    total_size_bytes: int = 0
    is_git_repo: bool = False
    git_info: Optional[GitRepoInfo] = None


class WorkspaceService:
    """Handles workspace isolation, Git repository cloning/pulling, and local project archive extraction."""

    # Disallowed characters in user_id or workspace_id to prevent path injection
    INVALID_ID_CHARS = re.compile(r'[\\/:\*\?"<>\|\x00]')

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            # Default to <PROJECT_ROOT>/project
            project_root = Path(__file__).resolve().parents[3]
            self.base_dir = project_root / "project"
        else:
            self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def validate_identifier(self, name: str, param_name: str = "identifier") -> str:
        """Validate that an ID does not contain path separators or dangerous characters."""
        if not name or not isinstance(name, str):
            raise WorkspaceSecurityError(f"{param_name} 不能为空")
        name = name.strip()
        if not name or name in (".", ".."):
            raise WorkspaceSecurityError(f"无效的 {param_name}: '{name}'")
        if self.INVALID_ID_CHARS.search(name):
            raise WorkspaceSecurityError(f"{param_name} 包含非法字符: '{name}'")
        return name

    def resolve_workspace_dir(self, user_id: str, workspace_id: str = "default", create: bool = True) -> Path:
        """Resolve and validate the absolute path for a user's workspace.
        
        Guarantees that the resulting path is strictly inside `self.base_dir`.
        Structure: <base_dir>/<user_id>/<workspace_id>
        """
        clean_user_id = self.validate_identifier(user_id, "user_id")
        clean_ws_id = self.validate_identifier(workspace_id, "workspace_id")

        target_dir = (self.base_dir / clean_user_id / clean_ws_id).resolve()

        # Strict containment check
        try:
            target_dir.relative_to(self.base_dir)
        except ValueError:
            raise WorkspaceSecurityError(f"工作空间路径逃逸检测拦截: {target_dir}")

        if create:
            target_dir.mkdir(parents=True, exist_ok=True)

        return target_dir

    def _sanitize_git_url(self, repo_url: str, auth_token: Optional[str] = None) -> Tuple[str, str]:
        """Inject auth_token into HTTPS URL if provided, and return (safe_url_with_auth, masked_url_for_logs)."""
        repo_url = repo_url.strip()
        if not repo_url:
            raise ValueError("Git 仓库地址不能为空")

        if not auth_token:
            return repo_url, repo_url

        parsed = urlparse(repo_url)
        if parsed.scheme in ("http", "https"):
            # Format: https://token@github.com/... or https://oauth2:token@...
            netloc = f"oauth2:{auth_token}@{parsed.netloc}"
            masked_netloc = f"oauth2:***@{parsed.netloc}"
            safe_url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            masked_url = urlunparse((parsed.scheme, masked_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
            return safe_url, masked_url

        return repo_url, repo_url

    async def _run_git_command(self, args: List[str], cwd: Path, masked_args: Optional[List[str]] = None) -> Tuple[int, str, str]:
        """Execute a git command asynchronously without invoking shell=True."""
        display_cmd = " ".join(masked_args or args)
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()
            return process.returncode or 0, out_str, err_str
        except FileNotFoundError:
            raise GitOperationError("云服务器未检测到 Git 命令行工具，请确保系统已安装 Git")
        except Exception as exc:
            raise GitOperationError(f"执行 Git 命令失败 [{display_cmd}]: {exc}")

    def get_git_info(self, workspace_dir: Path) -> Optional[GitRepoInfo]:
        """Extract Git repository info if workspace is a git repo."""
        git_dir = workspace_dir / ".git"
        if not git_dir.exists():
            return None

        info = GitRepoInfo()
        try:
            # 1. Branch name
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if branch_res.returncode == 0:
                info.branch = branch_res.stdout.strip()

            # 2. Commit hash
            hash_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if hash_res.returncode == 0:
                info.commit_hash = hash_res.stdout.strip()[:8]

            # 3. Commit message & author
            log_res = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%an|%s"],
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if log_res.returncode == 0 and log_res.stdout.strip():
                parts = log_res.stdout.strip().split("|", 1)
                info.author = parts[0]
                if len(parts) > 1:
                    info.commit_message = parts[1]

            # 4. Remote URL
            remote_res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(workspace_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if remote_res.returncode == 0:
                info.remote_url = remote_res.stdout.strip()
        except Exception:
            pass

        return info

    async def clone_or_pull_repo(
        self,
        user_id: str,
        repo_url: str,
        workspace_id: str = "default",
        branch: Optional[str] = None,
        depth: int = 1,
        auth_token: Optional[str] = None,
        clean_existing: bool = False,
    ) -> Dict[str, Any]:
        """Clone a remote Git repository into the user's workspace, or pull updates if already cloned."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=True)
        exec_url, masked_url = self._sanitize_git_url(repo_url, auth_token)

        # Check if workspace has files
        existing_files = [f for f in workspace_dir.iterdir() if f.name != ".git"]
        is_git = (workspace_dir / ".git").exists()

        if clean_existing and (existing_files or is_git):
            # Clean workspace
            for item in workspace_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            existing_files = []
            is_git = False

        if is_git:
            # Existing git repository: fetch and checkout
            git_info = self.get_git_info(workspace_dir)
            target_branch = branch or (git_info.branch if git_info else "main")

            # Fetch
            code, out, err = await self._run_git_command(["fetch", "origin"], cwd=workspace_dir)
            if code != 0:
                raise GitOperationError(f"Git fetch 失败: {err or out}")

            # Checkout & pull
            code, out, err = await self._run_git_command(["checkout", target_branch], cwd=workspace_dir)
            if code != 0:
                # Try checkout -B
                code, out, err = await self._run_git_command(["checkout", "-B", target_branch, f"origin/{target_branch}"], cwd=workspace_dir)

            code, out, err = await self._run_git_command(["pull", "origin", target_branch], cwd=workspace_dir)
            action = "pull"
        else:
            if existing_files:
                raise WorkspaceSecurityError(
                    f"工作空间 '{workspace_id}' 已存在文件，无法直接 Git Clone。请指定 clean_existing=True 或使用新 workspace_id"
                )

            # Fresh clone
            clone_args = ["clone"]
            masked_args = ["clone"]
            if depth and depth > 0:
                clone_args.extend(["--depth", str(depth)])
                masked_args.extend(["--depth", str(depth)])
            if branch:
                clone_args.extend(["--branch", branch])
                masked_args.extend(["--branch", branch])

            clone_args.extend([exec_url, str(workspace_dir)])
            masked_args.extend([masked_url, str(workspace_dir)])

            code, out, err = await self._run_git_command(
                clone_args,
                cwd=self.base_dir,
                masked_args=masked_args,
            )
            if code != 0:
                raise GitOperationError(f"Git Clone 失败: {err or out}")
            action = "clone"

        # Collect results
        git_info = self.get_git_info(workspace_dir)
        stats = self.calculate_dir_stats(workspace_dir)

        return {
            "success": True,
            "action": action,
            "workspace_id": workspace_id,
            "workspace_path": str(workspace_dir),
            "repo_url": masked_url,
            "branch": git_info.branch if git_info else branch,
            "commit_hash": git_info.commit_hash if git_info else None,
            "commit_message": git_info.commit_message if git_info else None,
            "author": git_info.author if git_info else None,
            "file_count": stats["file_count"],
            "total_size_bytes": stats["total_size_bytes"],
        }

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path, strip_root_dir: bool = True) -> List[str]:
        """Safely extract a zip archive to target_dir with Zip Slip protection."""
        extracted_files = []
        target_dir_abs = target_dir.resolve()

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            if not namelist:
                return []

            # Check if all files are inside a single root folder (e.g. repo-master/...)
            prefix_to_strip = ""
            if strip_root_dir:
                first_parts = [name.split("/")[0] for name in namelist if name.strip("/")]
                if first_parts and all(p == first_parts[0] for p in first_parts):
                    # Check if the common first part is a directory
                    common_prefix = first_parts[0] + "/"
                    if any(name.startswith(common_prefix) for name in namelist):
                        prefix_to_strip = common_prefix

            for member in zf.infolist():
                rel_name = member.filename
                if prefix_to_strip and rel_name.startswith(prefix_to_strip):
                    rel_name = rel_name[len(prefix_to_strip):]

                if not rel_name or rel_name.endswith("/"):
                    continue

                dest_path = (target_dir / rel_name).resolve()

                # Zip Slip security check
                try:
                    dest_path.relative_to(target_dir_abs)
                except ValueError:
                    raise WorkspaceSecurityError(f"非法压缩包路径拦截 (Zip Slip): {member.filename}")

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(dest_path, "wb") as target:
                    shutil.copyfileobj(source, target)

                extracted_files.append(rel_name)

        return extracted_files

    def _safe_extract_tar(self, tar_path: Path, target_dir: Path, strip_root_dir: bool = True) -> List[str]:
        """Safely extract a tar/tar.gz archive to target_dir with path traversal protection."""
        extracted_files = []
        target_dir_abs = target_dir.resolve()

        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            if not members:
                return []

            prefix_to_strip = ""
            if strip_root_dir:
                first_parts = [m.name.split("/")[0] for m in members if m.name.strip("/")]
                if first_parts and all(p == first_parts[0] for p in first_parts):
                    common_prefix = first_parts[0] + "/"
                    if any(m.name.startswith(common_prefix) for m in members):
                        prefix_to_strip = common_prefix

            for member in members:
                if not member.isfile():
                    continue

                rel_name = member.name
                if prefix_to_strip and rel_name.startswith(prefix_to_strip):
                    rel_name = rel_name[len(prefix_to_strip):]

                if not rel_name:
                    continue

                dest_path = (target_dir / rel_name).resolve()
                try:
                    dest_path.relative_to(target_dir_abs)
                except ValueError:
                    raise WorkspaceSecurityError(f"非法压缩包路径拦截 (Tar Slip): {member.name}")

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                fileobj = tf.extractfile(member)
                if fileobj:
                    with open(dest_path, "wb") as target:
                        shutil.copyfileobj(fileobj, target)
                    extracted_files.append(rel_name)

        return extracted_files

    async def extract_project_archive(
        self,
        user_id: str,
        archive_path: Path,
        workspace_id: str = "default",
        clean_existing: bool = False,
        strip_root_dir: bool = True,
    ) -> Dict[str, Any]:
        """Extract a user-uploaded project archive (zip, tar, tgz) into the workspace."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=True)

        if clean_existing:
            for item in workspace_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

        suffix = archive_path.name.lower()
        if suffix.endswith(".zip"):
            extracted = await asyncio.to_thread(
                self._safe_extract_zip, archive_path, workspace_dir, strip_root_dir
            )
        elif suffix.endswith((".tar", ".tar.gz", ".tgz")):
            extracted = await asyncio.to_thread(
                self._safe_extract_tar, archive_path, workspace_dir, strip_root_dir
            )
        else:
            raise ValueError(f"不支持的压缩包格式: {archive_path.name}，支持 .zip, .tar, .tar.gz, .tgz")

        stats = self.calculate_dir_stats(workspace_dir)

        return {
            "success": True,
            "workspace_id": workspace_id,
            "workspace_path": str(workspace_dir),
            "file_count": stats["file_count"],
            "total_size_bytes": stats["total_size_bytes"],
            "extracted_files": extracted[:50],  # Return up to 50 sample paths
            "has_more_files": len(extracted) > 50,
        }

    async def save_uploaded_files(
        self,
        user_id: str,
        files_data: List[Tuple[str, bytes]],
        workspace_id: str = "default",
        clean_existing: bool = False,
    ) -> Dict[str, Any]:
        """Save a list of (relative_path, bytes) representing local project files/folders."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=True)
        workspace_abs = workspace_dir.resolve()

        if clean_existing:
            for item in workspace_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)

        saved_files = []
        for rel_path_str, content in files_data:
            # Clean and normalize path
            clean_rel = rel_path_str.replace("\\", "/").lstrip("/")
            if not clean_rel or ".." in clean_rel:
                raise WorkspaceSecurityError(f"非法相对路径拦截: {rel_path_str}")

            dest_path = (workspace_dir / clean_rel).resolve()
            try:
                dest_path.relative_to(workspace_abs)
            except ValueError:
                raise WorkspaceSecurityError(f"文件路径逃逸拦截: {rel_path_str}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(content)
            saved_files.append(clean_rel)

        stats = self.calculate_dir_stats(workspace_dir)

        return {
            "success": True,
            "workspace_id": workspace_id,
            "workspace_path": str(workspace_dir),
            "file_count": stats["file_count"],
            "total_size_bytes": stats["total_size_bytes"],
            "saved_files": saved_files[:50],
        }

    def calculate_dir_stats(self, directory: Path) -> Dict[str, int]:
        """Calculate total file count and size in bytes for a directory."""
        if not directory.exists():
            return {"file_count": 0, "total_size_bytes": 0}

        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(directory):
            # Skip .git objects for speed
            if ".git" in dirs:
                dirs.remove(".git")
            for f in files:
                fp = Path(root) / f
                try:
                    total_size += fp.stat().st_size
                    file_count += 1
                except Exception:
                    pass

        return {"file_count": file_count, "total_size_bytes": total_size}

    def get_workspace_tree(
        self,
        user_id: str,
        workspace_id: str = "default",
        subpath: str = "",
        max_depth: int = 4,
        max_items: int = 300,
    ) -> Dict[str, Any]:
        """Generate a hierarchical tree of files and directories in the workspace."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=False)
        if not workspace_dir.exists():
            return {"name": workspace_id, "is_dir": True, "children": [], "exists": False}

        base_target = workspace_dir
        if subpath:
            clean_sub = subpath.replace("\\", "/").strip("/")
            base_target = (workspace_dir / clean_sub).resolve()
            try:
                base_target.relative_to(workspace_dir.resolve())
            except ValueError:
                raise WorkspaceSecurityError("子路径逃逸拦截")

        items_counted = 0

        def _build_tree(current_path: Path, current_depth: int) -> Dict[str, Any]:
            nonlocal items_counted
            is_dir = current_path.is_dir()
            node: Dict[str, Any] = {
                "name": current_path.name or workspace_id,
                "path": str(current_path.relative_to(workspace_dir)).replace("\\", "/"),
                "is_dir": is_dir,
            }

            if not is_dir:
                try:
                    node["size"] = current_path.stat().st_size
                except Exception:
                    node["size"] = 0
                return node

            node["children"] = []
            if current_depth >= max_depth or items_counted >= max_items:
                return node

            try:
                entries = sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for entry in entries:
                    if entry.name == ".git":
                        # Flag .git existence without traversing thousands of object blobs
                        node["children"].append({
                            "name": ".git",
                            "path": str(entry.relative_to(workspace_dir)).replace("\\", "/"),
                            "is_dir": True,
                            "children": [],
                            "is_git_root": True,
                        })
                        continue

                    items_counted += 1
                    child_node = _build_tree(entry, current_depth + 1)
                    node["children"].append(child_node)
                    if items_counted >= max_items:
                        break
            except PermissionError:
                pass

            return node

        tree = _build_tree(base_target, current_depth=0)
        tree["exists"] = True
        return tree

    def get_workspace_status(self, user_id: str, workspace_id: str = "default") -> WorkspaceStatus:
        """Inspect the current workspace status, size, and Git repository metadata."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=False)
        exists = workspace_dir.exists()

        if not exists:
            return WorkspaceStatus(
                workspace_id=workspace_id,
                user_id=user_id,
                exists=False,
                absolute_path=str(workspace_dir),
            )

        stats = self.calculate_dir_stats(workspace_dir)
        is_git = (workspace_dir / ".git").exists()
        git_info = self.get_git_info(workspace_dir) if is_git else None

        return WorkspaceStatus(
            workspace_id=workspace_id,
            user_id=user_id,
            exists=True,
            absolute_path=str(workspace_dir),
            file_count=stats["file_count"],
            total_size_bytes=stats["total_size_bytes"],
            is_git_repo=is_git,
            git_info=git_info,
        )

    def delete_workspace(self, user_id: str, workspace_id: str = "default") -> bool:
        """Safely delete a workspace directory."""
        workspace_dir = self.resolve_workspace_dir(user_id, workspace_id, create=False)
        if not workspace_dir.exists():
            return False
        shutil.rmtree(workspace_dir, ignore_errors=True)
        return True
