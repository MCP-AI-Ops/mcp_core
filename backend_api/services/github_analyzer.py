"""
GitHub Analyzer Service - MCP 로직을 백엔드에서 직접 실행

server_production.py의 핵심 로직을 재사용하여
백엔드 API에서 직접 GitHub 분석 수행
"""
from typing import Dict, Any
from github import Github, GithubException


class GitHubAnalyzer:
    """GitHub 저장소 자동 분석 서비스"""
    
    def __init__(self, github_token: str = None):
        """
        Args:
            github_token: GitHub API 토큰 (선택, rate limit 회피용)
        """
        self.github_token = github_token
        self.client = Github(github_token) if github_token else Github()
    
    def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        GitHub 저장소 자동 분석 (완전 자동화)
        
        Args:
            repo_url: GitHub 저장소 URL
        
        Returns:
            분석 결과 딕셔너리:
            - name, full_name, description
            - stars, forks, language
            - service_type (자동 추론)
            - estimated_users (자동 계산)
            - time_slot (자동 감지)
            - resources (CPU/Memory 자동 추정)
        
        Raises:
            ValueError: 잘못된 URL 또는 접근 불가 저장소
        """
        # URL 파싱
        owner, repo_name = self._parse_github_url(repo_url)
        
        try:
            # GitHub API 호출
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            
            # 자동 분석 실행
            service_type = self._detect_service_type(repo)
            time_slot = self._detect_time_slot(repo)
            estimated_users = self._estimate_users(repo.stargazers_count, repo.forks_count)
            resources = self._estimate_cpu_memory(repo, service_type, repo.stargazers_count)
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "language": repo.language or "Unknown",
                "service_type": service_type,
                "estimated_users": estimated_users,
                "time_slot": time_slot,
                "resources": resources
            }
            
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"저장소를 찾을 수 없습니다: {owner}/{repo_name}")
            elif e.status == 403:
                raise ValueError("GitHub API rate limit 초과. GITHUB_TOKEN 설정이 필요합니다.")
            else:
                raise ValueError(f"GitHub API 오류: {e}")
    
    def _parse_github_url(self, repo_url: str) -> tuple[str, str]:
        """GitHub URL에서 owner/repo 추출"""
        repo_url = repo_url.rstrip("/")
        
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        if "/" in repo_url and len(repo_url.split("/")) == 2:
            return tuple(repo_url.split("/"))
        
        raise ValueError(f"잘못된 GitHub URL 형식: {repo_url}")
    
    def _detect_service_type(self, repo) -> str:
        """서비스 타입 자동 추론 (web/api/worker/data)"""
        readme = ""
        try:
            readme_content = repo.get_readme()
            readme = readme_content.decoded_content.decode("utf-8").lower()
        except:
            pass
        
        description = (repo.description or "").lower()
        combined_text = readme + " " + description
        
        # 키워드 기반 추론
        if any(kw in combined_text for kw in ["flask", "django", "fastapi", "express", "react", "vue", "next.js", "frontend", "ui"]):
            return "web"
        elif any(kw in combined_text for kw in ["worker", "celery", "sidekiq", "queue", "background", "job"]):
            return "worker"
        elif any(kw in combined_text for kw in ["data", "ml", "machine learning", "tensorflow", "pytorch", "spark", "analytics"]):
            return "data"
        else:
            # 언어 기반 폴백
            languages = repo.get_languages()
            if "JavaScript" in languages or "TypeScript" in languages:
                return "web"
            else:
                return "api"
    
    def _detect_time_slot(self, repo) -> str:
        """활성 시간대 자동 감지 (최근 커밋 기반)"""
        try:
            commits = repo.get_commits()
            latest_commit = commits[0]
            hour = latest_commit.commit.author.date.hour
            
            if 9 <= hour < 18:
                return "peak"
            elif 18 <= hour < 22:
                return "normal"
            elif hour >= 22 or hour < 6:
                return "low"
            else:
                return "weekend"
        except:
            return "peak"  # 기본값
    
    def _estimate_users(self, stars: int, forks: int) -> int:
        """사용자 수 자동 계산 (Stars/Forks 기반)"""
        return max(10, int(stars * 0.05 + forks * 1.5))
    
    def _estimate_cpu_memory(self, repo, service_type: str, stars: int) -> Dict[str, int]:
        """
        CPU/Memory 자동 추정 (다단계 로직)
        
        Returns:
            {"cpu": int, "memory": int}  # memory는 MB 단위
        """
        language = repo.language or "Unknown"
        
        # 1단계: 언어별 기본값
        language_defaults = {
            "Java": {"cpu": 4, "memory": 8192},
            "Scala": {"cpu": 4, "memory": 8192},
            "Kotlin": {"cpu": 4, "memory": 8192},
            "C++": {"cpu": 4, "memory": 4096},
            "Rust": {"cpu": 2, "memory": 2048},
            "Go": {"cpu": 2, "memory": 2048},
            "Python": {"cpu": 2, "memory": 4096},
            "JavaScript": {"cpu": 2, "memory": 4096},
            "TypeScript": {"cpu": 2, "memory": 4096},
            "Ruby": {"cpu": 2, "memory": 4096},
            "PHP": {"cpu": 2, "memory": 4096},
        }
        
        base = language_defaults.get(language, {"cpu": 2, "memory": 4096})
        cpu = base["cpu"]
        memory = base["memory"]
        
        # 2단계: 서비스 타입 조정
        service_multipliers = {
            "web": {"cpu": 1.0, "memory": 1.5},
            "api": {"cpu": 1.2, "memory": 1.0},
            "worker": {"cpu": 1.5, "memory": 1.2},
            "data": {"cpu": 2.0, "memory": 2.0},
        }
        
        multiplier = service_multipliers.get(service_type, {"cpu": 1.0, "memory": 1.0})
        cpu = int(cpu * multiplier["cpu"])
        memory = int(memory * multiplier["memory"])
        
        # 3단계: Stars 규모 스케일링
        if stars > 50000:
            cpu = min(cpu * 4, 16)
            memory = min(memory * 4, 32768)
        elif stars > 10000:
            cpu = min(cpu * 2, 8)
            memory = min(memory * 2, 16384)
        elif stars > 1000:
            cpu = int(cpu * 1.5)
            memory = int(memory * 1.5)
        
        return {"cpu": cpu, "memory": memory}
