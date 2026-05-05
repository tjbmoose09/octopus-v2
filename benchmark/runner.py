"""Octopus Agents V2 — Benchmark Runner
Tests all available LM Studio models against each agent role.
Measures: speed, output quality, response time, and resource usage."""

import httpx
import time
import json
import asyncio
import psutil
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LM_STUDIO_API, AGENT_ROLES, SYSTEM_PROMPTS
from database.db import execute, fetch_all

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False


class BenchmarkRunner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
        self.base_url = LM_STUDIO_API
        self.results = []
        self.status = "idle"  # idle, running, complete, error
        self.progress = {"current_model": "", "current_role": "", "total": 0, "done": 0}

    async def get_available_models(self) -> list:
        """Query LM Studio for all available models."""
        try:
            resp = await self.client.get(f"{self.base_url}/models")
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            return [m.get("id", m.get("name", "unknown")) for m in models]
        except Exception as e:
            return []

    def get_system_info(self) -> dict:
        """Get current system resource usage."""
        info = {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
            "ram_percent": psutil.virtual_memory().percent,
        }
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    info["gpu_name"] = gpu.name
                    info["gpu_vram_total_mb"] = round(gpu.memoryTotal, 0)
                    info["gpu_vram_used_mb"] = round(gpu.memoryUsed, 0)
                    info["gpu_vram_percent"] = round(gpu.memoryUtil * 100, 1)
                    info["gpu_load_percent"] = round(gpu.load * 100, 1)
            except:
                pass
        return info

    async def benchmark_model_for_role(self, model_id: str, role: str) -> dict:
        """Run a single benchmark: one model against one role."""
        role_info = AGENT_ROLES.get(role)
        if not role_info:
            return {"error": f"Unknown role: {role}"}

        system_prompt = SYSTEM_PROMPTS.get(role, "You are a helpful assistant.")
        benchmark_prompt = role_info["benchmark_prompt"]

        # Build OpenAI-compatible format
        body = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": benchmark_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }

        # Measure system before
        sys_before = self.get_system_info()
        ram_before = psutil.virtual_memory().used

        # Call LM Studio OpenAI-compatible /v1/chat/completions
        start_time = time.time()
        try:
            resp = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=body,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            return {
                "model": model_id,
                "role": role,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
            }

        elapsed_ms = (time.time() - start_time) * 1000
        ram_after = psutil.virtual_memory().used

        # Extract metrics — handle both native and OpenAI-compat response formats
        try:
            if "choices" in result:
                # OpenAI-compatible format
                content = result["choices"][0]["message"]["content"]
            else:
                # LM Studio native format
                content = result.get("content", result.get("response", result.get("output", "")))
                if isinstance(content, list):
                    content = "".join(
                        block.get("text", str(block)) for block in content if isinstance(block, dict)
                    ) or str(content)
                if not content:
                    content = str(result)
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        except (KeyError, IndexError):
            content = str(result)
            total_tokens = 0
            completion_tokens = 0

        # Calculate tokens per second
        tps = (completion_tokens / (elapsed_ms / 1000)) if elapsed_ms > 0 and completion_tokens > 0 else 0

        # Quality score (heuristic based on output)
        quality = self._score_quality(content, role)

        # RAM delta
        ram_delta_mb = (ram_after - ram_before) / (1024**2)

        # VRAM
        vram_used = 0
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    vram_used = gpus[0].memoryUsed
            except:
                pass

        benchmark_result = {
            "model": model_id,
            "role": role,
            "response_time_ms": round(elapsed_ms, 1),
            "tokens_per_second": round(tps, 1),
            "completion_tokens": completion_tokens,
            "output_length": len(content),
            "quality_score": quality,
            "ram_delta_mb": round(ram_delta_mb, 1),
            "vram_usage_mb": round(vram_used, 1),
            "output_preview": content[:300],
        }

        # Store in DB
        await execute(
            """INSERT INTO benchmarks (model_id, role, tokens_per_second, response_time_ms,
               quality_score, output_length, vram_usage_mb, ram_usage_mb)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (model_id, role, tps, elapsed_ms, quality, len(content), vram_used, ram_delta_mb),
        )

        return benchmark_result

    def _score_quality(self, output: str, role: str) -> float:
        """Heuristic quality scoring (0-100) based on role expectations."""
        score = 50.0  # baseline

        # Length check — too short is bad, too long may be unfocused
        length = len(output)
        if length < 100:
            score -= 20
        elif length > 300:
            score += 10
        if length > 800:
            score += 10

        # Structure checks
        if "```" in output:
            score += 10  # Code blocks present
        if any(marker in output.lower() for marker in ["def ", "class ", "function", "import"]):
            if role in ("dev", "qa", "devops", "automation"):
                score += 15  # Code-producing roles should produce code
        if any(marker in output.lower() for marker in ["critical", "warning", "severity", "issue"]):
            if role in ("critic", "review"):
                score += 15  # Review roles should flag issues
        if "{" in output and "}" in output:
            score += 5  # Structured output
        if any(marker in output.lower() for marker in ["pro", "con", "compare", "analysis"]):
            if role == "research":
                score += 15

        # JSON structure check for PM/orchestrator
        if role in ("pm", "orchestrator"):
            try:
                json.loads(output)
                score += 20
            except:
                if "json" in output.lower() or '"' in output:
                    score += 5

        return min(100, max(0, score))

    async def run_full_benchmark(self) -> dict:
        """Benchmark all available models against all roles."""
        self.status = "running"
        self.results = []

        models = await self.get_available_models()
        if not models:
            self.status = "error"
            return {"error": "No models available in LM Studio. Make sure LM Studio is running with at least one model loaded."}

        roles = list(AGENT_ROLES.keys())
        total = len(models) * len(roles)
        self.progress = {"current_model": "", "current_role": "", "total": total, "done": 0}

        system_info = self.get_system_info()

        for model in models:
            for role in roles:
                self.progress["current_model"] = model
                self.progress["current_role"] = role

                result = await self.benchmark_model_for_role(model, role)
                self.results.append(result)

                self.progress["done"] += 1

        # Compute best assignments
        assignments = self._compute_best_assignments(models, roles)

        # Store assignments
        for role, assignment in assignments.items():
            await execute(
                "INSERT OR REPLACE INTO model_assignments (role, model_id, benchmark_score) VALUES (?, ?, ?)",
                (role, assignment["model"], assignment["score"]),
            )

        self.status = "complete"

        return {
            "system_info": system_info,
            "models_tested": models,
            "roles_tested": roles,
            "total_benchmarks": total,
            "results": self.results,
            "assignments": assignments,
        }

    def _compute_best_assignments(self, models: list, roles: list) -> dict:
        """Assign best model to each role based on composite score."""
        assignments = {}

        for role in roles:
            role_results = [r for r in self.results if r.get("role") == role and "error" not in r]
            if not role_results:
                continue

            # Composite score: 40% quality + 30% speed + 30% inverse-response-time
            best = None
            best_score = -1

            for r in role_results:
                quality = r.get("quality_score", 0) / 100
                tps = min(r.get("tokens_per_second", 0) / 50, 1)  # Normalize to 0-1 (50 tps = max)
                speed = 1 - min(r.get("response_time_ms", 10000) / 10000, 1)  # Lower is better

                # For orchestrator and PM, weight quality higher
                if role in ("orchestrator", "pm", "critic"):
                    composite = quality * 0.6 + tps * 0.2 + speed * 0.2
                # For dev/devops/automation, weight speed + quality equally
                elif role in ("dev", "devops", "automation"):
                    composite = quality * 0.4 + tps * 0.35 + speed * 0.25
                else:
                    composite = quality * 0.4 + tps * 0.3 + speed * 0.3

                if composite > best_score:
                    best_score = composite
                    best = r

            if best:
                assignments[role] = {
                    "model": best["model"],
                    "score": round(best_score * 100, 1),
                    "details": best,
                }

        return assignments


# Global instance
benchmark_runner = BenchmarkRunner()
