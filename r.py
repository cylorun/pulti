import pulti,os

# def get_resets(file) -> int:
#     try:
#         file_path = f'{pulti.PULTI_DIR}\\{file}'
#         if not os.path.exists(file_path):
#             print(f"File {file_path} does not exist.")
#             return 0

#         with open(file_path, 'r') as resets_file:
#             r = resets_file.read().strip()
#             if not r:
#                 print(f"File {file_path} is empty.")
#                 return 0
#             return int(r)
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return 0


# def update_reset_count(count=1) -> None:
#     with open(f'{pulti.PULTI_DIR}\\resets.txt', 'w') as resets, open(f'{pulti.PULTI_DIR}\\session_resets.txt', 'w') as session_resets:
#         v = get_resets('resets.txt') + count
#         print(v)
#         resets.write(str(v))
#         session_resets.write(str(get_resets('session_resets.txt') + count))


print(open(f'{pulti.PULTI_DIR}\\resets.txt', 'r').read())
