"""Blackboard state workspace manager for isolated pipeline runs."""

import os
import json
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from ecostream.models.state import RunState, RunIndex, PipelinePhase, QueryLogEntry, AssumptionLogEntry


class BlackboardWorkspace:
    """Manages files and structured JSON state in runs/<run_id>/."""

    def __init__(self, run_id: str, base_runs_dir: Optional[str] = None):
        self.run_id = run_id
        if base_runs_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_runs_dir = os.path.join(project_root, "runs")
        self.run_dir = os.path.join(base_runs_dir, run_id)
        self.raw_inputs_dir = os.path.join(self.run_dir, "raw_inputs")
        self.markdown_inputs_dir = os.path.join(self.run_dir, "markdown_inputs")
        self.intermediate_dir = os.path.join(self.run_dir, "intermediate")
        self.deliverables_dir = os.path.join(self.run_dir, "deliverables")

        self.state_file = os.path.join(self.run_dir, "state.json")
        self.index_file = os.path.join(self.run_dir, "index.json")

    def initialize_workspace(self) -> RunState:
        """Create directory structure and initialize state.json."""
        os.makedirs(self.raw_inputs_dir, exist_ok=True)
        os.makedirs(self.markdown_inputs_dir, exist_ok=True)
        os.makedirs(self.intermediate_dir, exist_ok=True)
        os.makedirs(self.deliverables_dir, exist_ok=True)

        initial_state = RunState(
            run_id=self.run_id,
            phase=PipelinePhase.INITIALIZED,
            progress_pct=0.0,
            start_time=datetime.now(timezone.utc).isoformat(),
        )
        self.save_state(initial_state)
        return initial_state

    def save_state(self, state: RunState) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))

    def load_state(self) -> Optional[RunState]:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return RunState(**json.load(f))
        return None

    def save_index(self, index: RunIndex) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write(index.model_dump_json(indent=2))

    def load_index(self) -> Optional[RunIndex]:
        if os.path.exists(self.index_file):
            with open(self.index_file, "r", encoding="utf-8") as f:
                return RunIndex(**json.load(f))
        return None

    def save_intermediate_json(self, filename: str, data: Any) -> str:
        """Save an intermediate JSON artifact into intermediate/ folder."""
        file_path = os.path.join(self.intermediate_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            if hasattr(data, "model_dump_json"):
                f.write(data.model_dump_json(indent=2))
            elif isinstance(data, list) and data and hasattr(data[0], "model_dump"):
                json.dump([item.model_dump() for item in data], f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return file_path

    def load_intermediate_json(self, filename: str) -> Optional[Any]:
        file_path = os.path.join(self.intermediate_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def store_raw_input(self, src_path: str) -> str:
        """Copy uploaded raw file to raw_inputs/."""
        fname = os.path.basename(src_path)
        dest = os.path.join(self.raw_inputs_dir, fname)
        shutil.copy2(src_path, dest)
        return dest

    def store_markdown_input(self, name: str, content: str) -> str:
        """Store converted markdown file in markdown_inputs/."""
        dest = os.path.join(self.markdown_inputs_dir, name)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        return dest

    def get_all_markdown_inputs(self) -> Dict[str, str]:
        """Read all markdown files in markdown_inputs/."""
        sources: Dict[str, str] = {}
        if os.path.exists(self.markdown_inputs_dir):
            for fname in sorted(os.listdir(self.markdown_inputs_dir)):
                fpath = os.path.join(self.markdown_inputs_dir, fname)
                if os.path.isfile(fpath) and fname.endswith(".md"):
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        sources[fname] = f.read()
        return sources

    def list_intermediate_files(self) -> List[Dict[str, Any]]:
        """List all intermediate JSON/text files with sizes and timestamps."""
        files = []
        if os.path.exists(self.intermediate_dir):
            for fname in sorted(os.listdir(self.intermediate_dir)):
                fpath = os.path.join(self.intermediate_dir, fname)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    files.append({
                        "filename": fname,
                        "size_bytes": stat.st_size,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    })
        return files

    def list_deliverables(self) -> List[Dict[str, Any]]:
        """List all generated deliverable files with sizes and timestamps."""
        files = []
        if os.path.exists(self.deliverables_dir):
            for fname in sorted(os.listdir(self.deliverables_dir)):
                fpath = os.path.join(self.deliverables_dir, fname)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    files.append({
                        "filename": fname,
                        "size_bytes": stat.st_size,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "url": f"/api/orchestrator/runs/{self.run_id}/deliverables/{fname}",
                    })
        return files

    def get_file_manifest(self) -> Dict[str, Any]:
        """Return full directory manifest of the blackboard workspace."""
        def scan_dir(directory: str) -> List[Dict[str, Any]]:
            items = []
            if os.path.exists(directory):
                for fname in sorted(os.listdir(directory)):
                    fpath = os.path.join(directory, fname)
                    if os.path.isfile(fpath):
                        stat = os.stat(fpath)
                        items.append({
                            "filename": fname,
                            "size_bytes": stat.st_size,
                            "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        })
            return items

        return {
            "run_id": self.run_id,
            "has_state": os.path.exists(self.state_file),
            "has_index": os.path.exists(self.index_file),
            "raw_inputs": scan_dir(self.raw_inputs_dir),
            "markdown_inputs": scan_dir(self.markdown_inputs_dir),
            "intermediate": scan_dir(self.intermediate_dir),
            "deliverables": self.list_deliverables(),
        }

