import argparse
import sys

def find_new_projects(file_a, file_b, output_file):
    try:
        # Read file A (the reference/existing list)
        # We use a set for O(1) lookup performance
        with open(file_a, 'r', encoding='utf-8') as f:
            existing_projects = {line.strip().lower() for line in f if line.strip()}

        # Read file B (the new list)
        with open(file_b, 'r', encoding='utf-8') as f:
            new_list = [line.strip() for line in f if line.strip()]

        # Filter: keep items from B that are NOT in A
        unique_new_projects = [
            proj for proj in new_list 
            if proj.lower() not in existing_projects
        ]

        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for proj in unique_new_projects:
                f.write(f"{proj}\n")

        print(f"--- Success ---")
        print(f"Compared {len(new_list)} items against {len(existing_projects)} references.")
        print(f"Found {len(unique_new_projects)} new projects. Saved to: {output_file}")

    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e.filename}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Find GitHub projects in file B that aren't in file A.")
    
    parser.add_argument("-a", default="websites.txt", 
                        help="Reference file (default: websites.txt)")
    parser.add_argument("-b", default="gh_projects.txt", 
                        help="New projects file (default: gh_projects.txt)")
    parser.add_argument("-o", default="new_projects.txt", 
                        help="Output file (default: new_projects.txt)")

    args = parser.parse_args()

    find_new_projects(args.a, args.b, args.o)

if __name__ == "__main__":
    fetch_and_save_repos()
