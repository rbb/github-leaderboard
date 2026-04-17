# **Software Specification: GitHub Topic Leaderboard Generator (v1.2)**

## **1\. Project Goal**

To create a Python-based utility using the ghapi library that ranks GitHub repositories based on a weighted multi-factor scoring system, outputting the results to a structured CSV file.

## **2\. Input Requirements**

The tool must support two mutually exclusive input methods:

1. **Topic Discovery:** A string representing a GitHub topic (e.g., machine-learning). The tool fetches the top $N$ repositories for that topic.  
2. **Target List:** A local .txt file containing repository identifiers (format: owner/repo), one per line.

## **3\. Metrics Definitions & API Mapping**

The "Leaderboard Score" will be derived from the following metrics using the GitHub REST API via ghapi:

| Metric | Logic / API Filter | Significance |
| :---- | :---- | :---- |
| **Stars** | stargazers\_count | Overall popularity/historical significance. |
| **Commits (7d)** | stats/commit\_activity | Raw technical output volume. |
| **PR Activity (7d)** | Search: type:pr created:\>YYYY-MM-DD | Community engagement and discussion. |
| **Merged PRs (7d)** | Search: type:pr is:merged merged:\>YYYY-MM-DD | Successful integration of new features/fixes. |
| **Trending Bonus** | Calculated: $\\Delta Stars \\div TotalStars$ | Velocity indicator for "up-and-coming" projects. |
| **Clones (7d)** | traffic/clones | Actual usage (Requires Admin/Push access). |

## **4\. Scoring Algorithm**

The user provides a configuration (JSON or YAML) defining weights ($W$) for each metric.  
$$Score \= (W\_{star} \\cdot Stars) \+ (W\_{com} \\cdot Commits) \+ (W\_{pra} \\cdot PR\_{active}) \+ (W\_{prm} \\cdot PR\_{merged}) \+ (W\_{trn} \\cdot Trend) \+ (W\_{cln} \\cdot Clones)$$  
*Note: If Clones are inaccessible (403 Error), the system must log a warning and treat* $Clones \= 0$ *for that specific repository.*

## **5\. Technical Stack**

* **Language:** Python 3.9+  
* **Library:** ghapi (for GitHub interaction)  
* **Authentication:** GitHub Personal Access Token (PAT) via environment variables.  
* **Output:** pandas or standard csv library for file generation.

## **6\. Execution Flow**

1. **Initialize:** Authenticate ghapi.GhApi with token.  
2. **Source Repos:** Load from .txt or query via api.search.repos(q=f'topic:{topic}').  
3. **Calculate Dates:** Compute ISO-8601 timestamps for T-7 days.  
4. **Fetch & Aggregate:** \* Iterate through repositories.  
   * Perform concurrent or sequential API calls for metrics.  
   * Handle rate limiting using exponential backoff.  
5. **Score:** Apply weights to the aggregated data.  
6. **Export:** Save sorted results to leaderboard.csv.