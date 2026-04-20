import requests
import argparse
import sys

def main():
    # 1. Set up Command Line Arguments
    parser = argparse.ArgumentParser(
        description="Fetch GitHub repository names and save to a file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
    
    parser.add_argument(
        "-u", "--url", 
        default="https://api.github.com/search/repositories?q=topic:ai",
        help="The GitHub API URL to query"
    )
    
    parser.add_argument(
        "-o", "--out", 
        default="gh_projects.txt",
        help="The output filename (default: gh_projects.txt)"
    )

    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Print the repository names to STDOUT while saving"
    )

    args = parser.parse_args()

    # 2. Define Headers
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "python-script"
    }

    try:
        # 3. Make the Request
        response = requests.get(args.url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle GitHub's search structure (items) vs list structure
        if isinstance(data, dict) and "items" in data:
            repositories = data["items"]
        elif isinstance(data, list):
            repositories = data
        else:
            print("Unexpected JSON structure returned from API.", file=sys.stderr)
            return

        # 4. Process and Save Data
        count = 0
        with open(args.out, "w", encoding="utf-8") as f:
            for repo in repositories:
                repo_name = repo.get("full_name")
                if repo_name:
                    f.write(f"{repo_name}\n")
                    count += 1
                    # Only print to STDOUT if verbose flag is set
                    if args.verbose:
                        print(repo_name)

        if args.verbose:
            print(f"\n--- Done! {count} projects saved to {args.out} ---")

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_save_repos()
