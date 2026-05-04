from collections import defaultdict


# Store users who activate private detector mode
active_private_users = set()

# Store private chat text messages temporarily before processing
private_message_buffer = defaultdict(list)

# Store active delayed processing tasks for private text messages
private_process_tasks = {}

# Store unsupported private chat content temporarily before processing
private_non_text_buffer = defaultdict(list)

# Store active delayed processing tasks for unsupported private content
private_non_text_process_tasks = {}

# Store group chat messages temporarily before processing
# Key format: (chat_id, user_id)
group_message_buffer = defaultdict(list)

# Store active delayed processing tasks per group user
# Key format: (chat_id, user_id)
group_process_tasks = {}