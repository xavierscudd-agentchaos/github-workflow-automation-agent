"""
GitHub Workflow Automation Agent - Python Implementation
Provides automated GitHub workflow management including PR handling, code generation, and refactoring
"""

import os
import json
import logging
from typing import List, Dict, Optional
from github import Github, GithubException
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the GitHub Agent"""
    github_token: str
    repo_owner: str
    repo_name: str
    auto_label: bool = True
    auto_assign: bool = False
    auto_merge: bool = False


class GitHubAgent:
    """Main agent class for GitHub automation"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.g = Github(config.github_token)
        self.repo = self.g.get_repo(f"{config.repo_owner}/{config.repo_name}")
        logger.info(f"GitHub Agent initialized for {config.repo_owner}/{config.repo_name}")

    def get_open_prs(self) -> List:
        """Get all open pull requests"""
        try:
            prs = self.repo.get_pulls(state='open')
            logger.info(f"Found {prs.totalCount} open pull requests")
            return list(prs)
        except GithubException as e:
            logger.error(f"Error fetching PRs: {e}")
            return []

    def get_open_issues(self) -> List:
        """Get all open issues"""
        try:
            issues = self.repo.get_issues(state='open')
            logger.info(f"Found {issues.totalCount} open issues")
            return list(issues)
        except GithubException as e:
            logger.error(f"Error fetching issues: {e}")
            return []

    def auto_label_pr(self, pr) -> None:
        """Automatically label a pull request based on file changes"""
        try:
            files = [f.filename for f in pr.get_files()]
            labels = self._determine_labels(files)
            
            if labels:
                pr.add_to_labels(*labels)
                logger.info(f"PR #{pr.number}: Applied labels {labels}")
            else:
                logger.info(f"PR #{pr.number}: No labels to apply")
        except GithubException as e:
            logger.error(f"Error labeling PR #{pr.number}: {e}")

    def auto_label_issue(self, issue) -> None:
        """Automatically label an issue based on content"""
        try:
            body = (issue.title + ' ' + (issue.body or '')).lower()
            labels = []

            # Categorize by type
            if any(keyword in body for keyword in ['bug', 'error', 'crash', 'broken']):
                labels.append('bug')
            if any(keyword in body for keyword in ['feature', 'enhancement', 'request']):
                labels.append('enhancement')
            if any(keyword in body for keyword in ['doc', 'documentation']):
                labels.append('documentation')
            if any(keyword in body for keyword in ['question', 'help']):
                labels.append('question')

            if labels:
                issue.add_to_labels(*labels)
                logger.info(f"Issue #{issue.number}: Applied labels {labels}")
        except GithubException as e:
            logger.error(f"Error labeling issue #{issue.number}: {e}")

    def _determine_labels(self, files: List[str]) -> List[str]:
        """Determine labels based on files changed"""
        labels = []

        if any('test' in f for f in files):
            labels.append('testing')
        if any('doc' in f for f in files):
            labels.append('documentation')
        if any(f.endswith('.py') for f in files):
            labels.append('python')
        if any(f.endswith('.java') for f in files):
            labels.append('java')
        if any(f.endswith('.kt') for f in files):
            labels.append('kotlin')
        if any(f.endswith(('.yml', '.yaml')) for f in files):
            labels.append('ci/cd')

        return list(set(labels))

    def check_pr_ready_to_merge(self, pr) -> bool:
        """Check if a PR is ready to merge"""
        try:
            # Check if all status checks pass
            commit = pr.get_commits().reversed[0]
            statuses = commit.get_statuses()
            
            all_success = all(status.state == 'success' for status in statuses)
            
            # Check if approved
            reviews = pr.get_reviews()
            approved = any(review.state == 'APPROVED' for review in reviews)
            
            logger.info(f"PR #{pr.number}: All checks pass: {all_success}, Approved: {approved}")
            return all_success and approved
        except GithubException as e:
            logger.error(f"Error checking PR #{pr.number}: {e}")
            return False

    def merge_pr_if_ready(self, pr) -> bool:
        """Merge PR if it's ready"""
        try:
            if self.check_pr_ready_to_merge(pr):
                pr.merge()
                logger.info(f"PR #{pr.number}: Successfully merged")
                return True
            else:
                logger.info(f"PR #{pr.number}: Not ready to merge")
                return False
        except GithubException as e:
            logger.error(f"Error merging PR #{pr.number}: {e}")
            return False

    def add_pr_comment(self, pr, comment: str) -> None:
        """Add a comment to a PR"""
        try:
            pr.create_issue_comment(comment)
            logger.info(f"PR #{pr.number}: Comment added")
        except GithubException as e:
            logger.error(f"Error commenting on PR #{pr.number}: {e}")

    def run_workflow(self) -> Dict:
        """Run the main automation workflow"""
        logger.info("Starting GitHub Agent workflow...")
        
        results = {
            'prs_labeled': 0,
            'issues_labeled': 0,
            'prs_merged': 0,
            'errors': []
        }

        # Label open PRs
        if self.config.auto_label:
            for pr in self.get_open_prs():
                self.auto_label_pr(pr)
                results['prs_labeled'] += 1

            # Label open issues
            for issue in self.get_open_issues():
                if not issue.pull_request:
                    self.auto_label_issue(issue)
                    results['issues_labeled'] += 1

        # Auto-merge if configured
        if self.config.auto_merge:
            for pr in self.get_open_prs():
                if self.merge_pr_if_ready(pr):
                    results['prs_merged'] += 1

        logger.info(f"Workflow completed: {json.dumps(results, indent=2)}")
        return results


def main():
    """Main entry point"""
    # Load configuration from environment
    config = AgentConfig(
        github_token=os.getenv('GITHUB_TOKEN', ''),
        repo_owner=os.getenv('REPO_OWNER', 'xavierscudd-agentchaos'),
        repo_name=os.getenv('REPO_NAME', 'github-workflow-automation-agent'),
        auto_label=os.getenv('AUTO_LABEL', 'true').lower() == 'true',
        auto_assign=os.getenv('AUTO_ASSIGN', 'false').lower() == 'true',
        auto_merge=os.getenv('AUTO_MERGE', 'false').lower() == 'true'
    )

    # Create and run agent
    agent = GitHubAgent(config)
    results = agent.run_workflow()
    
    return results


if __name__ == '__main__':
    main()
