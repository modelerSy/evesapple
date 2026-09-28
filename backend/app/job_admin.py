import argparse
from .job_manager import job_manager

parser = argparse.ArgumentParser(description="Manage EVE investigation jobs")
sub = parser.add_subparsers(dest="command", required=True)
sub.add_parser("list", help="list active investigations")
clear = sub.add_parser("clear", help="remove active investigations")
clear.add_argument("--all", action="store_true", required=True, help="remove all queued/running jobs")
args = parser.parse_args()

if args.command == "list":
    for row in job_manager.list_active():
        print(f"{row['id']}\t{row['status']}\t{row['created_at']}")
elif args.command == "clear":
    print(f"Removed {job_manager.clear_active()} active investigation(s).")
