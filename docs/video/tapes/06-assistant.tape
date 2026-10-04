Type "make assistant AS_OF=2026-09-16T10:00:00-07:00"
Enter
Sleep 6s
Type "Message Sarah on Slack that the geocoding fix looks good"
Enter
Sleep 5s
Type "yes"
Enter
Sleep 2s
Ctrl+D
Sleep 1s
Type "tail -1 outbox/audit.jsonl | python3 -m json.tool"
Enter
Sleep 4s
